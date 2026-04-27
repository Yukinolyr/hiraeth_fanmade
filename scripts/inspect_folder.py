#!/usr/bin/env python3
"""Create a read-only inventory for a song folder."""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_magic(path: Path, length: int = 16) -> bytes:
    with path.open("rb") as file_obj:
        return file_obj.read(length)


def printable_ascii(data: bytes) -> str:
    return "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in data)


def detect_kind(path: Path, magic: bytes) -> str:
    suffix = path.suffix.lower()
    if suffix == ".xml" or magic.startswith(b"\xef\xbb\xbf<?xml") or magic.startswith(b"<?xml"):
        return "chart xml"
    if suffix == ".xwb":
        return "xact wave bank candidate"
    if suffix == ".xsb":
        return "xact sound bank candidate"
    if not suffix:
        return "unknown"
    return f"unknown {suffix}"


def xml_summary(path: Path) -> dict[str, Any] | None:
    if path.suffix.lower() != ".xml":
        return None
    root = ET.parse(path).getroot()
    note_data = root.find("note_data")
    event_data = root.find("event_data")
    beat_data = root.find("beat_data")
    return {
        "root": root.tag,
        "top_level_nodes": [child.tag for child in root],
        "note_count": len(note_data.findall("note")) if note_data is not None else 0,
        "event_count": len(event_data.findall("event")) if event_data is not None else 0,
        "beat_count": len(beat_data.findall("beat")) if beat_data is not None else 0,
    }


def inspect_file(path: Path, base: Path) -> dict[str, Any]:
    magic = read_magic(path)
    stat = path.stat()
    return {
        "path": path.relative_to(base).as_posix(),
        "size_bytes": stat.st_size,
        "extension": path.suffix.lower(),
        "magic_hex": magic.hex(" "),
        "magic_ascii": printable_ascii(magic),
        "sha256": sha256_file(path),
        "kind": detect_kind(path, magic),
        "xml": xml_summary(path),
    }


def inspect_folder(path: Path) -> list[dict[str, Any]]:
    files = [item for item in sorted(path.rglob("*")) if item.is_file()]
    return [inspect_file(file_path, path) for file_path in files]


def print_markdown(folder: Path, rows: list[dict[str, Any]]) -> None:
    print(f"# File Inventory: {folder}")
    print()
    print("| path | size | ext | kind | magic ascii | magic hex | sha256 |")
    print("|---|---:|---|---|---|---|---|")
    for row in rows:
        print(
            f"| `{row['path']}` | {row['size_bytes']} | `{row['extension']}` | "
            f"{row['kind']} | `{row['magic_ascii']}` | `{row['magic_hex']}` | "
            f"`{row['sha256']}` |"
        )

    xml_rows = [row for row in rows if row["xml"] is not None]
    if xml_rows:
        print()
        print("## XML Summary")
        print()
        print("| path | root | top-level nodes | notes | events | beats |")
        print("|---|---|---|---:|---:|---:|")
        for row in xml_rows:
            xml = row["xml"]
            print(
                f"| `{row['path']}` | `{xml['root']}` | "
                f"`{', '.join(xml['top_level_nodes'])}` | "
                f"{xml['note_count']} | {xml['event_count']} | {xml['beat_count']} |"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect files in a song folder.")
    parser.add_argument("path", type=Path, help="Folder to inspect.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of Markdown.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    folder = args.path
    if not folder.exists() or not folder.is_dir():
        print(f"Folder not found: {folder}")
        return 1

    rows = inspect_folder(folder)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print_markdown(folder, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
