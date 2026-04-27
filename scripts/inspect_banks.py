#!/usr/bin/env python3
"""Inspect XSB/XWB bank files without extracting or modifying audio data."""

from __future__ import annotations

import argparse
import json
import re
import struct
from pathlib import Path
from typing import Any


XWB_SEGMENTS = [
    "bank_data",
    "entry_metadata",
    "seek_tables",
    "entry_names",
    "wave_data",
]
XWB_FORMAT_TAGS = {
    0: "PCM",
    1: "XMA",
    2: "ADPCM",
    3: "WMA",
}


def u16(data: bytes, offset: int) -> int | None:
    if offset + 2 > len(data):
        return None
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int | None:
    if offset + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, offset)[0]


def c_string(data: bytes, offset: int, max_len: int) -> str:
    raw = data[offset : offset + max_len]
    raw = raw.split(b"\x00", 1)[0]
    return raw.decode("ascii", errors="replace")


def find_ascii_strings(data: bytes, min_len: int = 4) -> list[dict[str, Any]]:
    rows = []
    pattern = rb"[A-Za-z0-9_]{%d,}" % min_len
    for match in re.finditer(pattern, data):
        rows.append({"offset": match.start(), "text": match.group().decode("ascii", errors="replace")})
    return rows


def decode_xwb_format(raw: int) -> dict[str, Any]:
    return {
        "raw": raw,
        "tag": raw & 0x3,
        "tag_name": XWB_FORMAT_TAGS.get(raw & 0x3, "unknown"),
        "channels_guess": (raw >> 2) & 0x7,
        "sample_rate_guess": (raw >> 5) & 0x3FFFF,
        "block_align_guess": (raw >> 23) & 0xFF,
        "bits_flag_guess": (raw >> 31) & 0x1,
    }


