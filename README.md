# cotl-save-converter

Convert *Cult of the Lamb* save files between iOS/App Store (ZB+gzip+JSON) and Steam (AES-CBC+JSON) formats.

Tested with iOS version **1.4.12** → Steam version **1.5.25**.

## How it works

| Platform | Format |
|---|---|
| iOS / App Store | `ZB` header + gzip-compressed JSON |
| Steam (pre-1.5) | `E` header + 16-byte AES key + 16-byte IV + AES-128-CBC encrypted JSON |
| Steam (1.5+ Woolhaven) | Same AES wrapper, but inner data is MessagePack + LZ4 — **not supported for writing** |

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

### iOS → Steam (the main use case)

```bash
# Convert the save slot
uv run python convert.py ios_to_steam path/to/ios/slot_0 ~/Library/Application\ Support/Massive\ Monster/Cult\ Of\ The\ Lamb/saves/slot_0.json

# Convert the slot metadata (shown on the load screen)
uv run python convert.py ios_to_steam path/to/ios/meta_0 ~/Library/Application\ Support/Massive\ Monster/Cult\ Of\ The\ Lamb/saves/meta_0.json

# Convert global persistence (unlocks Survival Mode etc.)
uv run python convert.py ios_to_steam path/to/ios/persistence ~/Library/Application\ Support/Massive\ Monster/Cult\ Of\ The\ Lamb/saves/persistence.json
```

Then, if you're on Steam 1.5+, **delete or move `slot_0.mp` and `meta_0.mp`** from the saves folder. The game will load the JSON files instead.

> **Note:** Back up your existing Steam saves before overwriting anything.

### Inspect a save as JSON

```bash
# Compact (default)
uv run python convert.py ios_to_json path/to/ios/slot_0

# Pretty-printed, written to a file
uv run python convert.py ios_to_json path/to/ios/slot_0 slot_0.json --pretty
```

### Decrypt a Steam JSON save

```bash
uv run python convert.py steam_to_json path/to/steam/slot_0 slot_0.json --pretty
```

### Re-encrypt an edited JSON back to Steam format

```bash
uv run python convert.py json_to_steam slot_0_edited.json path/to/steam/slot_0.json
```

## All commands

```
ios_to_json   <infile> [outfile] [--pretty]   Decompress iOS save to JSON
ios_to_steam  <infile> <outfile>              Convert iOS save to Steam format
steam_to_json <infile> [outfile] [--pretty]   Decrypt Steam save to JSON
json_to_steam <infile> <outfile>              Encrypt JSON to Steam format
```
