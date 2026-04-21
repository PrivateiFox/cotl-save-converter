"""
gen_synthetic_saves.py — Generate non-derivative synthetic save files for testing.

Produces:
1. synthetic_ios_slot: ZB + gzip JSON (pre-migration schema)
2. synthetic_slot.mp:  Steam 1.5.x encrypted/compressed (post-migration schema)
3. synthetic_meta.mp:  Steam 1.5.x meta save
"""
import json
import os
from pathlib import Path

# Add project root to path so we can import our modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

import convert
import mp_format
from migrate import SLOT_DEFAULTS, META_DEFAULTS

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURES.mkdir(exist_ok=True)

def gen_ios_slot_json():
    """Generate a 'Named' JSON dict using the older iOS 1.4.x schema."""
    return {
        "CultName": "Synthetic Cult",
        "Day": 10,
        "TimeInGame": 3600.0,
        "items": [
            {"type": 0, "quantity": 100, "QuantityReserved": 0},
            {"type": 1, "quantity": 50},
        ],
        "PlayerDamageDealt": "123.45", # iOS uses string for this
        "PlayerDamageReceived": 10.0,
        "ItemSelectorCategories": [
            {"Key": "Seeds", "TrackedItems": [0, 1], "MostRecentItem": 0}
        ],
        "AppleArcade_DLC_Clothing": [1, 2, 3], # To be removed
        "Followers": [
            {
                "ID": 1,
                "_name": "Follower 1",
                "Age": 20,
                "Thoughts": [{"ThoughtType": 1, "Duration": 100}]
            }
        ],
        "BaseStructures": [
            {"Type": 0, "ID": 1, "GridX": 0, "GridY": 0}
        ]
    }

def gen_steam_slot_json():
    """Generate a 'Named' JSON dict using the Steam 1.5.x schema (post-migration)."""
    data = {
        "CultName": "Steam Cult",
        "Day": 20,
        "TimeInGame": 7200.0,
        "1162": [[0, 500, 0], [1, 250, 10]], # items positional format
        "playerDamageDealt": 456.78,
        "playerDamageReceived": 20.0,
        "ItemSelectorCategories": [
            ["Seeds", [0, 1], 0]
        ],
        "Followers": [
            {
                "ID": 1,
                "_name": "Steam Follower",
                "Age": 30,
                "Thoughts": [{"ThoughtType": 2, "Duration": 50}]
            }
        ],
        "BaseStructures": [
            {"Type": 1, "ID": 10, "GridX": 5, "GridY": 5}
        ],
        "AllowSaving": True
    }
    # Fill in some defaults to make it "populated"
    for k, v in SLOT_DEFAULTS.items():
        if k not in data:
            data[k] = v
    return data

def gen_steam_meta_json():
    """Generate a 'Named' JSON dict for a meta save."""
    data = {
        "CultName": "Meta Cult",
        "Day": 20,
        "SaveUniqueID": "synth-uuid-123"
    }
    for k, v in META_DEFAULTS.items():
        if k not in data:
            data[k] = v
    return data

def main():
    print("Generating synthetic test artifacts...")

    # 1. iOS Slot (Pre-migration)
    ios_json = json.dumps(gen_ios_slot_json())
    convert.write_ios(ios_json, str(FIXTURES / "synthetic_slot_ios"))
    print(f"  Created {FIXTURES / 'synthetic_slot_ios'}")

    # 2. Steam MP Slot (Post-migration)
    steam_json = json.dumps(gen_steam_slot_json())
    mp_format.write_mp(steam_json, str(FIXTURES / "synthetic_slot.mp"))
    print(f"  Created {FIXTURES / 'synthetic_slot.mp'}")

    # 3. Steam MP Meta
    meta_json = json.dumps(gen_steam_meta_json())
    mp_format.write_mp(meta_json, str(FIXTURES / "synthetic_meta.mp"))
    print(f"  Created {FIXTURES / 'synthetic_meta.mp'}")

if __name__ == "__main__":
    main()
