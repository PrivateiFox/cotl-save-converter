#!/usr/bin/env python3
"""
Cult of the Lamb save converter
Supports iOS (ZB+gzip) and Steam (E+AES-128-CBC) formats.
"""

import argparse
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
    text = read_ios(args.infile)
    if args.pretty:
        try:
            text = json.dumps(json.loads(text), indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
    if args.outfile:
        with open(args.outfile, "w", encoding="utf-8") as f:
            f.write(text)
        size = len(text.encode("utf-8"))
        print(f"Written to {args.outfile} ({size:,} bytes)")
    else:
        print(text)


def cmd_ios_to_steam(args):
    text = read_ios(args.infile)
    write_steam(text, args.outfile)
    print(f"Converted {args.infile} → {args.outfile} (Steam format)")


def cmd_steam_to_json(args):
    text = read_steam(args.infile)
    if args.pretty:
        try:
            text = json.dumps(json.loads(text), indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
    if args.outfile:
        with open(args.outfile, "w", encoding="utf-8") as f:
            f.write(text)
        size = len(text.encode("utf-8"))
        print(f"Written to {args.outfile} ({size:,} bytes)")
    else:
        print(text)


def cmd_json_to_steam(args):
    with open(args.infile, "r", encoding="utf-8-sig") as f:
        text = f.read()
    write_steam(text, args.outfile)
    print(f"Encrypted {args.infile} → {args.outfile} (Steam format)")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=__doc__.strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_ios_to_json = subparsers.add_parser("ios_to_json", help="Decompress iOS save to JSON")
    p_ios_to_json.add_argument("infile", help="Input file")
    p_ios_to_json.add_argument("outfile", nargs="?", help="Output file")
    p_ios_to_json.add_argument("--pretty", action="store_true", help="Pretty print JSON")
    p_ios_to_json.set_defaults(func=cmd_ios_to_json)

    p_ios_to_steam = subparsers.add_parser("ios_to_steam", help="Convert iOS save to Steam format")
    p_ios_to_steam.add_argument("infile", help="Input file")
    p_ios_to_steam.add_argument("outfile", help="Output file")
    p_ios_to_steam.set_defaults(func=cmd_ios_to_steam)

    p_steam_to_json = subparsers.add_parser("steam_to_json", help="Decrypt Steam save to JSON")
    p_steam_to_json.add_argument("infile", help="Input file")
    p_steam_to_json.add_argument("outfile", nargs="?", help="Output file")
    p_steam_to_json.add_argument("--pretty", action="store_true", help="Pretty print JSON")
    p_steam_to_json.set_defaults(func=cmd_steam_to_json)

    p_json_to_steam = subparsers.add_parser("json_to_steam", help="Encrypt JSON to Steam format")
    p_json_to_steam.add_argument("infile", help="Input file")
    p_json_to_steam.add_argument("outfile", help="Output file")
    p_json_to_steam.set_defaults(func=cmd_json_to_steam)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
