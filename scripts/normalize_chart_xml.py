#!/usr/bin/env python3
"""Normalize a chart XML into the observed NOSTALGIA music_score shape."""

from __future__ import annotations

import argparse
import copy
import xml.etree.ElementTree as ET
from pathlib import Path


NOTE_FIELDS = [
    ("index", "s32", "0"),
    ("start_timing_msec", "s32", "0"),
    ("end_timing_msec", "s32", "0"),
    ("gate_time_msec", "s32", "0"),
    ("scale_piano", "u8", "0"),
    ("min_key_index", "s32", "0"),
    ("max_key_index", "s32", "0"),
    ("note_type", "s32", "0"),
    ("hand", "s32", "0"),
    ("key_kind", "s32", "0"),
    ("param1", "s32", "0"),
    ("param2", "s32", "0"),
    ("param3", "s32", "0"),
]

TOP_LEVEL_ORDER = [
    "header",
    "note_data",
    "event_data",
    "beat_data",
    "track_info",
    "velocity_zone_data",
]

MAX_PIANO_SCALE = 88


class NormalizeError(ValueError):
    """Raised when a chart cannot be normalized."""


def child_text(parent: ET.Element, tag: str) -> str | None:
    child = parent.find(tag)
    if child is not None and child.text is not None:
        return child.text
    return parent.attrib.get(tag)


def set_typed_child(parent: ET.Element, tag: str, type_name: str, value: str) -> ET.Element:
    child = ET.SubElement(parent, tag)
    child.set("__type", type_name)
    child.text = value
    return child


def clamp_piano_scale(value: str) -> str:
    return str(max(0, min(MAX_PIANO_SCALE, int(value))))


def infer_fixed_bpm(root: ET.Element) -> str:
    header = root.find("header")
    if header is None:
        raise NormalizeError("header is missing")
    raw = child_text(header, "first_bpm")
    if raw is None:
        raise NormalizeError("header.first_bpm is missing")
    value = int(raw)
    if value < 10000:
        value *= 100000
    return str(value)


def normalize_header(root: ET.Element, fixed_bpm: str, clamp_scale: bool) -> ET.Element:
    source = root.find("header")
    if source is None:
        raise NormalizeError("header is missing")

    header = ET.Element("header")
    for child in source:
        if child.tag in {"time_signature_numerator", "time_signature_denominator", "time_signature"}:
            continue
        copied = copy.deepcopy(child)
        if copied.tag == "first_bpm":
            copied.text = fixed_bpm
        elif clamp_scale and copied.tag == "max_scale" and copied.text is not None:
            copied.text = clamp_piano_scale(copied.text)
        header.append(copied)
    return header


def normalize_note(source: ET.Element, clamp_scale: bool, shift_sub_note_track_index: int) -> ET.Element:
    note = ET.Element("note")
    values: dict[str, str] = {}
    for tag, type_name, default in NOTE_FIELDS:
        value = child_text(source, tag)
        if value is None:
            value = default
        if tag == "key_kind":
            value = "0"
        elif clamp_scale and tag == "scale_piano":
            value = clamp_piano_scale(value)
        values[tag] = value
        set_typed_child(note, tag, type_name, value)

    sub_note_data = source.find("sub_note_data")
    if sub_note_data is None:
        sub_note_data = ET.Element("sub_note_data")
    sub_note_copy = copy.deepcopy(sub_note_data)
    if clamp_scale:
        for sub_note in sub_note_copy.findall("sub_note"):
            scale = sub_note.find("scale_piano")
            if scale is not None and scale.text is not None:
                scale.text = clamp_piano_scale(scale.text)
    if shift_sub_note_track_index:
        for sub_note in sub_note_copy.findall("sub_note"):
            track_index = sub_note.find("track_index")
            if track_index is not None and track_index.text is not None:
                track_index.text = str(int(track_index.text) + shift_sub_note_track_index)
    if not sub_note_copy.findall("sub_note"):
        sub_note = ET.SubElement(sub_note_copy, "sub_note")
        set_typed_child(sub_note, "start_timing_msec", "s32", values["start_timing_msec"])
        set_typed_child(sub_note, "end_timing_msec", "s32", values["end_timing_msec"])
        set_typed_child(sub_note, "scale_piano", "u8", values["scale_piano"])
        set_typed_child(sub_note, "velocity", "u8", "100")
        track_index = "1" if values.get("hand") == "0" else "2"
        set_typed_child(sub_note, "track_index", "s32", track_index)
    note.append(sub_note_copy)
    return note


def normalize_note_data(root: ET.Element, clamp_scale: bool, shift_sub_note_track_index: int) -> ET.Element:
    source = root.find("note_data")
    if source is None:
        raise NormalizeError("note_data is missing")
    note_data = ET.Element("note_data")
    for note in source.findall("note"):
        note_data.append(normalize_note(note, clamp_scale, shift_sub_note_track_index))
    return note_data


def build_event_data(fixed_bpm: str) -> ET.Element:
    event_data = ET.Element("event_data")
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
    for index, start, type_value, value in events:
        event = ET.SubElement(event_data, "event")
        set_typed_child(event, "index", "s32", str(index))
        set_typed_child(event, "start_timing_msec", "s32", str(start))
        set_typed_child(event, "type", "s32", str(type_value))
        set_typed_child(event, "value", "s64", value)
    return event_data


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


def normalize_chart(
    input_path: Path,
    output_path: Path,
    clamp_scale: bool = False,
    shift_sub_note_track_index: int = 0,
) -> dict[str, str]:
    source_root = ET.parse(input_path).getroot()
    if source_root.tag != "music_score":
        raise NormalizeError(f"Unexpected root: {source_root.tag}")

    fixed_bpm = infer_fixed_bpm(source_root)
    output_root = ET.Element("music_score")
    elements: dict[str, ET.Element] = {
        "header": normalize_header(source_root, fixed_bpm, clamp_scale),
        "note_data": normalize_note_data(source_root, clamp_scale, shift_sub_note_track_index),
        "event_data": build_event_data(fixed_bpm),
    }
    for tag in ["beat_data", "track_info", "velocity_zone_data"]:
        source = source_root.find(tag)
        if source is None:
            raise NormalizeError(f"{tag} is missing")
        elements[tag] = copy.deepcopy(source)

    for tag in TOP_LEVEL_ORDER:
        output_root.append(elements[tag])

    indent(output_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = "<?xml version=\"1.0\"?>\n" + ET.tostring(
        output_root,
        encoding="unicode",
        short_empty_elements=True,
    )
    output_path.write_text(text, encoding="utf-8", newline="\n")
    return {
        "output": str(output_path),
        "fixed_bpm": fixed_bpm,
        "clamp_scale": str(clamp_scale),
        "shift_sub_note_track_index": str(shift_sub_note_track_index),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize a NOSTALGIA chart XML.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--clamp-scale-piano",
        action="store_true",
        help="Clamp note and sub_note scale_piano values to 0..88, and clamp header max_scale.",
    )
    parser.add_argument(
        "--shift-sub-note-track-index",
        type=int,
        default=0,
        help="Add this integer to every copied sub_note track_index value.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = normalize_chart(
            args.input,
            args.output,
            clamp_scale=args.clamp_scale_piano,
            shift_sub_note_track_index=args.shift_sub_note_track_index,
        )
    except (OSError, ET.ParseError, NormalizeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(f"OK: {args.input} -> {result['output']} fixed_bpm={result['fixed_bpm']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
