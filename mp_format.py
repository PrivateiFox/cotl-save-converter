"""
mp_format.py — read/write Steam 1.5.x .mp save files.

.mp file layout:
  b"E" + 16-byte AES key + 16-byte IV + AES-CBC(PKCS7) ciphertext

Decrypted payload: outer msgpack list whose first element is ExtType(98):
  [uint32 total_uncompressed_len] [uint32 block0_len] [block0 bytes]
  [uint32 block1_len] [block1 bytes] ...

Each block is an LZ4 block (lz4.block mode, NOT lz4.frame).
Concatenated decompressed bytes form the inner msgpack payload:
  a flat positional list → map to named dict using keys.py
"""
from __future__ import annotations

import base64
import json
import struct
from typing import Any

import lz4.block
import msgpack
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from keys import META_KEYS, SLOT_KEYS

_EXT_LZ4 = 98  # MessagePack-CSharp LZ4 extension type


# ── JSON encode/decode for non-serialisable msgpack types ─────────────────────
# bytes      → {"__b64__": "<base64>"}
# ExtType(n) → {"__ext__": n, "__b64__": "<base64>"}
#
# msgpack.ExtType is a namedtuple, so json.JSONEncoder serialises it as a list
# [code, data] without ever calling default().  We pre-process the data tree
# before json.dumps and use object_hook on json.loads to restore the types.

def _to_json_safe(obj: Any) -> Any:
    """Recursively convert non-JSON-native types to JSON-safe marker dicts.

    Handles:
    - bytes/bytearray → {"__b64__": "<base64>"}
    - msgpack.ExtType → {"__ext__": code, "__b64__": "<base64>"}
    - dicts with non-string keys → {"__intmap__": [[key, val], ...]}
      (msgpack allows arbitrary key types; JSON only allows string keys)
    """
    if isinstance(obj, msgpack.ExtType):
        return {"__ext__": obj.code, "__b64__": base64.b64encode(obj.data).decode("ascii")}
    if isinstance(obj, (bytes, bytearray)):
        return {"__b64__": base64.b64encode(obj).decode("ascii")}
    if isinstance(obj, list):
        return [_to_json_safe(item) for item in obj]
    if isinstance(obj, dict):
        if obj and any(not isinstance(k, str) for k in obj):
            return {"__intmap__": [[k, _to_json_safe(v)] for k, v in obj.items()]}
        return {k: _to_json_safe(v) for k, v in obj.items()}
    return obj


def _from_json_safe(obj: dict) -> Any:
    """object_hook: restore bytes/ExtType/int-keyed dicts from JSON marker dicts."""
    if "__ext__" in obj and "__b64__" in obj and len(obj) == 2:
        return msgpack.ExtType(obj["__ext__"], base64.b64decode(obj["__b64__"]))
    if "__b64__" in obj and len(obj) == 1:
        return base64.b64decode(obj["__b64__"])
    if "__intmap__" in obj and len(obj) == 1:
        return dict(obj["__intmap__"])  # [[key, val], ...] → {key: val}
    return obj


# ── Smart msgpack packer (preserves float32 vs float64) ──────────────────────
# MessagePack-CSharp (Unity) encodes C# `float` as float32 (0xca) and
# `double` as float64 (0xcb).  Python's msgpack always uses float64.
# This packer re-encodes each Python float as float32 iff it round-trips
# through float32 without precision loss — matching the original encoding.

