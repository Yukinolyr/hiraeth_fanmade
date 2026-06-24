#!/usr/bin/env python3
"""Create closeup packages that regroup nested sub_note_data."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class SubnoteGroupingPackageError(ValueError):
    """Raised when sub_note grouping package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise SubnoteGroupingPackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def copy_base_package(base_package: Path, destination: Path, source_mod: str, target_mod: str) -> None:
    source = base_package / "data_mods" / source_mod
    target = destination / "data_mods" / target_mod
    if not source.is_dir():
        raise SubnoteGroupingPackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise SubnoteGroupingPackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def required_child(parent: ET.Element, tag: str) -> ET.Element:
    child = parent.find(tag)
    if child is None:
        raise SubnoteGroupingPackageError(f"missing field: {tag}")
    return child


def regroup_all_under_first_note(root: ET.Element) -> dict[str, int]:
    notes = root.findall("./note_data/note")
    if not notes:
        raise SubnoteGroupingPackageError("no notes")

    all_subnotes: list[ET.Element] = []
    for note in notes:
        sub_data = required_child(note, "sub_note_data")
        all_subnotes.extend(list(sub_data.findall("sub_note")))
        sub_data[:] = []

    first_sub_data = required_child(notes[0], "sub_note_data")
    for sub_note in all_subnotes:
        first_sub_data.append(sub_note)

    return {"notes_seen": len(notes), "sub_notes_moved": len(all_subnotes)}


def patch_package(package_root: Path, mod_name: str) -> dict[str, int]:
    totals = {"files_changed": 0, "notes_seen": 0, "sub_notes_moved": 0}
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        stats = regroup_all_under_first_note(root)
        totals["notes_seen"] += stats["notes_seen"]
        totals["sub_notes_moved"] += stats["sub_notes_moved"]
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


def write_install(package_root: Path, mod_name: str) -> None:
    text = f"""# Closeup Subnote Grouping Test Package

Variant: all nested `sub_note` elements are moved under the first visible note.

Changed:

- distribution of nested `sub_note_data`

Unchanged:

- total `sub_note` count
- `sub_note` timing, scale, velocity, track_index
- visible `note_data`
- `track_info`
- `.xsb/.xwb`

Install only one closeup package at a time:

```text
{package_root.relative_to(PROJECT_ROOT)}/data_mods/{mod_name}
```
"""
    (package_root / "INSTALL.md").write_text(text, encoding="utf-8", newline="\n")


def create_package(base_package: Path, output_root: Path, source_mod: str, target_mod: str) -> dict[str, str | int]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise SubnoteGroupingPackageError(f"output root must be inside work/: {output_root}") from exc

    package = output_root / "lf_closeup_subnotes_under_first"
    copy_base_package(base_package, package, source_mod, target_mod)
    stats = patch_package(package, target_mod)
    write_install(package, target_mod)
    return {"package": str(package.relative_to(PROJECT_ROOT)), "mod_name": target_mod, **stats}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup sub_note grouping test package.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_iso_notimesig"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    parser.add_argument("--source-mod", default="clfn_notimesig")
    parser.add_argument("--target-mod", default="clfn_subfirst")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_package(args.base_package, args.output_root, args.source_mod, args.target_mod)
    except (OSError, ET.ParseError, SubnoteGroupingPackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"package={result['package']} mod_name={result['mod_name']} "
        f"files_changed={result['files_changed']} notes_seen={result['notes_seen']} "
        f"sub_notes_moved={result['sub_notes_moved']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
