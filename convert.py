#!/usr/bin/env python3
"""
Cult of the Lamb save converter
Supports iOS (ZB+gzip) and Steam (E+AES-128-CBC) formats.

Usage:
  python convert.py ios_to_json   <infile> [outfile]
  python convert.py ios_to_steam  <infile> <outfile>
  python convert.py steam_to_json <infile> [outfile]
  python convert.py json_to_steam <infile> <outfile>
"""

import gzip
import json
import secrets
import sys

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding


# ── iOS (ZB + gzip) ──────────────────────────────────────────────────────────

def read_ios(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    if data[:2] != b"ZB":
        raise ValueError(f"{path}: not an iOS save (expected 'ZB' header, got {data[:2]!r})")
    return gzip.decompress(data[2:]).decode("utf-8-sig")


def write_ios(json_str: str, path: str) -> None:
    compressed = gzip.compress(json_str.encode("utf-8"))
    with open(path, "wb") as f:
        f.write(b"ZB")
        f.write(compressed)


# ── Steam (E + AES-128-CBC) ───────────────────────────────────────────────────

def read_steam(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    if data[0:1] != b"E":
        raise ValueError(f"{path}: not a Steam save (expected 'E' header, got {data[0:1]!r})")
    key = data[1:17]
    iv  = data[17:33]
    ciphertext = data[33:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    dec = cipher.decryptor()
    padded = dec.update(ciphertext) + dec.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return (unpadder.update(padded) + unpadder.finalize()).decode("utf-8-sig")


def write_steam(json_str: str, path: str) -> None:
    key = secrets.token_bytes(16)
    iv  = secrets.token_bytes(16)
    padder = padding.PKCS7(128).padder()
    plaintext = json_str.encode("utf-8")
    padded = padder.update(plaintext) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    enc = cipher.encryptor()
    ciphertext = enc.update(padded) + enc.finalize()
    with open(path, "wb") as f:
        f.write(b"E")
        f.write(key)
        f.write(iv)
        f.write(ciphertext)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_ios_to_json(args):
    if len(args) < 1:
        die("Usage: ios_to_json <infile> [outfile] [--pretty]")
    pretty = "--pretty" in args
    args = [a for a in args if a != "--pretty"]
    src = args[0]
    text = read_ios(src)
    if pretty:
        try:
            text = json.dumps(json.loads(text), indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
    if len(args) >= 2:
        with open(args[1], "w", encoding="utf-8") as f:
            f.write(text)
        size = len(text.encode("utf-8"))
        print(f"Written to {args[1]} ({size:,} bytes)")
    else:
        print(text)


def cmd_ios_to_steam(args):
    if len(args) < 2:
        die("Usage: ios_to_steam <infile> <outfile>")
    text = read_ios(args[0])
    write_steam(text, args[1])
    print(f"Converted {args[0]} → {args[1]} (Steam format)")


def cmd_steam_to_json(args):
    if len(args) < 1:
        die("Usage: steam_to_json <infile> [outfile] [--pretty]")
    pretty = "--pretty" in args
    args = [a for a in args if a != "--pretty"]
    src = args[0]
    text = read_steam(src)
    if pretty:
        try:
            text = json.dumps(json.loads(text), indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
    if len(args) >= 2:
        with open(args[1], "w", encoding="utf-8") as f:
            f.write(text)
        size = len(text.encode("utf-8"))
        print(f"Written to {args[1]} ({size:,} bytes)")
    else:
        print(text)


def cmd_json_to_steam(args):
    if len(args) < 2:
        die("Usage: json_to_steam <infile> <outfile>")
    with open(args[0], "r", encoding="utf-8-sig") as f:
        text = f.read()
    write_steam(text, args[1])
    print(f"Encrypted {args[0]} → {args[1]} (Steam format)")


# ── Entry point ───────────────────────────────────────────────────────────────

COMMANDS = {
    "ios_to_json":   cmd_ios_to_json,
    "ios_to_steam":  cmd_ios_to_steam,
    "steam_to_json": cmd_steam_to_json,
    "json_to_steam": cmd_json_to_steam,
}


def die(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print((__doc__ or "").strip())
        sys.exit(0 if len(sys.argv) == 1 else 1)
    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
