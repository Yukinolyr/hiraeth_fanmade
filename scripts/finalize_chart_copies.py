#!/usr/bin/env python3
"""Finalize one chart XML and write identical copies for all four difficulties."""

from __future__ import annotations

import argparse
import copy
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIFFICULTIES = ["00normal", "01hard", "02extreme", "03real"]
TOP_LEVEL_ORDER = [
    "header",
    "note_data",
    "event_data",
    "beat_data",
    "track_info",
    "velocity_zone_data",
]


class FinalizeChartError(ValueError):
    """Raised when a chart cannot be finalized safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise FinalizeChartError(f"Path must stay inside project root: {path}") from exc
    return resolved


def elem_int(parent: ET.Element, tag: str) -> int:
    child = parent.find(tag)
    if child is None or child.text is None:
        raise FinalizeChartError(f"Missing required field: {tag}")
    return int(child.text)


def set_typed_child(parent: ET.Element, tag: str, type_name: str, value: int) -> None:
    child = ET.SubElement(parent, tag)
    child.set("__type", type_name)
    child.text = str(value)


def build_beat_data(root: ET.Element) -> ET.Element:
    header = root.find("header")
    if header is None:
        raise FinalizeChartError("header is missing.")

    fixed_bpm = elem_int(header, "first_bpm")
    finish_time = elem_int(header, "music_finish_time_msec")
    if fixed_bpm <= 0:
        raise FinalizeChartError("first_bpm must be positive.")
    if finish_time <= 0:
        raise FinalizeChartError("music_finish_time_msec must be positive.")

    bpm = fixed_bpm / 100000
    beat_interval = round(60000 / bpm)
    if beat_interval <= 0:
        raise FinalizeChartError("computed beat interval is invalid.")

    beat_data = ET.Element("beat_data")
    index = 0
    timing = 0
    while timing <= finish_time:
        beat = ET.SubElement(beat_data, "beat")
        set_typed_child(beat, "index", "s32", index)
        set_typed_child(beat, "start_timing_msec", "s32", timing)
        index += 1
        timing = round(index * beat_interval)

    if beat_data[-1].findtext("start_timing_msec") != str(finish_time):
        beat = ET.SubElement(beat_data, "beat")
        set_typed_child(beat, "index", "s32", index)
        set_typed_child(beat, "start_timing_msec", "s32", finish_time)

    return beat_data


def normalize_notes(root: ET.Element) -> dict[str, int]:
    key_kind_changed = 0
    measure_index_removed = 0
    for note in root.findall("./note_data/note"):
        key_kind = note.find("key_kind")
        if key_kind is not None:
            if key_kind.text != "0":
                key_kind_changed += 1
            key_kind.text = "0"

        for child in list(note):
            if child.tag == "measure_index":
                note.remove(child)
                measure_index_removed += 1

    return {
        "key_kind_changed": key_kind_changed,
        "measure_index_removed": measure_index_removed,
    }


def reorder_top_level(root: ET.Element, new_beat_data: ET.Element) -> ET.Element:
    blocks: dict[str, ET.Element] = {}
    for child in list(root):
        if child.tag in blocks:
            raise FinalizeChartError(f"Duplicate top-level block: {child.tag}")
        blocks[child.tag] = child
    blocks["beat_data"] = new_beat_data

    missing = [tag for tag in TOP_LEVEL_ORDER if tag not in blocks]
    if missing:
        raise FinalizeChartError("Missing top-level blocks: " + ", ".join(missing))

    output_root = ET.Element(root.tag, root.attrib)
    for tag in TOP_LEVEL_ORDER:
        output_root.append(blocks[tag])
    return output_root


def indent(elem: ET.Element, level: int = 0) -> None:
    prefix = "\n" + "  " * level
    child_prefix = "\n" + "  " * (level + 1)
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = child_prefix
        for child in elem:
            indent(child, level + 1)
        if not elem[-1].tail or not elem[-1].tail.strip():
            elem[-1].tail = prefix
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = prefix


def write_xml(root: ET.Element, path: Path) -> None:
    output_root = copy.deepcopy(root)
    indent(output_root)
    text = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" + ET.tostring(
        output_root,
        encoding="unicode",
        short_empty_elements=True,
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def finalize_chart_copies(source: Path, destination: Path, basename: str) -> dict[str, int | str]:
    source = resolve_inside_project(source)
    destination = resolve_inside_project(destination)
    if not source.is_file():
        raise FinalizeChartError(f"Source XML not found: {source}")
    try:
        destination.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise FinalizeChartError(f"Destination must be inside work/: {destination}") from exc
    if destination.exists():
        raise FinalizeChartError(f"Destination already exists: {destination}")

    root = ET.parse(source).getroot()
    if root.tag != "music_score":
        raise FinalizeChartError(f"Unexpected root: {root.tag}")

    note_stats = normalize_notes(root)
    beat_data = build_beat_data(root)
    finalized = reorder_top_level(root, beat_data)

    destination.mkdir(parents=True)
    for difficulty in DIFFICULTIES:
        write_xml(finalized, destination / f"{basename}_{difficulty}.xml")

    return {
        "destination": str(destination),
        "files": len(DIFFICULTIES),
        "beats": len(beat_data.findall("beat")),
        "key_kind_changed": note_stats["key_kind_changed"],
        "measure_index_removed": note_stats["measure_index_removed"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild beat_data, set key_kind=0, remove measure_index, and write four difficulty XML copies."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--basename", default="closeup")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = finalize_chart_copies(args.source, args.destination, args.basename)
    except (OSError, ET.ParseError, FinalizeChartError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"{result['destination']} files={result['files']} beats={result['beats']} "
        f"key_kind_changed={result['key_kind_changed']} "
        f"measure_index_removed={result['measure_index_removed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
