#!/usr/bin/env python3
"""Validate a NOSTALGIA custom song folder without modifying it."""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DIFFICULTIES = {
    "00normal": "Normal",
    "01hard": "Hard",
    "02extreme": "Extreme",
    "03real": "Real",
}
DIFF_PATTERN = re.compile(r"^(?P<base>.+)_(?P<diff>00normal|01hard|02extreme|03real)$")
TOP_LEVEL_NODES = [
    "header",
    "note_data",
    "event_data",
    "beat_data",
    "track_info",
    "velocity_zone_data",
]
HEADER_FIELDS = [
    "max_scale",
    "min_scale",
    "file_version",
    "first_bpm",
    "music_finish_time_msec",
]
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
SUB_NOTE_FIELDS = [
    "start_timing_msec",
    "end_timing_msec",
    "scale_piano",
    "velocity",
    "track_index",
]
KNOWN_NOTE_TYPES = {0, 2, 4, 8, 10, 12, 64}


@dataclass
class Finding:
    level: str
    path: str
    message: str


@dataclass
class ValidationResult:
    folder: str
    inferred_basename: str | None = None
    errors: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)
    summaries: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, path: Path | str, message: str) -> None:
        self.errors.append(Finding("error", str(path), message))

    def add_warning(self, path: Path | str, message: str) -> None:
        self.warnings.append(Finding("warning", str(path), message))


def elem_int(elem: ET.Element, tag: str) -> int | None:
    child = elem.find(tag)
    if child is None or child.text is None:
        return None
    try:
        return int(child.text)
    except ValueError:
        return None


def read_magic(path: Path, length: int = 4) -> bytes:
    with path.open("rb") as file_obj:
        return file_obj.read(length)


def find_ascii_strings(data: bytes, min_len: int = 4) -> list[str]:
    pattern = rb"[A-Za-z0-9_]{%d,}" % min_len
    return [match.group().decode("ascii", errors="replace") for match in re.finditer(pattern, data)]


def infer_basename(folder: Path, files: list[Path]) -> str | None:
    candidates: list[str] = []
    for file_path in files:
        stem = file_path.stem
        match = DIFF_PATTERN.match(stem)
        if match:
            candidates.append(match.group("base"))
        elif stem.endswith("_pre"):
            candidates.append(stem[:-4])
        elif file_path.suffix.lower() in {".xwb", ".xsb"}:
            candidates.append(stem)

    if candidates:
        return Counter(candidates).most_common(1)[0][0]
    return folder.name if folder.name else None


def validate_bank_files(folder: Path, basename: str | None, result: ValidationResult, strict: bool) -> None:
    if not basename:
        result.add_error(folder, "Could not infer song basename.")
        return

    required = [folder / f"{basename}.xwb", folder / f"{basename}.xsb"]
    optional = [folder / f"{basename}_pre.xwb", folder / f"{basename}_pre.xsb"]

    for path in required:
        if not path.exists():
            result.add_error(path, "Required bank file is missing.")
            continue
        validate_magic(path, result)
        validate_internal_bank_name(path, basename, result)

    for path in optional:
        if not path.exists():
            message = "Preview bank file is missing."
            if strict:
                result.add_error(path, message)
            else:
                result.add_warning(path, message)
            continue
        validate_magic(path, result)
        validate_internal_bank_name(path, f"{basename}_pre", result)


def validate_magic(path: Path, result: ValidationResult) -> None:
    suffix = path.suffix.lower()
    try:
        magic = read_magic(path)
    except OSError as exc:
        result.add_error(path, f"Could not read file magic: {exc}")
        return

    expected = {".xwb": b"WBND", ".xsb": b"SDBK"}.get(suffix)
    if expected is not None and magic != expected:
        result.add_error(path, f"Unexpected magic bytes: expected {expected!r}, got {magic!r}.")


def validate_internal_bank_name(path: Path, expected_basename: str, result: ValidationResult) -> None:
    try:
        data = path.read_bytes()
    except OSError as exc:
        result.add_error(path, f"Could not read file for internal name check: {exc}")
        return

    strings = find_ascii_strings(data)
    normalized_expected = expected_basename.lower()
    if not any(text.lower() == normalized_expected for text in strings):
        result.add_warning(path, f"No internal bank string matches expected basename `{expected_basename}`.")