def _pack_value(obj: Any) -> bytes:
    """Recursively pack a value to msgpack bytes with smart float encoding."""
    if obj is None:
        return b'\xc0'
    if isinstance(obj, bool):
        return b'\xc3' if obj else b'\xc2'
    if isinstance(obj, int):
        return msgpack.packb(obj, use_bin_type=True)
    if isinstance(obj, float):
        f32_bytes = struct.pack('>f', obj)
        if struct.unpack('>f', f32_bytes)[0] == obj:
            return b'\xca' + f32_bytes   # float32 — round-trips exactly
        return b'\xcb' + struct.pack('>d', obj)  # float64 — needs full precision
    if isinstance(obj, (bytes, bytearray)):
        n = len(obj)
        if n <= 255:
            return b'\xc4' + struct.pack('B', n) + bytes(obj)
        elif n <= 65535:
            return b'\xc5' + struct.pack('>H', n) + bytes(obj)
        else:
            return b'\xc6' + struct.pack('>I', n) + bytes(obj)
    if isinstance(obj, str):
        enc = obj.encode('utf-8')
        n = len(enc)
        if n <= 31:
            return bytes([0xa0 | n]) + enc
        elif n <= 255:
            return b'\xd9' + struct.pack('B', n) + enc
        elif n <= 65535:
            return b'\xda' + struct.pack('>H', n) + enc
        else:
            return b'\xdb' + struct.pack('>I', n) + enc
    if isinstance(obj, msgpack.ExtType):
        data, code = obj.data, obj.code
        n = len(data)
        if n == 1:
            return bytes([0xd4, code]) + data
        elif n == 2:
            return bytes([0xd5, code]) + data
        elif n == 4:
            return bytes([0xd6, code]) + data
        elif n == 8:
            return bytes([0xd7, code]) + data
        elif n == 16:
            return bytes([0xd8, code]) + data
        elif n <= 255:
            return b'\xc7' + struct.pack('B', n) + bytes([code]) + data
        elif n <= 65535:
            return b'\xc8' + struct.pack('>H', n) + bytes([code]) + data
        else:
            return b'\xc9' + struct.pack('>I', n) + bytes([code]) + data
    if isinstance(obj, list):
        n = len(obj)
        if n <= 15:
            header = bytes([0x90 | n])
        elif n <= 65535:
            header = b'\xdc' + struct.pack('>H', n)
        else:
            header = b'\xdd' + struct.pack('>I', n)
        return header + b''.join(_pack_value(item) for item in obj)
    if isinstance(obj, dict):
        n = len(obj)
        if n <= 15:
            header = bytes([0x80 | n])
        elif n <= 65535:
            header = b'\xde' + struct.pack('>H', n)
        else:
            header = b'\xdf' + struct.pack('>I', n)
        return header + b''.join(_pack_value(k) + _pack_value(v) for k, v in obj.items())
    return msgpack.packb(obj, use_bin_type=True)


# ── AES helpers ───────────────────────────────────────────────────────────────

