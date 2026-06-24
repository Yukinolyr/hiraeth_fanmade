#!/usr/bin/env python3
"""Create a closeup package with note/sub_note timings shifted later."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class OffsetPackageError(ValueError):
    """Raised when offset package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise OffsetPackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def copy_base_package(base_package: Path, destination: Path, mod_name: str) -> None:
    source = base_package / "data_mods" / "clfn_scale12"
    target = destination / "data_mods" / mod_name
    if not source.is_dir():
        raise OffsetPackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise OffsetPackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def add_to_child(parent: ET.Element, tag: str, offset: int) -> None:
    child = parent.find(tag)
    if child is None or child.text is None:
        raise OffsetPackageError(f"missing field: {tag}")
    child.text = str(int(child.text) + offset)


def patch_xml(root: ET.Element, offset: int) -> dict[str, int]:
    notes = 0
    sub_notes = 0
    zones = 0

    header = root.find("header")
    if header is None:
        raise OffsetPackageError("missing header")
    add_to_child(header, "music_finish_time_msec", offset)

    for note in root.findall("./note_data/note"):
        add_to_child(note, "start_timing_msec", offset)
        add_to_child(note, "end_timing_msec", offset)
        notes += 1
        for sub_note in note.findall("./sub_note_data/sub_note"):
            add_to_child(sub_note, "start_timing_msec", offset)
            add_to_child(sub_note, "end_timing_msec", offset)
            sub_notes += 1

    for zone in root.findall("./velocity_zone_data/velocity_zone"):
        add_to_child(zone, "start_timing_msec", offset)
        add_to_child(zone, "end_timing_msec", offset)
        zones += 1

    return {"notes_shifted": notes, "sub_notes_shifted": sub_notes, "zones_shifted": zones}


def patch_package(package_root: Path, mod_name: str, offset: int) -> dict[str, int]:
    totals = {"files_changed": 0, "notes_shifted": 0, "sub_notes_shifted": 0, "zones_shifted": 0}
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        stats = patch_xml(root, offset)
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


def write_install(package_root: Path, mod_name: str, offset: int) -> None:
    text = f"""# Closeup Time Offset Test Package

Variant: shift every note and sub_note timing later by {offset}ms.

Changed:

- `note_data/note/start_timing_msec`
- `note_data/note/end_timing_msec`
- `sub_note_data/sub_note/start_timing_msec`
- `sub_note_data/sub_note/end_timing_msec`
- `velocity_zone_data` timing
- `header/music_finish_time_msec`

Unchanged:

- scale
- velocity
- track_index
- note_type
- event_data
- beat_data
- banks

Copy this folder into the test game's `contents/data_mods`:

```text
{package_root.relative_to(PROJECT_ROOT)}/data_mods/{mod_name}
```
"""
    (package_root / "INSTALL.md").write_text(text, encoding="utf-8", newline="\n")


def create_package(base_package: Path, output_root: Path, offset: int) -> dict[str, str | int]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise OffsetPackageError(f"output root must be inside work/: {output_root}") from exc

    package = output_root / f"lf_closeup_offset_{offset}ms"
    mod_name = f"clfn_offset{offset}"
    copy_base_package(base_package, package, mod_name)
    stats = patch_package(package, mod_name, offset)
    write_install(package, mod_name, offset)
    return {"package": str(package.relative_to(PROJECT_ROOT)), "mod_name": mod_name, "offset": offset, **stats}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup time-offset test package.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_ab_scale_plus12"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    parser.add_argument("--offset", type=int, default=1500)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_package(args.base_package, args.output_root, args.offset)
    except (OSError, ET.ParseError, OffsetPackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"package={result['package']} mod_name={result['mod_name']} offset={result['offset']} "
        f"files_changed={result['files_changed']} notes_shifted={result['notes_shifted']} "
        f"sub_notes_shifted={result['sub_notes_shifted']} zones_shifted={result['zones_shifted']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
