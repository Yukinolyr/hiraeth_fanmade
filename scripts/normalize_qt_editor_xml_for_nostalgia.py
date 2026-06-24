#!/usr/bin/env python3
"""Normalize a qt_editor-exported XML toward NOSTALGIA's official chart shape."""

from __future__ import annotations

import argparse
import copy
import xml.etree.ElementTree as ET
from pathlib import Path


TOP_LEVEL_ORDER = [
    "header",
    "note_data",
    "event_data",
    "beat_data",
    "track_info",
    "velocity_zone_data",
]

EXTRA_HEADER_FIELDS = {
    "time_signature_numerator",
    "time_signature_denominator",
    "time_signature",
}


class NormalizeError(ValueError):
    """Raised when the source XML cannot be normalized safely."""


def child(parent: ET.Element, tag: str) -> ET.Element:
    found = parent.find(tag)
    if found is None:
        raise NormalizeError(f"Missing required element: {tag}")
    return found


def elem_int(parent: ET.Element, tag: str) -> int:
    found = child(parent, tag)
    if found.text is None:
        raise NormalizeError(f"Missing text for element: {tag}")
    return int(found.text)


def set_typed_child(parent: ET.Element, tag: str, type_name: str, value: int | str) -> ET.Element:
    found = parent.find(tag)
    if found is None:
        found = ET.SubElement(parent, tag)
    found.set("__type", type_name)
    found.text = str(value)
    return found


def add_typed_child(parent: ET.Element, tag: str, type_name: str, value: int | str) -> ET.Element:
    found = ET.SubElement(parent, tag)
    found.set("__type", type_name)
    found.text = str(value)
    return found


def fixed_bpm_from_header(header: ET.Element) -> tuple[int, float]:
    raw_bpm = elem_int(header, "first_bpm")
    if raw_bpm <= 0:
        raise NormalizeError("header/first_bpm must be positive.")
    if raw_bpm < 10000:
        bpm = float(raw_bpm)
        fixed_bpm = int(round(bpm * 100000))
    else:
        fixed_bpm = raw_bpm
        bpm = fixed_bpm / 100000.0
    return fixed_bpm, bpm


def max_chart_end(root: ET.Element) -> int:
    max_end = 0
    for note in root.findall("./note_data/note"):
        note_end = note.findtext("end_timing_msec")
        if note_end is not None:
            max_end = max(max_end, int(note_end))
        for sub_note in note.findall("./sub_note_data/sub_note"):
            sub_end = sub_note.findtext("end_timing_msec")
            if sub_end is not None:
                max_end = max(max_end, int(sub_end))
    return max_end


def normalize_header(root: ET.Element) -> tuple[int, float, int, int, int]:
    header = child(root, "header")
    fixed_bpm, bpm = fixed_bpm_from_header(header)
    original_finish = elem_int(header, "music_finish_time_msec")
    note_finish = max_chart_end(root)
    new_finish = max(original_finish, note_finish)

    set_typed_child(header, "max_scale", "s32", 88)
    set_typed_child(header, "min_scale", "s32", 1)
    set_typed_child(header, "first_bpm", "s64", fixed_bpm)
    set_typed_child(header, "music_finish_time_msec", "s32", new_finish)

    removed = 0
    for item in list(header):
        if item.tag in EXTRA_HEADER_FIELDS:
            header.remove(item)
            removed += 1

    return fixed_bpm, bpm, new_finish, removed, 2


def build_event(index: int, timing: int, event_type: int, value: int) -> ET.Element:
    event = ET.Element("event")
    add_typed_child(event, "index", "s32", index)
    add_typed_child(event, "start_timing_msec", "s32", timing)
    add_typed_child(event, "type", "s32", event_type)
    add_typed_child(event, "value", "s64", value)
    return event


def init_event_timings(bpm: float) -> tuple[int, int]:
    if abs(bpm - 120.0) < 0.001:
        return 126, 254
    beat_msec = 60000.0 / bpm
    return int(round(beat_msec / 4.0)), int(round(beat_msec / 2.0))


def normalize_events(root: ET.Element, fixed_bpm: int, bpm: float) -> int:
    old_event_data = root.find("event_data")
    later_bpm_events: list[tuple[int, int]] = []
    if old_event_data is not None:
        for event in old_event_data.findall("event"):
            if event.findtext("type") != "0":
                continue
            timing = int(event.findtext("start_timing_msec") or "0")
            value = int(event.findtext("value") or "0")
            if timing > 0 and value > 0:
                later_bpm_events.append((timing, value))

    init_a, init_b = init_event_timings(bpm)
    event_data = ET.Element("event_data")
    events = [
        (0, 0, fixed_bpm),
        (0, 1, 120),
        (0, 2, 9),
        (init_a, 3, 16),
        (init_a, 4, 14),
        (init_a, 5, 24),
        (init_b, 6, 120),
        (init_b, 7, 0),
        (init_b, 8, 80),
    ]
    for index, (timing, event_type, value) in enumerate(events):
        event_data.append(build_event(index, timing, event_type, value))

    next_index = len(events)
    for timing, value in sorted(set(later_bpm_events)):
        event_data.append(build_event(next_index, timing, 0, value))
        next_index += 1

    if old_event_data is None:
        root.append(event_data)
    else:
        old_index = list(root).index(old_event_data)
        root.remove(old_event_data)
        root.insert(old_index, event_data)
    return len(event_data.findall("event"))