def _aes_decrypt(data: bytes) -> bytes:
    """Decrypt an E+key+iv+ciphertext blob; return plaintext bytes."""
    if data[0:1] != b"E":
        raise ValueError(f"Not a Steam save (expected 'E' header, got {data[0:1]!r})")
    key = data[1:17]
    iv = data[17:33]
    ciphertext = data[33:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    dec = cipher.decryptor()
    padded = dec.update(ciphertext) + dec.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


def _aes_encrypt(plaintext: bytes) -> bytes:
    """Encrypt plaintext bytes; return E+key+iv+ciphertext blob."""
    import secrets
    key = secrets.token_bytes(16)
    iv = secrets.token_bytes(16)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    enc = cipher.encryptor()
    ciphertext = enc.update(padded) + enc.finalize()
    return b"E" + key + iv + ciphertext


# ── LZ4 block helpers ─────────────────────────────────────────────────────────

# Actual .mp file format (verified against real saves):
#   outer msgpack list:
#     outer[0]  ExtType(98) whose .data is msgpack-encoded uncompressed sizes
#               (one uint per block, packed as a stream of msgpack integers)
#     outer[1:] raw bytes — one LZ4 block per entry (lz4.block, NOT lz4.frame)
#
# This differs from the original spec comment which described a self-contained
# binary layout; the real Unity/MessagePack-CSharp encoding separates the
# size hints into the Ext payload and the compressed data into sibling list items.

def _decompress_lz4_outer(outer: list) -> bytes:
    """Decompress an outer msgpack list that uses ExtType(98) for LZ4 blocks.

    outer[0] must be ExtType(98); its .data is a stream of msgpack-encoded
    per-block uncompressed sizes.  outer[1:] are the corresponding compressed
    byte strings.
    """
    ext = outer[0]
    # Decode per-block uncompressed sizes from ext.data (msgpack stream)
    unpacker = msgpack.Unpacker(raw=False)
    unpacker.feed(ext.data)
    sizes: list[int] = list(unpacker)

    chunks: list[bytes] = []
    for block, size in zip(outer[1:], sizes):
        chunks.append(lz4.block.decompress(block, uncompressed_size=size))
    return b"".join(chunks)


def _compress_lz4_outer(data: bytes, block_size: int = 65536) -> list:
    """Compress data into the outer msgpack list format used by .mp files.

    Splits data into blocks of at most block_size bytes, compresses each with
    lz4.block, and returns [ExtType(98, sizes_msgpack), block1, block2, ...].
    """
    blocks = [data[i:i + block_size] for i in range(0, len(data), block_size)]
    compressed_blocks = [lz4.block.compress(b, store_size=False) for b in blocks]
    sizes = [len(b) for b in blocks]

    # Encode sizes as a stream of msgpack integers (same as original format)
    sizes_bytes = b"".join(msgpack.packb(s, use_bin_type=True) for s in sizes)
    ext_obj = msgpack.ExtType(_EXT_LZ4, sizes_bytes)
    return [ext_obj] + compressed_blocks


# ── Key mapping ───────────────────────────────────────────────────────────────

def _pick_keys(positional_list: list) -> dict:
    """Choose SLOT_KEYS or META_KEYS based on list length (< 100 → meta)."""
    return META_KEYS if len(positional_list) < 100 else SLOT_KEYS


def _apply_keys(positional_dict: dict, keys_map: dict) -> dict[str, Any]:
    """Recursively map positional integer keys to field names."""
    result: dict[str, Any] = {}
    for k, v in positional_dict.items():
        entry = keys_map.get(int(k))
        if entry is None:
            result[str(k)] = v
        elif isinstance(entry, str):
            result[entry] = v
        elif isinstance(entry, dict):
            name = entry["name"]
            sub_keys = entry["keys"]
            if v is None:
                result[name] = v
            elif isinstance(sub_keys, list):
                sub_map = sub_keys[0]
                def map_item(item):
                    if item is None:
                        return None
                    if isinstance(item, list):
                        return _apply_keys({i: val for i, val in enumerate(item)}, sub_map)
                    return item
                result[name] = [map_item(item) for item in (v if isinstance(v, list) else [v])]
            else:
                if isinstance(v, list):
                    result[name] = _apply_keys({i: val for i, val in enumerate(v)}, sub_keys)
                else:
                    result[name] = _apply_keys(v, sub_keys)
    return result


def _strip_keys(named_dict: dict, keys_map: dict) -> dict[int, Any]:
    """Inverse of _apply_keys — convert named keys back to integer indices."""
    reverse: dict[str, int] = {}
    for idx, entry in keys_map.items():
        if isinstance(entry, str):
            reverse[entry] = idx
        elif isinstance(entry, dict):
            reverse[entry["name"]] = idx

    result: dict[int, Any] = {}
    for k, v in named_dict.items():
        try:
            int_k = int(k)
            result[int_k] = v
            continue
        except (ValueError, TypeError):
            pass

        idx = reverse.get(k)
        if idx is None:
            continue
        entry = keys_map[idx]
        if isinstance(entry, str):
            result[idx] = v
        elif isinstance(entry, dict):
            sub_keys = entry["keys"]
            if v is None:
                result[idx] = v
            elif isinstance(sub_keys, list):
                sub_map = sub_keys[0]
                def strip_item(item):
                    if item is None:
                        return None
                    if not isinstance(item, dict):
                        return item  # scalar/bytes/ExtType — pass through unchanged
                    stripped = _strip_keys(item, sub_map)
                    if not stripped:
                        return []
                    max_i = max(stripped.keys())
                    return [stripped.get(i) for i in range(max_i + 1)]
                result[idx] = [strip_item(item) for item in (v if isinstance(v, list) else [v])]
            else:
                if not isinstance(v, dict):
                    result[idx] = v  # scalar/bytes/ExtType — pass through unchanged
                    continue
                stripped = _strip_keys(v, sub_keys)
                if not stripped:
                    result[idx] = []
                else:
                    max_i = max(stripped.keys())
                    result[idx] = [stripped.get(i) for i in range(max_i + 1)]
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def read_mp(path: str) -> str:
    """Read a Steam 1.5.x .mp file; return a JSON string with named keys."""
    with open(path, "rb") as f:
        raw = f.read()

    plaintext = _aes_decrypt(raw)

    outer = msgpack.unpackb(plaintext, strict_map_key=False, raw=False)
    if not outer or not isinstance(outer[0], msgpack.ExtType):
        raise ValueError("Unexpected outer msgpack structure (expected ExtType at index 0)")
    if outer[0].code != _EXT_LZ4:
        raise ValueError(f"Expected ExtType code {_EXT_LZ4}, got {outer[0].code}")

    inner_bytes = _decompress_lz4_outer(outer)
    inner_list = msgpack.unpackb(inner_bytes, strict_map_key=False, raw=False)

    if not isinstance(inner_list, list):
        raise ValueError("Inner msgpack payload is not a list")

    keys_map = _pick_keys(inner_list)
    positional = {i: v for i, v in enumerate(inner_list)}
    named = _apply_keys(positional, keys_map)
    return json.dumps(_to_json_safe(named), ensure_ascii=False)


def write_mp(json_str: str, path: str) -> None:
    """Write a named-key JSON string as a Steam 1.5.x .mp file."""
    named = json.loads(json_str, object_hook=_from_json_safe)

    is_meta = len(named) <= 31 and "CultName" in named
    keys_map = META_KEYS if is_meta else SLOT_KEYS

    positional = _strip_keys(named, keys_map)

    if not positional:
        raise ValueError("No data to write")
    max_idx = max(positional.keys())
    inner_list = [positional.get(i) for i in range(max_idx + 1)]

    inner_bytes = _pack_value(inner_list)
    outer = _compress_lz4_outer(inner_bytes)
    outer_bytes = msgpack.packb(outer, use_bin_type=True)

    encrypted = _aes_encrypt(outer_bytes)
    with open(path, "wb") as f:
        f.write(encrypted)
