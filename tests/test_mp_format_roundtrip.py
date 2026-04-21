"""
Binary round-trip tests for mp_format write path.

Strategy: read a synthetic .mp file, write it back to a temp file, decrypt both,
decompress LZ4, and compare the decoded inner msgpack structures.

Note on byte-level comparison:
  The raw inner bytes are NOT expected to be identical byte-for-byte because
  C# MessagePack-CSharp may encode integers with non-minimal encoding (e.g.,
  encoding the value 8 as int32/0xd2 rather than fixint/0x08) while Python's
  msgpack always uses minimal encoding.  What matters is that the decoded
  structures are identical — the game decodes values, not raw bytes.
"""
import json
import tempfile
from pathlib import Path

import msgpack

FIXTURES = Path(__file__).parent / "fixtures"
MP_SLOT = FIXTURES / "synthetic_slot.mp"
MP_META = FIXTURES / "synthetic_meta.mp"


def _decode_inner(path: str) -> list:
    """Decrypt .mp file and return the decoded inner msgpack list."""
    from mp_format import _aes_decrypt, _decompress_lz4_outer
    with open(path, "rb") as f:
        raw = f.read()
    plaintext = _aes_decrypt(raw)
    outer = msgpack.unpackb(plaintext, strict_map_key=False, raw=False)
    inner_bytes = _decompress_lz4_outer(outer)
    return msgpack.unpackb(inner_bytes, strict_map_key=False, raw=False)


def _inner_bytes(path: str) -> bytes:
    from mp_format import _aes_decrypt, _decompress_lz4_outer
    with open(path, "rb") as f:
        raw = f.read()
    outer = msgpack.unpackb(_aes_decrypt(raw), strict_map_key=False, raw=False)
    return _decompress_lz4_outer(outer)


def test_slot_roundtrip_decoded_structures_identical():
    """synthetic_slot: decode → JSON → re-encode → decode must give identical structure."""
    from mp_format import read_mp, write_mp
    json_str = read_mp(str(MP_SLOT))
    with tempfile.NamedTemporaryFile(suffix=".mp", delete=False) as tmp:
        tmp_path = tmp.name
    write_mp(json_str, tmp_path)
    assert _decode_inner(str(MP_SLOT)) == _decode_inner(tmp_path)


def test_meta_roundtrip_inner_bytes_identical():
    """synthetic_meta: round-trip must produce bit-for-bit identical inner bytes."""
    from mp_format import read_mp, write_mp
    json_str = read_mp(str(MP_META))
    with tempfile.NamedTemporaryFile(suffix=".mp", delete=False) as tmp:
        tmp_path = tmp.name
    write_mp(json_str, tmp_path)
    assert _inner_bytes(str(MP_META)) == _inner_bytes(tmp_path)


def test_slot_json_preserved_through_roundtrip():
    """JSON content must survive encode→decode→encode cycle unchanged."""
    from mp_format import read_mp, write_mp
    json1 = read_mp(str(MP_SLOT))
    with tempfile.NamedTemporaryFile(suffix=".mp", delete=False) as tmp:
        tmp_path = tmp.name
    write_mp(json1, tmp_path)
    assert json.loads(json1) == json.loads(read_mp(tmp_path))


def test_meta_json_preserved_through_roundtrip():
    """synthetic_meta JSON content must survive encode→decode→encode cycle unchanged."""
    from mp_format import read_mp, write_mp
    json1 = read_mp(str(MP_META))
    with tempfile.NamedTemporaryFile(suffix=".mp", delete=False) as tmp:
        tmp_path = tmp.name
    write_mp(json1, tmp_path)
    assert json.loads(json1) == json.loads(read_mp(tmp_path))