def validate_xml_files(folder: Path, basename: str | None, result: ValidationResult, strict: bool) -> None:
    xml_files = sorted(folder.glob("*.xml"))
    chart_xml_files = [path for path in xml_files if DIFF_PATTERN.match(path.stem)]
    non_chart_xml_files = [path for path in xml_files if not DIFF_PATTERN.match(path.stem)]
    if not chart_xml_files:
        result.add_error(folder, "No chart XML files found.")
        return

    for xml_path in non_chart_xml_files:
        result.add_warning(xml_path, "Non-chart XML file ignored by song validator.")

    seen_difficulties: set[str] = set()
    for xml_path in chart_xml_files:
        match = DIFF_PATTERN.match(xml_path.stem)
        if match:
            seen_difficulties.add(match.group("diff"))
            if basename and match.group("base") != basename:
                result.add_error(xml_path, f"XML basename does not match inferred basename `{basename}`.")
        else:
            result.add_warning(xml_path, "XML filename does not match `{basename}_{difficulty}.xml`.")

        validate_xml_file(xml_path, result)

    missing_difficulties = [diff for diff in DIFFICULTIES if diff not in seen_difficulties]
    if missing_difficulties:
        message = "Missing difficulty XML files: " + ", ".join(missing_difficulties)
        if strict:
            result.add_error(folder, message)
        else:
            result.add_warning(folder, message)


def validate_xml_file(path: Path, result: ValidationResult) -> None:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        result.add_error(path, f"XML parse error: {exc}")
        return
    except ValueError as exc:
        result.add_error(path, f"XML parse error: {exc}")
        return
    except OSError as exc:
        result.add_error(path, f"Could not read XML: {exc}")
        return

    if root.tag != "music_score":
        result.add_error(path, f"Unexpected root tag `{root.tag}`, expected `music_score`.")

    child_tags = [child.tag for child in root]
    missing_top = [tag for tag in TOP_LEVEL_NODES if root.find(tag) is None]
    if missing_top:
        result.add_error(path, "Missing top-level nodes: " + ", ".join(missing_top))

    if child_tags != TOP_LEVEL_NODES:
        result.add_warning(path, "Top-level node order differs from reference structure.")

    header = root.find("header")
    if header is not None:
        missing_header = [tag for tag in HEADER_FIELDS if header.find(tag) is None]
        if missing_header:
            result.add_error(path, "Missing header fields: " + ", ".join(missing_header))

    notes = root.find("note_data").findall("note") if root.find("note_data") is not None else []
    events = root.find("event_data").findall("event") if root.find("event_data") is not None else []
    beats = root.find("beat_data").findall("beat") if root.find("beat_data") is not None else []
    tracks = root.find("track_info").findall("track") if root.find("track_info") is not None else []
    velocity_zones = (
        root.find("velocity_zone_data").findall("velocity_zone")
        if root.find("velocity_zone_data") is not None
        else []
    )

    if not notes:
        result.add_error(path, "No note entries found.")
    if not any(elem_int(event, "type") == 0 for event in events):
        result.add_error(path, "No BPM event found in event_data.")

    validate_notes(path, notes, result)
    validate_beats(path, beats, result)

    result.summaries.append(
        {
            "file": path.name,
            "notes": len(notes),
            "events": len(events),
            "beats": len(beats),
            "tracks": len(tracks),
            "velocity_zones": len(velocity_zones),
        }
    )


def validate_notes(path: Path, notes: list[ET.Element], result: ValidationResult) -> None:
    indexes: list[int] = []
    index_to_note: dict[int, ET.Element] = {}
    track_indexes: set[int] = set()

    for note in notes:
        note_index = elem_int(note, "index")
        if note_index is not None:
            indexes.append(note_index)
            index_to_note[note_index] = note

        missing_fields = [tag for tag in NOTE_FIELDS if note.find(tag) is None]
        if missing_fields:
            result.add_error(path, f"Note {note_index} missing fields: {', '.join(missing_fields)}")
            continue

        start = elem_int(note, "start_timing_msec")
        end = elem_int(note, "end_timing_msec")
        gate = elem_int(note, "gate_time_msec")
        if start is None or end is None or gate is None:
            result.add_error(path, f"Note {note_index} has invalid timing values.")
        elif gate != end - start:
            result.add_error(path, f"Note {note_index} gate_time_msec does not equal end - start.")

        min_key = elem_int(note, "min_key_index")
        max_key = elem_int(note, "max_key_index")
        if min_key is not None and max_key is not None and min_key > max_key:
            result.add_error(path, f"Note {note_index} has min_key_index > max_key_index.")

        scale = elem_int(note, "scale_piano")
        if scale is not None and not 0 <= scale <= 88:
            result.add_warning(path, f"Note {note_index} scale_piano is outside 0..88.")

        note_type = elem_int(note, "note_type")
        if note_type is not None and note_type not in KNOWN_NOTE_TYPES:
            result.add_warning(path, f"Note {note_index} has unknown note_type {note_type}.")

        key_kind = elem_int(note, "key_kind")
        param3 = elem_int(note, "param3")
        if key_kind not in (0, None):
            result.add_warning(path, f"Note {note_index} key_kind is non-zero: {key_kind}.")
        if param3 not in (0, None):
            result.add_warning(path, f"Note {note_index} param3 is non-zero: {param3}.")

        sub_note_data = note.find("sub_note_data")
        sub_notes = sub_note_data.findall("sub_note") if sub_note_data is not None else []
        if not sub_notes:
            result.add_error(path, f"Note {note_index} has no sub_note entries.")
        for sub_note in sub_notes:
            missing_sub_fields = [tag for tag in SUB_NOTE_FIELDS if sub_note.find(tag) is None]
            if missing_sub_fields:
                result.add_error(
                    path,
                    f"Note {note_index} sub_note missing fields: {', '.join(missing_sub_fields)}",
                )
            track_index = elem_int(sub_note, "track_index")
            if track_index is not None:
                track_indexes.add(track_index)

    duplicate_indexes = sorted(index for index, count in Counter(indexes).items() if count > 1)
    if duplicate_indexes:
        result.add_error(path, "Duplicate note indexes: " + ", ".join(map(str, duplicate_indexes[:20])))

    validate_glissando_links(path, notes, index_to_note, result)


