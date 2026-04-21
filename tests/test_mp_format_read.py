"""Tests for mp_format read path — using fixture save files."""
import json
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
MP_SLOT = FIXTURES / "synthetic_slot.mp"
MP_META = FIXTURES / "synthetic_meta.mp"


def test_read_mp_slot_returns_json():
    from mp_format import read_mp
    result = read_mp(str(MP_SLOT))
    data = json.loads(result)
    assert isinstance(data, dict)
    assert len(data) > 100


def test_read_mp_slot_has_known_fields():
    from mp_format import read_mp
    data = json.loads(read_mp(str(MP_SLOT)))
    assert "AllowSaving" in data


def test_read_mp_meta_returns_json():
    from mp_format import read_mp
    result = read_mp(str(MP_META))
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "CultName" in data
    assert "Day" in data
