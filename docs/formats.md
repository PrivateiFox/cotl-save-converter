# Save File Format Reference

Technical reference for the three save file formats handled by this tool.

---

## iOS / App Store

**Header:** `ZB` (2 bytes)  
**Body:** gzip-compressed UTF-8 JSON (may have a UTF-8 BOM — decoded with `utf-8-sig`)

```
┌──────┬───────────────────────────────────┐
│  ZB  │  gzip( JSON )                     │
└──────┴───────────────────────────────────┘
 2 bytes
```

The JSON is a flat object with all save fields at the top level (same schema as Steam).

---

## Steam pre-1.5 (`.json` files)

**Header:** `E` (1 byte)  
**Body:** 16-byte AES-128 key (stored in plaintext), 16-byte IV, then AES-128-CBC ciphertext.

```
┌───┬──────────────────┬──────────────────┬──────────────────────────────────┐
│ E │  AES key (16 B)  │  IV (16 B)       │  AES-128-CBC( PKCS7( JSON ) )    │
└───┴──────────────────┴──────────────────┴──────────────────────────────────┘
 1 B        16 B               16 B
```

The AES key is generated fresh on every save, stored unencrypted alongside the ciphertext. Decrypted content is PKCS7-unpadded UTF-8 JSON (same schema as iOS).

**Steam 1.5+ fallback:** The game loads `.json` saves when no `.mp` file is present alongside them. Rename or delete `slot_0.mp` / `meta_0.mp` and the game falls back automatically.

---

## Steam 1.5+ Woolhaven (`.mp` files)

Four nested layers. Outermost to innermost:

```
Layer 1 — AES envelope (same as pre-1.5)
Layer 2 — Outer MessagePack: list with LZ4 metadata + compressed blocks
Layer 3 — LZ4 block decompression → inner MessagePack bytes
Layer 4 — Inner MessagePack: flat positional array → apply field-name keys
```

### Layer 1 — AES envelope

Identical layout to the pre-1.5 format: `E` + 16-byte key + 16-byte IV + AES-128-CBC ciphertext.

### Layer 2 — Outer MessagePack

The decrypted bytes are a MessagePack **list**. The list has this structure:

```
outer[0]   ExtType(code=98)  — LZ4 metadata (uncompressed sizes, one per block)
outer[1]   bytes             — LZ4-compressed block 0
outer[2]   bytes             — LZ4-compressed block 1
...
```

The **ExtType(98) payload** is a stream of MessagePack-encoded integers, one per block. Each integer is the uncompressed byte count of the corresponding block:

```python
unpacker = msgpack.Unpacker()
unpacker.feed(ext.data)
sizes = list(unpacker)   # e.g. [65536, 65536, 43403]
```

This is the [MessagePack-CSharp](https://github.com/neuecc/MessagePack-CSharp) LZ4 block compression format used by Unity.

### Layer 3 — LZ4 block decompression

Each block (`outer[1]`, `outer[2]`, …) is decompressed with `lz4.block.decompress()` (block mode, **not** frame mode) using the corresponding size hint from Layer 2. The decompressed chunks are concatenated to produce the inner MessagePack bytes.

### Layer 4 — Inner MessagePack → named JSON

The inner bytes are a MessagePack **list** — a flat positional array where index `i` holds the value of field `i`. There are no field names in the binary data.

```
inner[0]   → AllowSaving
inner[1]   → DisableSaving
inner[2]   → PauseGameTime
...
inner[1394] → WoolhavenSkinsPurchased
```

Field names come from `keys.py`, which is auto-generated from [`lamb-mp-decoder/src/keys.ts`](https://github.com/matthewmmorrow/lamb-mp-decoder). There are two key maps:

| Map | Entries | Heuristic |
|---|---|---|
| `SLOT_KEYS` | 1394 | `len(inner_list) >= 100` |
| `META_KEYS` | 31 | `len(inner_list) < 100` |

Key map entries are either a plain string (field name) or a nested dict `{name, keys}` / `{name, keys: [sub_map]}` for nested objects and arrays of objects respectively. Unmapped indices (e.g. new Woolhaven fields not yet in `keys.ts`) are preserved as string keys (`"1395"`) so they round-trip without loss.

---

## Round-trip fidelity

### Integer encoding

MessagePack-CSharp encodes C# typed integers at their declared width (e.g. a `int` field holding value `8` is encoded as int32: `0xd2 0x00 0x00 0x00 0x08`). Python's msgpack always uses the minimal encoding (fixint: `0x08`). Both decode to the same value; the game is unaffected.

### Float encoding

C# `float` fields are encoded as float32 (4 bytes, `0xca`). C# `double` fields are encoded as float64 (8 bytes, `0xcb`). Python's msgpack decodes both as `float` (Python float is always 64-bit) losing the type distinction.

On write-back, each Python `float` is re-encoded as float32 iff it round-trips through float32 without precision loss:

```python
f32 = struct.unpack('>f', struct.pack('>f', value))[0]
use_float32 = (f32 == value)
```

This correctly recovers C# `float` vs `double` for all values observed in practice.

### Non-JSON-native types

Some save fields contain raw `bytes` or nested `ExtType` objects. These are preserved through JSON using marker dicts:

| Original type | JSON representation |
|---|---|
| `bytes` | `{"__b64__": "<base64>"}` |
| `ExtType(n, data)` | `{"__ext__": n, "__b64__": "<base64>"}` |
| `dict` with int keys | `{"__intmap__": [[key, value], ...]}` |

These markers are restored to their original types when reading back from JSON.

---

## Key generation

`gen_keys.py` parses `lamb-mp-decoder/src/keys.ts` and emits `keys.py`. Run it once whenever `keys.ts` is updated upstream:

```bash
python gen_keys.py path/to/lamb-mp-decoder/src/keys.ts keys.py
```

The TypeScript `Keys` type maps to Python dicts:

| TypeScript | Python |
|---|---|
| `0: "fieldName"` | `0: "fieldName"` |
| `5: {name: "pos", keys: vector2Keys}` | `5: {"name": "pos", "keys": VECTOR2_KEYS}` |
| `7: {name: "items", keys: [itemKeys]}` | `7: {"name": "items", "keys": [ITEM_KEYS]}` |