def normalize_notes(root: ET.Element) -> dict[str, int]:
    key_kind_changed = 0
    measure_index_removed = 0
    velocity_changed = 0
    for note in root.findall("./note_data/note"):
        key_kind = note.find("key_kind")
        if key_kind is not None:
            if key_kind.text != "0":
                key_kind_changed += 1
            key_kind.set("__type", "s32")
            key_kind.text = "0"

        for item in list(note):
            if item.tag == "measure_index":
                note.remove(item)
                measure_index_removed += 1

        for velocity in note.findall("./sub_note_data/sub_note/velocity"):
            if velocity.text != "0":
                velocity_changed += 1
            velocity.set("__type", "u8")
            velocity.text = "0"

    return {
        "key_kind_changed": key_kind_changed,
        "measure_index_removed": measure_index_removed,
        "velocity_changed": velocity_changed,
    }


def strip_non_type_attributes(root: ET.Element) -> int:
    removed = 0
    for elem in root.iter():
        for name in list(elem.attrib):
            if name == "__type":
                continue
            del elem.attrib[name]
            removed += 1
    return removed


def build_beat_data(bpm: float, finish_time: int) -> ET.Element:
    if bpm <= 0:
        raise NormalizeError("BPM must be positive.")
    interval = 60000.0 / bpm
    if interval <= 0:
        raise NormalizeError("Computed beat interval is invalid.")

    beat_data = ET.Element("beat_data")
    index = 0
    while True:
        timing = int(round(index * interval))
        beat = ET.SubElement(beat_data, "beat")
        add_typed_child(beat, "index", "s32", index)
        add_typed_child(beat, "start_timing_msec", "s32", timing)
        if timing >= finish_time:
            break
        index += 1
        if index > 1_000_000:
            raise NormalizeError("Too many beats generated; BPM/finish time looks invalid.")
    return beat_data


def collect_track_indexes(root: ET.Element) -> set[int]:
    indexes: set[int] = set()
    for sub_note in root.findall("./note_data/note/sub_note_data/sub_note"):
        text = sub_note.findtext("track_index")
        if text is not None:
            indexes.add(int(text))
    return indexes


def build_track_info(root: ET.Element) -> ET.Element:
    track_indexes = collect_track_indexes(root)
    if not track_indexes:
        track_indexes = {1}
    max_index = max(3, max(track_indexes))

    track_info = ET.Element("track_info")
    for index in range(1, max_index + 1):
        track = ET.SubElement(track_info, "track")
        add_typed_child(track, "index", "s32", index)
        add_typed_child(track, "name", "str", "key_apiano1")
    return track_info


def normalize_top_level(root: ET.Element, beat_data: ET.Element, track_info: ET.Element) -> ET.Element:
    blocks: dict[str, ET.Element] = {}
    for item in list(root):
        if item.tag in blocks:
            raise NormalizeError(f"Duplicate top-level element: {item.tag}")
        if item.tag in TOP_LEVEL_ORDER:
            blocks[item.tag] = item

    blocks["beat_data"] = beat_data
    blocks["track_info"] = track_info
    blocks["velocity_zone_data"] = ET.Element("velocity_zone_data")

    missing = [tag for tag in TOP_LEVEL_ORDER if tag not in blocks]
    if missing:
        raise NormalizeError("Missing required top-level elements: " + ", ".join(missing))

    output = ET.Element(root.tag, root.attrib)
    for tag in TOP_LEVEL_ORDER:
        output.append(blocks[tag])
    return output


def indent(elem: ET.Element, level: int = 0) -> None:
    prefix = "\n" + "  " * level
    child_prefix = "\n" + "  " * (level + 1)
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = child_prefix
        for item in elem:
            indent(item, level + 1)
        if not elem[-1].tail or not elem[-1].tail.strip():
            elem[-1].tail = prefix
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = prefix


def write_xml(root: ET.Element, output: Path) -> None:
    output_root = copy.deepcopy(root)
    indent(output_root)
    text = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" + ET.tostring(
        output_root,
        encoding="unicode",
        short_empty_elements=False,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")


def normalize(source: Path, output: Path) -> dict[str, int | str | float]:
    root = ET.parse(source).getroot()
    if root.tag != "music_score":
        raise NormalizeError(f"Unexpected root element: {root.tag}")

    fixed_bpm, bpm, finish_time, header_removed, header_scale_fields = normalize_header(root)
    events = normalize_events(root, fixed_bpm, bpm)
    note_stats = normalize_notes(root)
    attrs_removed = strip_non_type_attributes(root)
    beat_data = build_beat_data(bpm, finish_time)
    track_info = build_track_info(root)
    output_root = normalize_top_level(root, beat_data, track_info)
    write_xml(output_root, output)

    return {
        "output": str(output),
        "fixed_bpm": fixed_bpm,
        "bpm": bpm,
        "finish_time": finish_time,
        "beats": len(beat_data.findall("beat")),
        "tracks": len(track_info.findall("track")),
        "header_fields_removed": header_removed,
        "header_scale_fields": header_scale_fields,
        "events": events,
        "attrs_removed": attrs_removed,
        "key_kind_changed": note_stats["key_kind_changed"],
        "measure_index_removed": note_stats["measure_index_removed"],
        "velocity_changed": note_stats["velocity_changed"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize one qt_editor XML for NOSTALGIA import testing."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = normalize(args.source, args.output)
    except (OSError, ET.ParseError, NormalizeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"{result['output']} bpm={result['fixed_bpm']} "
        f"finish={result['finish_time']} beats={result['beats']} tracks={result['tracks']} "
        f"removed_header={result['header_fields_removed']} "
        f"scale_fields={result['header_scale_fields']} "
        f"events={result['events']} "
        f"attrs_removed={result['attrs_removed']} "
        f"key_kind_changed={result['key_kind_changed']} "
        f"measure_index_removed={result['measure_index_removed']} "
        f"velocity_changed={result['velocity_changed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
