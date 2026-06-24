#!/usr/bin/env python3
"""Add Himawari-style velocity_zone_data scaled to the chart finish time."""

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
MUSIC_FINISH_RE = re.compile(r"<music_finish_time_msec\b[^>]*>\s*(\d+)\s*</music_finish_time_msec>")

HIMAWARI_FINISH_TIME_MSEC = 164756
HIMAWARI_ZONES = [
    (0, 0, 8000, 0),
    (1, 26000, 32000, 0),
    (2, 37000, 41000, 0),
    (3, 60000, 72000, 0),
    (4, 73000, 74000, 0),
    (5, 103000, 109000, 1),
    (6, 137000, 152000, 1),
]


class VelocityZoneError(ValueError):
    """Raised when velocity_zone_data cannot be added safely."""


def find_block(root_body: str, tag: str) -> str | None:
    pattern = re.compile(rf"  <{tag}\b.*?</{tag}>\n?", re.DOTALL)
    match = pattern.search(root_body)
    if match is None:
        return None
    return match.group(0)


def scale_time(value: int, target_finish: int) -> int:
    return round(value * target_finish / HIMAWARI_FINISH_TIME_MSEC)


def build_velocity_zone_data(target_finish: int) -> str:
    lines = ["  <velocity_zone_data>\n"]
    for index, start, end, velocity_type in HIMAWARI_ZONES:
        scaled_start = min(scale_time(start, target_finish), target_finish)
        scaled_end = min(scale_time(end, target_finish), target_finish)
        lines.extend(
            [
                "    <velocity_zone>\n",
                f"      <index __type=\"s32\">{index}</index>\n",
                f"      <start_timing_msec __type=\"s32\">{scaled_start}</start_timing_msec>\n",
                f"      <end_timing_msec __type=\"s32\">{scaled_end}</end_timing_msec>\n",
                f"      <velocity_type __type=\"s32\">{velocity_type}</velocity_type>\n",
                "    </velocity_zone>\n",
            ]
        )
    lines.append("  </velocity_zone_data>\n")
    return "".join(lines)


def add_velocity_zones(path: Path) -> dict[str, int | str]:
    text = path.read_text(encoding="utf-8-sig")
    if "<velocity_zone_data>" in text:
        raise VelocityZoneError("velocity_zone_data already exists.")

    root_match = re.fullmatch(r"(?s)(<\?xml[^>]*>\n)?<music_score>\n(.*)</music_score>\n?", text)
    if root_match is None:
        raise VelocityZoneError("XML shape is not the expected <music_score> document.")

    xml_decl = root_match.group(1) or "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
    root_body = root_match.group(2)
    finish_match = MUSIC_FINISH_RE.search(root_body)
    if finish_match is None:
        raise VelocityZoneError("header.music_finish_time_msec is missing.")
    finish_time = int(finish_match.group(1))

    blocks: dict[str, str] = {}
    for tag in TOP_LEVEL_ORDER:
        block = find_block(root_body, tag)
        if block is not None:
            blocks[tag] = block
    for required in ["header", "note_data", "event_data", "beat_data", "track_info"]:
        if required not in blocks:
            raise VelocityZoneError(f"{required} block is missing.")
    blocks["velocity_zone_data"] = build_velocity_zone_data(finish_time)

    ordered_blocks = [blocks[tag] for tag in TOP_LEVEL_ORDER if tag in blocks]
    updated = xml_decl + "<music_score>\n" + "".join(ordered_blocks) + "</music_score>\n"
    path.write_text(updated, encoding="utf-8", newline="")
    return {"output": str(path), "finish_time": finish_time, "zones": len(HIMAWARI_ZONES)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add Himawari-style scaled velocity zones.")
    parser.add_argument("xml", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = add_velocity_zones(args.xml)
    except (OSError, UnicodeError, VelocityZoneError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(f"OK: {result['output']} zones={result['zones']} finish_time={result['finish_time']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
