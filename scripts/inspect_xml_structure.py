#!/usr/bin/env python3
"""Inspect NOSTALGIA chart XML files without modifying them."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any


NOTE_FIELDS = [
    "index",
    "start_timing_msec",
    "end_timing_msec",
    "gate_time_msec",
    "scale_piano",
    "min_key_index",
    "max_key_index",
    "note_type",
    "hand",
    "key_kind",
    "param1",
    "param2",
    "param3",
    "sub_note_data",
]


def elem_int(elem: ET.Element, tag: str, default: int | None = None) -> int | None:
    child = elem.find(tag)
    if child is None or child.text is None:
        return default
    try:
        return int(child.text)
    except ValueError:
        return default


def elem_text(elem: ET.Element, tag: str, default: str | None = None) -> str | None:
    child = elem.find(tag)
    if child is None or child.text is None:
        return default
    return child.text


def counter_to_dict(counter: Counter[Any]) -> dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter, key=lambda item: (str(type(item)), item))}


def int_range(values: list[int]) -> list[int] | None:
    if not values:
        return None
    return [min(values), max(values)]


def inspect_xml(path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    header_elem = root.find("header")
    note_data = root.find("note_data")
    event_data = root.find("event_data")
    beat_data = root.find("beat_data")
    track_info = root.find("track_info")
    velocity_zone_data = root.find("velocity_zone_data")

    header: dict[str, str] = {}
    if header_elem is not None:
        header = {child.tag: child.text or "" for child in header_elem}

    notes = note_data.findall("note") if note_data is not None else []
    events = event_data.findall("event") if event_data is not None else []
    beats = beat_data.findall("beat") if beat_data is not None else []
    tracks = track_info.findall("track") if track_info is not None else []
    velocity_zones = (
        velocity_zone_data.findall("velocity_zone") if velocity_zone_data is not None else []
    )

    note_types: Counter[int | None] = Counter()
    hands: Counter[int | None] = Counter()
    key_kinds: Counter[int | None] = Counter()
    param3_values: Counter[int | None] = Counter()
    note_field_shapes: Counter[tuple[str, ...]] = Counter()
    sub_note_counts: Counter[int] = Counter()
    sub_tracks: Counter[int | None] = Counter()
    sub_velocities: Counter[int | None] = Counter()

    starts: list[int] = []
    ends: list[int] = []
    gates: list[int] = []
    key_indexes: list[int] = []
    scales: list[int] = []
    sub_scales: list[int] = []
    indexes: list[int] = []
    bad_gate_indexes: list[int] = []
    no_sub_note_indexes: list[int] = []

    for note in notes:
        index = elem_int(note, "index")
        if index is not None:
            indexes.append(index)

        start = elem_int(note, "start_timing_msec")
        end = elem_int(note, "end_timing_msec")
        gate = elem_int(note, "gate_time_msec")
        if start is not None:
            starts.append(start)
        if end is not None:
            ends.append(end)
        if gate is not None:
            gates.append(gate)
        if start is not None and end is not None and gate is not None and gate != end - start:
            if index is not None:
                bad_gate_indexes.append(index)

        min_key = elem_int(note, "min_key_index")
        max_key = elem_int(note, "max_key_index")
        scale = elem_int(note, "scale_piano")
        if min_key is not None:
            key_indexes.append(min_key)
        if max_key is not None:
            key_indexes.append(max_key)
        if scale is not None:
            scales.append(scale)

        note_types[elem_int(note, "note_type")] += 1
        hands[elem_int(note, "hand")] += 1
        key_kinds[elem_int(note, "key_kind")] += 1
        param3_values[elem_int(note, "param3")] += 1
        note_field_shapes[tuple(child.tag for child in note)] += 1

        sub_note_data = note.find("sub_note_data")
        sub_notes = sub_note_data.findall("sub_note") if sub_note_data is not None else []
        sub_note_counts[len(sub_notes)] += 1
        if not sub_notes and index is not None:
            no_sub_note_indexes.append(index)
        for sub_note in sub_notes:
            sub_tracks[elem_int(sub_note, "track_index")] += 1
            sub_velocities[elem_int(sub_note, "velocity")] += 1
            sub_scale = elem_int(sub_note, "scale_piano")
            if sub_scale is not None:
                sub_scales.append(sub_scale)

    event_rows = [
        {
            "index": elem_int(event, "index"),
            "start_timing_msec": elem_int(event, "start_timing_msec"),
            "type": elem_int(event, "type"),
            "value": elem_int(event, "value"),
        }
        for event in events
    ]
    event_types = Counter(row["type"] for row in event_rows)

    beat_times = [elem_int(beat, "start_timing_msec") for beat in beats]
    beat_times = [time for time in beat_times if time is not None]
    beat_deltas = Counter(
        beat_times[index + 1] - beat_times[index] for index in range(len(beat_times) - 1)
    )

    index_counts = Counter(indexes)
    duplicate_indexes = sorted(index for index, count in index_counts.items() if count > 1)

    return {
        "file": str(path),
        "root": root.tag,
        "top_level_nodes": [child.tag for child in root],
        "header": header,
        "first_bpm": int(header["first_bpm"]) / 100000.0 if header.get("first_bpm") else None,
        "counts": {
            "notes": len(notes),
            "events": len(events),
            "beats": len(beats),
            "tracks": len(tracks),
            "velocity_zones": len(velocity_zones),
            "playable_notes_hand_not_2": sum(1 for note in notes if elem_int(note, "hand") != 2),
        },
        "note": {
            "field_shapes": [
                {"fields": list(fields), "count": count}
                for fields, count in note_field_shapes.most_common()
            ],
            "expected_fields_match": set(note_field_shapes) == {tuple(NOTE_FIELDS)},
            "types": counter_to_dict(note_types),
            "hands": counter_to_dict(hands),
            "key_kinds": counter_to_dict(key_kinds),
            "param3_values": counter_to_dict(param3_values),
            "sub_note_counts": counter_to_dict(sub_note_counts),
            "index_range": int_range(indexes),
            "duplicate_indexes": duplicate_indexes,
            "bad_gate_indexes": bad_gate_indexes,
            "no_sub_note_indexes": no_sub_note_indexes,
            "start_range": int_range(starts),
            "end_range": int_range(ends),
            "gate_range": int_range(gates),
            "key_index_range": int_range(key_indexes),
            "scale_range": int_range(scales),
            "glissando_nodes": sum(1 for note in notes if elem_int(note, "note_type") in (4, 12)),
            "glissando_heads": sum(
                1
                for note in notes
                if elem_int(note, "note_type") in (4, 12) and elem_int(note, "param1") == -1
            ),
            "glissando_tails": sum(
                1
                for note in notes
                if elem_int(note, "note_type") in (4, 12) and elem_int(note, "param2") == -1
            ),
        },
        "sub_note": {
            "track_indexes": counter_to_dict(sub_tracks),
            "velocities": counter_to_dict(sub_velocities),
            "scale_range": int_range(sub_scales),
        },
        "event": {
            "types": counter_to_dict(event_types),
            "rows": event_rows,
        },
        "beat": {
            "time_range": int_range(beat_times),
            "last_index": elem_int(beats[-1], "index") if beats else None,
            "delta_counts": counter_to_dict(beat_deltas),
        },
        "tracks": [
            {"index": elem_int(track, "index"), "name": elem_text(track, "name")}
            for track in tracks
        ],
        "velocity_zones": [
            {
                "index": elem_int(zone, "index"),
                "start_timing_msec": elem_int(zone, "start_timing_msec"),
                "end_timing_msec": elem_int(zone, "end_timing_msec"),
                "velocity_type": elem_int(zone, "velocity_type"),
            }
            for zone in velocity_zones
        ],
    }


def print_markdown(results: list[dict[str, Any]]) -> None:
    print("# XML Structure Summary")
    print()
    for result in results:
        path = Path(result["file"])
        counts = result["counts"]
        note = result["note"]
        beat = result["beat"]
        print(f"## {path.name}")
        print()
        print(f"- root: `{result['root']}`")
        print(f"- top_level_nodes: `{', '.join(result['top_level_nodes'])}`")
        print(f"- first_bpm: `{result['first_bpm']}`")
        print(f"- finish_time_ms: `{result['header'].get('music_finish_time_msec', '')}`")
        print(
            "- counts: "
            f"notes={counts['notes']}, playable(hand!=2)={counts['playable_notes_hand_not_2']}, "
            f"events={counts['events']}, beats={counts['beats']}, tracks={counts['tracks']}, "
            f"velocity_zones={counts['velocity_zones']}"
        )
        print(f"- note_types: `{note['types']}`")
        print(f"- hands: `{note['hands']}`")
        print(f"- sub_note_counts: `{note['sub_note_counts']}`")
        print(f"- key_kind_values: `{note['key_kinds']}`")
        print(f"- param3_values: `{note['param3_values']}`")
        print(
            "- ranges: "
            f"start={note['start_range']}, end={note['end_range']}, gate={note['gate_range']}, "
            f"key_index={note['key_index_range']}, scale={note['scale_range']}"
        )
        print(
            "- glissando: "
            f"nodes={note['glissando_nodes']}, heads={note['glissando_heads']}, "
            f"tails={note['glissando_tails']}"
        )
        print(
            "- validation: "
            f"expected_fields_match={note['expected_fields_match']}, "
            f"duplicate_indexes={len(note['duplicate_indexes'])}, "
            f"bad_gate={len(note['bad_gate_indexes'])}, "
            f"missing_sub_note={len(note['no_sub_note_indexes'])}"
        )
        print(f"- event_types: `{result['event']['types']}`")
        print(f"- beat_range: `{beat['time_range']}`, last_index=`{beat['last_index']}`")
        print(f"- beat_delta_counts: `{beat['delta_counts']}`")
        print(f"- sub_note_tracks: `{result['sub_note']['track_indexes']}`")
        print(f"- sub_note_scale_range: `{result['sub_note']['scale_range']}`")
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect NOSTALGIA chart XML structure.")
    parser.add_argument("path", type=Path, help="XML file or folder containing XML files.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of Markdown.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = args.path
    if target.is_dir():
        xml_files = sorted(target.glob("*.xml"))
    else:
        xml_files = [target]

    missing = [path for path in xml_files if not path.exists()]
    if not xml_files or missing:
        print(f"No XML files found: {target}")
        return 1

    results = [inspect_xml(path) for path in xml_files]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_markdown(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
