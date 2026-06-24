#!/usr/bin/env python3
"""Add the minimal tested event_data block to a NOSTALGIA XML chart."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


TOP_LEVEL_ORDER = [
    "header",
    "note_data",
    "event_data",
    "beat_data",
    "track_info",
    "velocity_zone_data",
]
FIRST_BPM_RE = re.compile(r"<first_bpm\b[^>]*>\s*(-?\d+)\s*</first_bpm>")


class EventDataError(ValueError):
    """Raised when event_data cannot be added safely."""


def find_block(root_body: str, tag: str) -> str | None:
    pattern = re.compile(rf"  <{tag}\b.*?</{tag}>\n?", re.DOTALL)
    match = pattern.search(root_body)
    if match is None:
        return None
    return match.group(0)


def build_event_data(fixed_bpm: str) -> str:
    events = [
        (0, 0, 0, fixed_bpm),
        (1, 0, 1, "120"),
        (2, 0, 2, "11"),
        (3, 80, 3, "20"),
        (4, 80, 4, "61"),
        (5, 80, 5, "16"),
        (6, 161, 6, "117"),
        (7, 161, 7, "0"),
        (8, 161, 8, "100"),
    ]
    lines = ["  <event_data>\n"]
    for index, start, type_value, value in events:
        lines.extend(
            [
                "    <event>\n",
                f"      <index __type=\"s32\">{index}</index>\n",
                f"      <start_timing_msec __type=\"s32\">{start}</start_timing_msec>\n",
                f"      <type __type=\"s32\">{type_value}</type>\n",
                f"      <value __type=\"s64\">{value}</value>\n",
                "    </event>\n",
            ]
        )
    lines.append("  </event_data>\n")
    return "".join(lines)


def add_basic_event_data(path: Path) -> dict[str, str | int]:
    text = path.read_text(encoding="utf-8-sig")
    if "<event_data>" in text:
        raise EventDataError("event_data already exists.")

    root_match = re.fullmatch(r"(?s)(<\?xml[^>]*>\n)?<music_score>\n(.*)</music_score>\n?", text)
    if root_match is None:
        raise EventDataError("XML shape is not the expected <music_score> document.")

    xml_decl = root_match.group(1) or "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
    root_body = root_match.group(2)
    bpm_match = FIRST_BPM_RE.search(root_body)
    if bpm_match is None:
        raise EventDataError("header.first_bpm is missing.")
    fixed_bpm = bpm_match.group(1)

    blocks: dict[str, str] = {}
    for tag in TOP_LEVEL_ORDER:
        block = find_block(root_body, tag)
        if block is not None:
            blocks[tag] = block
    for required in ["header", "note_data", "beat_data"]:
        if required not in blocks:
            raise EventDataError(f"{required} block is missing.")
    blocks["event_data"] = build_event_data(fixed_bpm)

    ordered_blocks = [blocks[tag] for tag in TOP_LEVEL_ORDER if tag in blocks]
    updated = xml_decl + "<music_score>\n" + "".join(ordered_blocks) + "</music_score>\n"
    path.write_text(updated, encoding="utf-8", newline="")
    return {"output": str(path), "fixed_bpm": fixed_bpm, "events": 9}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add tested type=0..8 event_data and order top-level blocks.")
    parser.add_argument("xml", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = add_basic_event_data(args.xml)
    except (OSError, UnicodeError, EventDataError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(f"OK: {result['output']} events={result['events']} fixed_bpm={result['fixed_bpm']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
