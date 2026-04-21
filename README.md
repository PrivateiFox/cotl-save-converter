# cotl-save-converter

Convert *Cult of the Lamb* save files between iOS/App Store (ZB+gzip+JSON) and Steam (AES-CBC+JSON) formats.

Tested with iOS version **1.4.12** → Steam version **1.5.25**.

## How it works

| Platform | Format |
|---|---|
| iOS / App Store | `ZB` header + gzip-compressed JSON |
| Steam (pre-1.5) | `E` header + 16-byte AES key + 16-byte IV + AES-128-CBC encrypted JSON |
| Steam (1.5+ Woolhaven) | Same AES wrapper, but inner data is MessagePack + LZ4 |

The 1.5+ Steam client will load a pre-1.5 JSON save if no `.mp` file exists alongside it. Delete (or move) `slot_0.mp` / `meta_0.mp` and the game falls back to the JSON files automatically.

## Save file locations

### Steam (Mac)
```
~/Library/Application Support/Massive Monster/Cult Of The Lamb/saves/
```

Files: `slot_0`, `slot_0.mp`, `meta_0`, `meta_0.mp`, `persistence.json`, `settings.json`

### App Store (Mac)
```
~/Library/Containers/com.devolverdigital.cultofthelamb/
```

### iOS (via iMazing or similar)
```
<app data>/Documents/user/
```

Files: `slot_0`, `meta_0`, `persistence`, `settings`, `Prefs.dict`

## Requirements

- Python 3.8+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
git clone https://github.com/PrivateiFox/cotl-save-converter
cd cotl-save-converter
uv sync
```

## Usage

You can see all available commands and options by running:
```bash
uv run python convert.py --help
```

### iOS → Steam (the main use case)

Steam files (even the encrypted ones) should end in `.json` for the game to recognize them as fallback saves. iOS files typically have no suffix.

```bash
# Convert the save slot
uv run python convert.py ios_to_steam path/to/ios/slot_0 path/to/steam/slot_0.json

# Convert the slot metadata (shown on the load screen)
uv run python convert.py ios_to_steam path/to/ios/meta_0 path/to/steam/meta_0.json

# Convert global persistence (unlocks Survival Mode etc.)
uv run python convert.py ios_to_steam path/to/ios/persistence path/to/steam/persistence.json
```

Then, if you're on Steam 1.5+, **delete or move any existing `.mp` files** (like `slot_0.mp`) from the saves folder. The game will load the `.json` files instead.

> **Note:** Always back up your existing saves before overwriting them.

### Inspect a save as JSON

```bash
# Decompress iOS save to JSON (prints to terminal)
uv run python convert.py ios_to_json path/to/ios/slot_0

# Decompress iOS save to a pretty-printed JSON file
uv run python convert.py ios_to_json path/to/ios/slot_0 slot_0_dec.json --pretty

# Decrypt a Steam save to a pretty-printed JSON file
uv run python convert.py steam_to_json path/to/steam/slot_0.json slot_0_dec.json --pretty
```

### Re-encrypt an edited JSON back to Steam format

```bash
uv run python convert.py json_to_steam slot_0_dec.json path/to/steam/slot_0.json
```

### Steam 1.5.x .mp format (Woolhaven)

Steam 1.5+ uses `.mp` (MessagePack + LZ4) saves. These commands read and write `.mp` files directly — useful for inspecting or editing an existing Steam save.

```bash
# Decrypt a 1.5.x .mp save to JSON
uv run python convert.py mp_to_json path/to/slot_0.mp slot_0_dec.json --pretty

# Re-encode an edited JSON back to .mp
uv run python convert.py json_to_mp slot_0_dec.json path/to/slot_0.mp
```

**iOS → Steam 1.5.x:** Use `ios_to_steam` (produces a `.json` file) and delete the `.mp` files — the game will run its own migration when it loads the JSON save for the first time, which correctly initialises all 1.5.x fields.

```bash
uv run python convert.py ios_to_steam path/to/ios/slot_0 path/to/steam/slot_0.json
uv run python convert.py ios_to_steam path/to/ios/meta_0 path/to/steam/meta_0.json
# Then delete slot_0.mp and meta_0.mp from the saves folder
```


## Related tools

- **[CotlSaveExtractorLoader](https://github.com/osoclos/CotlSaveExtractorLoader)** — BepInEx plugin for Steam 1.5.x. Hooks into the game process to auto-extract `.mp` saves to JSON on every in-game save event, and can force the game to always load JSON. Useful if you want a live extraction workflow rather than running a script manually.

- **[lamb-mp-decoder](https://github.com/matthewmmorrow/lamb-mp-decoder)** — TypeScript library that decodes the 1.5.x `.mp` format (AES → MessagePack → LZ4). The key mapping in `keys.ts` is what powers this tool's field-name resolution.

- **[COTL-SaveDecryptor](https://github.com/Pentalex/COTL-SaveDecryptor)** — Browser-based decryptor for the pre-1.5 Steam JSON format.
