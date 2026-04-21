from keys import SLOT_KEYS, META_KEYS


def test_slot_keys_count():
    assert len(SLOT_KEYS) >= 1394


def test_slot_keys_zero():
    assert SLOT_KEYS[0] == "AllowSaving"


def test_slot_keys_string_entry():
    assert isinstance(SLOT_KEYS[1], str)


def test_slot_keys_nested_entry():
    # Entry 1352 is {name: "bestFriendAnimal", keys: [ranchAnimalKeys]}
    entry = SLOT_KEYS[1352]
    assert isinstance(entry, dict)
    assert entry["name"] == "bestFriendAnimal"
    assert isinstance(entry["keys"], list)


def test_meta_keys_count():
    assert len(META_KEYS) == 31


def test_meta_keys_zero():
    assert META_KEYS[0] == "CultName"


def test_meta_keys_last():
    assert META_KEYS[30] == "ActivatedMajorDLC"
