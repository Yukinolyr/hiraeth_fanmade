#!/usr/bin/env python3
"""Inspect NOSTALGIA music_list.xml metadata."""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


DEFAULT_FIELDS = [
    "basename",
    "title",
    "title_kana",
    "artist",
    "artist_kana",
    "category_flag",
    "primary_category",
    "bemani_flag",
    "bemani_category",
    "add_ver",
    "level_normal",
    "level_hard",
    "level_extreme",
    "level_real",
    "volume_bgm",
    "volume_key",
    "start_date",
    "end_date",
    "expiration_date",
    "real_start_date",
    "real_end_date",
    "real_release_code",
    "force_unlock_date",
    "real_force_unlock_date",
]


def load_music_list(path: Path) -> ET.Element:
    raw = path.read_bytes()
    # Expat in Python's stdlib does not handle Shift_JIS XML directly.
    text = raw.decode("shift_jis", errors="replace")
    text = re.sub(r"<\?xml[^>]*\?>", "<?xml version='1.0'?>", text, count=1)
    return ET.fromstring(text)


def spec_to_dict(spec: ET.Element, fields: list[str]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "index": spec.attrib.get("index"),
    }
    for field in fields:
        row[field] = spec.findtext(field)
    row["tag_ids"] = [item.text for item in spec.findall("./tag_list_data/id")]
    return row


def find_specs(root: ET.Element, basenames: list[str]) -> list[dict[str, Any]]:
    lookup = {name.lower() for name in basenames}
    rows = []
    for spec in root.findall("music_spec"):
        basename = spec.findtext("basename")
        if basename and basename.lower() in lookup:
            rows.append(spec_to_dict(spec, DEFAULT_FIELDS))
    return rows


def all_specs(root: ET.Element) -> list[dict[str, Any]]:
    return [spec_to_dict(spec, DEFAULT_FIELDS) for spec in root.findall("music_spec")]


def print_markdown(root: ET.Element, rows: list[dict[str, Any]]) -> None:
    print("# Music List Summary")
    print()
    print(f"- revision: `{root.attrib.get('revision', '')}`")
    print(f"- release_code: `{root.attrib.get('release_code', '')}`")
    print(f"- music_spec_count: `{len(root.findall('music_spec'))}`")
    print()

    if not rows:
        print("No matching entries.")
        return

    print("| index | basename | title | artist | levels N/H/E/R | bgm | key | start | real_start |")
    print("|---:|---|---|---|---|---:|---:|---|---|")
    for row in rows:
        levels = "/".join(
            [
                row.get("level_normal") or "",
                row.get("level_hard") or "",
                row.get("level_extreme") or "",
                row.get("level_real") or "",
            ]
        )
        print(
            f"| {row.get('index') or ''} | `{row.get('basename') or ''}` | "
            f"{row.get('title') or ''} | {row.get('artist') or ''} | "
            f"{levels} | {row.get('volume_bgm') or ''} | {row.get('volume_key') or ''} | "
            f"{row.get('start_date') or ''} | {row.get('real_start_date') or ''} |"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect music_list.xml.")
    parser.add_argument("path", type=Path, help="Path to music_list.xml.")
    parser.add_argument(
        "basename",
        nargs="*",
        help="Optional basename(s), e.g. M_C0047_chopin_etude10_4.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--all", action="store_true", help="Print all entries.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = load_music_list(args.path)
    if args.all:
        rows = all_specs(root)
    elif args.basename:
        rows = find_specs(root, args.basename)
    else:
        rows = []

    if args.json:
        print(
            json.dumps(
                {
                    "revision": root.attrib.get("revision"),
                    "release_code": root.attrib.get("release_code"),
                    "music_spec_count": len(root.findall("music_spec")),
                    "entries": rows,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_markdown(root, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
