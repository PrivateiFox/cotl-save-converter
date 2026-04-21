"""Tests for migrate.py logic."""
import json
import struct
from migrate import migrate_ios, migrate_slot, migrate_meta, SLOT_DEFAULTS, META_DEFAULTS

def test_migrate_slot_renames_fields():
    ios_data = {
        "PlayerDamageDealt": "123.45",
        "PlayerDamageReceived": "10.5"
    }
    migrated = migrate_slot(ios_data)
    # Renamed to lowercase
    assert "playerDamageDealt" in migrated
    assert "playerDamageReceived" in migrated
    # String "123.45" should become float 123.45 (subject to float32 precision)
    import pytest
    assert isinstance(migrated["playerDamageDealt"], float)
    assert migrated["playerDamageDealt"] == pytest.approx(123.45)
    assert migrated["playerDamageReceived"] == pytest.approx(10.5)

def test_migrate_slot_removes_ios_fields():
    ios_data = {
        "AppleArcade_DLC_Clothing": [1, 2],
        "Sinful_DLC_Clothing": [3],
        "KeepMe": True
    }
    migrated = migrate_slot(ios_data)
    assert "AppleArcade_DLC_Clothing" not in migrated
    assert "Sinful_DLC_Clothing" not in migrated
    assert migrated["KeepMe"] is True

def test_migrate_slot_adds_defaults():
    ios_data = {"CultName": "Test"}
    migrated = migrate_slot(ios_data)
    assert migrated["AnimalID"] == 0
    assert migrated["BeatenDungeon5"] is False
    assert "TwitchSettings" in migrated

def test_migrate_slot_transforms_items():
    ios_data = {
        "items": [
            {"type": 1, "quantity": 10, "QuantityReserved": 2},
            {"type": 2, "quantity": 5}
        ]
    }
    migrated = migrate_slot(ios_data)
    # Format: [[type, quantity, reserved], ...]
    assert "1162" in migrated
    assert migrated["1162"] == [[1, 10, 2], [2, 5, 0]]

def test_migrate_slot_transforms_item_selector():
    ios_data = {
        "ItemSelectorCategories": [
            {"Key": "Food", "TrackedItems": [1, 2], "MostRecentItem": 1}
        ]
    }
    migrated = migrate_slot(ios_data)
    # Format: [[Key, TrackedItems, MostRecentItem], ...]
    assert migrated["ItemSelectorCategories"] == [["Food", [1, 2], 1]]

def test_coerce_float32_precision():
    from migrate import _coerce_float32
    # A float64 that loses precision when converted to float32
    val = 0.1234567890123456789 
    coerced = _coerce_float32(val)
    # Check that it matches a float32 round-trip
    expected = struct.unpack(">f", struct.pack(">f", val))[0]
    assert coerced == expected
    assert coerced != val

def test_migrate_meta_removes_fields():
    meta_data = {
        "SaveDate": "2024-01-01",
        "CultName": "Meta"
    }
    migrated = migrate_meta(meta_data)
    assert "SaveDate" not in migrated
    assert migrated["CultName"] == "Meta"

def test_migrate_meta_adds_defaults():
    meta_data = {"CultName": "Meta"}
    migrated = migrate_meta(meta_data)
    assert migrated["ActivatedMajorDLC"] is False
    assert migrated["DLCPercentageCompleted"] == 3

def test_migrate_ios_auto_detects():
    # Meta: < 100 fields and has CultName
    meta_data = {"CultName": "Meta", "Field1": 1}
    assert "ActivatedMajorDLC" in migrate_ios(meta_data)
    
    # Slot: > 100 fields or no CultName (though slot usually has it too)
    slot_data = {"Field" + str(i): i for i in range(150)}
    assert "AnimalID" in migrate_ios(slot_data)