def validate_glissando_links(
    path: Path,
    notes: list[ET.Element],
    index_to_note: dict[int, ET.Element],
    result: ValidationResult,
) -> None:
    glissando_types = {4, 12}
    for note in notes:
        note_type = elem_int(note, "note_type")
        if note_type not in glissando_types:
            continue

        note_index = elem_int(note, "index")
        param1 = elem_int(note, "param1")
        param2 = elem_int(note, "param2")
        for tag, ref in [("param1", param1), ("param2", param2)]:
            if ref in (None, -1):
                continue
            ref_note = index_to_note.get(ref)
            if ref_note is None:
                result.add_error(path, f"Glissando note {note_index} {tag} references missing index {ref}.")
                continue
            if elem_int(ref_note, "note_type") not in glissando_types:
                result.add_error(path, f"Glissando note {note_index} {tag} references non-glissando note {ref}.")


def validate_beats(path: Path, beats: list[ET.Element], result: ValidationResult) -> None:
    previous_time: int | None = None
    previous_index: int | None = None
    for beat in beats:
        beat_index = elem_int(beat, "index")
        beat_time = elem_int(beat, "start_timing_msec")
        if beat_index is None or beat_time is None:
            result.add_error(path, "Beat entry has invalid index or start_timing_msec.")
            continue
        if previous_index is not None and beat_index <= previous_index:
            result.add_error(path, "Beat indexes are not strictly increasing.")
            break
        if previous_time is not None and beat_time < previous_time:
            result.add_error(path, "Beat start_timing_msec values are decreasing.")
            break
        previous_index = beat_index
        previous_time = beat_time


def findings_to_json(findings: list[Finding]) -> list[dict[str, str]]:
    return [finding.__dict__ for finding in findings]


def print_text(result: ValidationResult) -> None:
    status = "PASS" if result.ok else "FAIL"
    print(f"{status}: {result.folder}")
    if result.inferred_basename:
        print(f"inferred_basename: {result.inferred_basename}")
    print(f"errors: {len(result.errors)}")
    print(f"warnings: {len(result.warnings)}")

    if result.summaries:
        print()
        print("XML summaries:")
        for summary in result.summaries:
            print(
                "- "
                f"{summary['file']}: notes={summary['notes']}, events={summary['events']}, "
                f"beats={summary['beats']}, tracks={summary['tracks']}, "
                f"velocity_zones={summary['velocity_zones']}"
            )

    for title, findings in [("Errors", result.errors), ("Warnings", result.warnings)]:
        if not findings:
            continue
        print()
        print(f"{title}:")
        for finding in findings:
            print(f"- {finding.path}: {finding.message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a NOSTALGIA song folder.")
    parser.add_argument("path", type=Path, help="Song folder to validate.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat optional preview banks and missing difficulty XMLs as errors.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    folder = args.path
    result = ValidationResult(folder=str(folder))

    if not folder.exists() or not folder.is_dir():
        result.add_error(folder, "Folder not found.")
    else:
        files = [path for path in sorted(folder.iterdir()) if path.is_file()]
        basename = infer_basename(folder, files)
        result.inferred_basename = basename
        validate_bank_files(folder, basename, result, args.strict)
        validate_xml_files(folder, basename, result, args.strict)

    if args.json:
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "folder": result.folder,
                    "inferred_basename": result.inferred_basename,
                    "errors": findings_to_json(result.errors),
                    "warnings": findings_to_json(result.warnings),
                    "summaries": result.summaries,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_text(result)

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
