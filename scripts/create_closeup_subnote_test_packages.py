#!/usr/bin/env python3
"""Create closeup sub_note_data audio-trigger test packages."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class SubNotePackageError(ValueError):
    """Raised when sub_note package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise SubNotePackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def copy_base_package(base_package: Path, destination: Path, mod_name: str) -> None:
    source = base_package / "data_mods" / "clfn_scale12"
    target = destination / "data_mods" / mod_name
    if not source.is_dir():
        raise SubNotePackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise SubNotePackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def required_text(parent: ET.Element, tag: str) -> str:
    child = parent.find(tag)
    if child is None or child.text is None:
        raise SubNotePackageError(f"missing field: {tag}")
    return child.text


def set_velocity(sub_note: ET.Element, value: int) -> None:
    velocity = sub_note.find("velocity")
    if velocity is None:
        raise SubNotePackageError("missing sub_note velocity")
    velocity.text = str(value)


def patch_velocity_clamp(root: ET.Element, max_velocity: int) -> dict[str, int]:
    changed = 0
    total = 0
    for sub_note in root.findall("./note_data/note/sub_note_data/sub_note"):
        total += 1
        velocity = int(required_text(sub_note, "velocity"))
        if velocity > max_velocity:
            set_velocity(sub_note, max_velocity)
            changed += 1
    return {"sub_notes_seen": total, "sub_notes_muted": 0, "velocities_changed": changed}


def patch_same_pitch_gap_mute(root: ET.Element, gap_msec: int) -> dict[str, int]:
    rows: list[tuple[int, int, int, ET.Element]] = []
    for sub_note in root.findall("./note_data/note/sub_note_data/sub_note"):
        start = int(required_text(sub_note, "start_timing_msec"))
        track = int(required_text(sub_note, "track_index"))
        scale = int(required_text(sub_note, "scale_piano"))
        rows.append((start, track, scale, sub_note))

    rows.sort(key=lambda row: (row[0], row[1], row[2]))
    last_kept_start: dict[tuple[int, int], int] = {}
    muted = 0
    for start, track, scale, sub_note in rows:
        key = (track, scale)
        previous = last_kept_start.get(key)
        if previous is not None and start - previous <= gap_msec:
            set_velocity(sub_note, 0)
            muted += 1
            continue
        last_kept_start[key] = start

    return {"sub_notes_seen": len(rows), "sub_notes_muted": muted, "velocities_changed": muted}


def patch_time_bucket_one_sound(root: ET.Element, bucket_msec: int) -> dict[str, int]:
    buckets: dict[int, list[ET.Element]] = defaultdict(list)
    for sub_note in root.findall("./note_data/note/sub_note_data/sub_note"):
        start = int(required_text(sub_note, "start_timing_msec"))
        buckets[start // bucket_msec].append(sub_note)

    muted = 0
    total = 0
    for bucket in sorted(buckets):
        sub_notes = sorted(
            buckets[bucket],
            key=lambda sub_note: (
                int(required_text(sub_note, "start_timing_msec")),
                int(required_text(sub_note, "track_index")),
                int(required_text(sub_note, "scale_piano")),
            ),
        )
        total += len(sub_notes)
        for sub_note in sub_notes[1:]:
            set_velocity(sub_note, 0)
            muted += 1
    return {"sub_notes_seen": total, "sub_notes_muted": muted, "velocities_changed": muted}


def patch_package(
    package_root: Path,
    mod_name: str,
    patcher: Callable[[ET.Element], dict[str, int]],
) -> dict[str, int]:
    totals = {"files_changed": 0, "sub_notes_seen": 0, "sub_notes_muted": 0, "velocities_changed": 0}
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        stats = patcher(root)
        for key, value in stats.items():
            totals[key] += value
        write_xml(root, xml_path)
        totals["files_changed"] += 1
    return totals


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
    indent(root)
    text = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" + ET.tostring(
        root,
        encoding="unicode",
        short_empty_elements=True,
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def write_install(package_root: Path, mod_name: str, description: str) -> None:
    text = f"""# Closeup sub_note_data Test Package

Variant: {description}

Only `sub_note_data/sub_note/velocity` is changed. Outer `note_data`, timings, scales, tracks, and banks are unchanged.

Copy this folder into the test game's `contents/data_mods`:

```text
{package_root.relative_to(PROJECT_ROOT)}/data_mods/{mod_name}
```

Install only one closeup test package at a time because all variants use the same song basename:

```text
{SONG_BASENAME}
```
"""
    (package_root / "INSTALL.md").write_text(text, encoding="utf-8", newline="\n")


def create_one(
    base_package: Path,
    output_root: Path,
    package_name: str,
    mod_name: str,
    description: str,
    patcher: Callable[[ET.Element], dict[str, int]],
) -> dict[str, str | int]:
    package = output_root / package_name
    copy_base_package(base_package, package, mod_name)
    stats = patch_package(package, mod_name, patcher)
    write_install(package, mod_name, description)
    return {"package": str(package.relative_to(PROJECT_ROOT)), "mod_name": mod_name, **stats}


def create_packages(base_package: Path, output_root: Path) -> list[dict[str, str | int]]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise SubNotePackageError(f"output root must be inside work/: {output_root}") from exc

    variants = [
        (
            "lf_closeup_subnote_vel60",
            "clfn_subvel60",
            "clamp every sub_note velocity to max 60",
            lambda root: patch_velocity_clamp(root, 60),
        ),
        (
            "lf_closeup_subnote_samepitch200",
            "clfn_subsame200",
            "mute same track+scale sub_note triggers within 200ms",
            lambda root: patch_same_pitch_gap_mute(root, 200),
        ),
        (
            "lf_closeup_subnote_bucket80",
            "clfn_subbucket80",
            "keep only one audible sub_note per 80ms time bucket",
            lambda root: patch_time_bucket_one_sound(root, 80),
        ),
    ]
    return [create_one(base_package, output_root, *variant) for variant in variants]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup sub_note_data test packages.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_ab_scale_plus12"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        results = create_packages(args.base_package, args.output_root)
    except (OSError, ET.ParseError, SubNotePackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    for result in results:
        print(
            "OK: "
            f"package={result['package']} mod_name={result['mod_name']} "
            f"files_changed={result['files_changed']} sub_notes_seen={result['sub_notes_seen']} "
            f"sub_notes_muted={result['sub_notes_muted']} "
            f"velocities_changed={result['velocities_changed']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