def inspect_xwb(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if data[:4] != b"WBND":
        return {"file": str(path), "kind": "xwb", "error": "missing WBND signature"}

    version = u32(data, 0x04)
    header_version = u32(data, 0x08)
    segments = []
    for index, name in enumerate(XWB_SEGMENTS):
        offset = 0x0C + index * 8
        segment_offset = u32(data, offset)
        segment_length = u32(data, offset + 4)
        segments.append(
            {
                "index": index,
                "name": name,
                "offset": segment_offset,
                "length": segment_length,
                "end": (
                    segment_offset + segment_length
                    if segment_offset is not None and segment_length is not None
                    else None
                ),
            }
        )

    bank_data: dict[str, Any] = {}
    bank_segment = segments[0]
    bank_offset = bank_segment["offset"]
    if bank_offset is not None and bank_segment["length"] and bank_offset + 96 <= len(data):
        bank_data = {
            "flags": u32(data, bank_offset),
            "entry_count": u32(data, bank_offset + 4),
            "bank_name": c_string(data, bank_offset + 8, 64),
            "entry_metadata_element_size": u32(data, bank_offset + 72),
            "entry_name_element_size": u32(data, bank_offset + 76),
            "alignment": u32(data, bank_offset + 80),
            "compact_format": u32(data, bank_offset + 84),
            "build_time_raw_low": u32(data, bank_offset + 88),
            "build_time_raw_high": u32(data, bank_offset + 92),
        }

    entries = []
    entry_segment = segments[1]
    entry_offset = entry_segment["offset"]
    entry_size = int(bank_data.get("entry_metadata_element_size") or 24)
    entry_count = int(bank_data.get("entry_count") or 0)
    if entry_offset is not None and entry_size >= 24:
        for index in range(entry_count):
            offset = entry_offset + index * entry_size
            if offset + 24 > len(data):
                break
            format_raw = u32(data, offset + 4)
            entries.append(
                {
                    "index": index,
                    "offset": offset,
                    "flags_and_duration_raw": u32(data, offset),
                    "format": decode_xwb_format(format_raw or 0),
                    "play_region_offset": u32(data, offset + 8),
                    "play_region_length": u32(data, offset + 12),
                    "loop_region_offset": u32(data, offset + 16),
                    "loop_region_length": u32(data, offset + 20),
                }
            )

    wave_segment = segments[4]
    wave_data_fills_file = (
        wave_segment["offset"] is not None
        and wave_segment["length"] is not None
        and wave_segment["offset"] + wave_segment["length"] == len(data)
    )

    return {
        "file": str(path),
        "kind": "xwb",
        "size_bytes": len(data),
        "signature": data[:4].decode("ascii", errors="replace"),
        "version": version,
        "header_version": header_version,
        "segments": segments,
        "bank_data": bank_data,
        "entries": entries,
        "strings": find_ascii_strings(data[: max(256, int(wave_segment["offset"] or 0))]),
        "wave_data_fills_file": wave_data_fills_file,
    }


def inspect_xsb(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if data[:4] != b"SDBK":
        return {"file": str(path), "kind": "xsb", "error": "missing SDBK signature"}

    header_words = []
    for offset in range(0, min(len(data), 0x50), 4):
        value = u32(data, offset)
        header_words.append({"offset": offset, "u32": value})

    strings = find_ascii_strings(data)
    likely_names = [row for row in strings if row["text"].startswith(("M_", "_"))]

    return {
        "file": str(path),
        "kind": "xsb",
        "size_bytes": len(data),
        "signature": data[:4].decode("ascii", errors="replace"),
        "version_u16": u16(data, 0x04),
        "header_version_u16": u16(data, 0x06),
        "guid_or_hash_hex": data[0x08:0x18].hex(" "),
        "header_words": header_words,
        "strings": strings,
        "likely_names": likely_names,
    }


def inspect_file(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".xwb":
        return inspect_xwb(path)
    if suffix == ".xsb":
        return inspect_xsb(path)
    return {"file": str(path), "kind": "unknown", "error": "unsupported extension"}


def collect_paths(path: Path) -> list[Path]:
    if path.is_dir():
        return sorted([item for item in path.iterdir() if item.suffix.lower() in {".xwb", ".xsb"}])
    return [path]


def print_markdown(results: list[dict[str, Any]]) -> None:
    print("# Bank Inspection")
    print()
    for result in results:
        print(f"## {Path(result['file']).name}")
        print()
        if result.get("error"):
            print(f"- error: {result['error']}")
            print()
            continue

        print(f"- kind: `{result['kind']}`")
        print(f"- size_bytes: `{result['size_bytes']}`")
        print(f"- signature: `{result['signature']}`")
        if result["kind"] == "xwb":
            print(f"- version: `{result['version']}`")
            print(f"- header_version: `{result['header_version']}`")
            print(f"- wave_data_fills_file: `{result['wave_data_fills_file']}`")
            print()
            print("| segment | offset | length | end |")
            print("|---|---:|---:|---:|")
            for segment in result["segments"]:
                print(
                    f"| `{segment['name']}` | {segment['offset']} | "
                    f"{segment['length']} | {segment['end']} |"
                )
            print()
            bank = result["bank_data"]
            if bank:
                print(
                    "- bank_data: "
                    f"name=`{bank['bank_name']}`, entry_count=`{bank['entry_count']}`, "
                    f"entry_metadata_element_size=`{bank['entry_metadata_element_size']}`, "
                    f"entry_name_element_size=`{bank['entry_name_element_size']}`, "
                    f"alignment=`{bank['alignment']}`, compact_format=`{bank['compact_format']}`"
                )
            for entry in result["entries"]:
                fmt = entry["format"]
                print(
                    "- entry "
                    f"{entry['index']}: format=`{fmt['tag_name']}` raw=`0x{fmt['raw']:08x}`, "
                    f"channels_guess=`{fmt['channels_guess']}`, "
                    f"sample_rate_guess=`{fmt['sample_rate_guess']}`, "
                    f"block_align_guess=`{fmt['block_align_guess']}`, "
                    f"play_region=({entry['play_region_offset']}, {entry['play_region_length']}), "
                    f"loop_region=({entry['loop_region_offset']}, {entry['loop_region_length']})"
                )
        else:
            print(f"- version_u16: `{result['version_u16']}`")
            print(f"- header_version_u16: `{result['header_version_u16']}`")
            print(f"- guid_or_hash_hex: `{result['guid_or_hash_hex']}`")
            if result["likely_names"]:
                print("- likely names:")
                for row in result["likely_names"]:
                    print(f"  - `0x{row['offset']:04x}`: `{row['text']}`")
        if result.get("strings"):
            print("- strings:")
            for row in result["strings"][:20]:
                print(f"  - `0x{row['offset']:04x}`: `{row['text']}`")
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect XSB/XWB bank files.")
    parser.add_argument("path", type=Path, help="Bank file or folder containing .xsb/.xwb files.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = collect_paths(args.path)
    if not paths:
        print(f"No .xsb/.xwb files found: {args.path}")
        return 1

    results = [inspect_file(path) for path in paths]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_markdown(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
