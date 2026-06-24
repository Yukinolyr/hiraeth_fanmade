#!/usr/bin/env python3
"""Create a closeup package with sub_note timings made relative to parent notes."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class SubnoteRelativePackageError(ValueError):
    """Raised when package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise SubnoteRelativePackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def copy_base_package(base_package: Path, destination: Path, source_mod: str, target_mod: str) -> None:
    source = base_package / "data_mods" / source_mod
    target = destination / "data_mods" / target_mod
    if not source.is_dir():
        raise SubnoteRelativePackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise SubnoteRelativePackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def required_child(parent: ET.Element, tag: str) -> ET.Element:
    child = parent.find(tag)
    if child is None:
        raise SubnoteRelativePackageError(f"missing field: {tag}")
    return child


def patch_xml(root: ET.Element) -> dict[str, int]:
    changed = 0
    for note in root.findall("./note_data/note"):
        note_start = int(required_child(note, "start_timing_msec").text or "0")
        for sub_note in note.findall("./sub_note_data/sub_note"):
            start_node = required_child(sub_note, "start_timing_msec")
            end_node = required_child(sub_note, "end_timing_msec")
            old_start = int(start_node.text or "0")
            old_end = int(end_node.text or "0")
            new_start = old_start - note_start
            new_end = old_end - note_start
            if new_start < 0 or new_end < new_start:
                raise SubnoteRelativePackageError(
                    f"invalid relative sub_note time: {old_start}..{old_end} parent={note_start}"
                )
            if old_start != new_start or old_end != new_end:
                changed += 1
            start_node.text = str(new_start)
            end_node.text = str(new_end)
    return {"sub_notes_changed": changed}


def patch_package(package_root: Path, mod_name: str) -> dict[str, int]:
    totals = {"files_changed": 0, "sub_notes_changed": 0}
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        stats = patch_xml(root)
        totals["sub_notes_changed"] += stats["sub_notes_changed"]
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
    text = f"""# Closeup Subnote Relative Time Test Package

Variant: every nested `sub_note` timing is made relative to its parent note.

Changed:

- `sub_note/start_timing_msec`
- `sub_note/end_timing_msec`

Unchanged:

- parent `note` timing
- `scale_piano`
- `velocity`
- `track_index`
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
        raise SubnoteRelativePackageError(f"output root must be inside work/: {output_root}") from exc

    package = output_root / "lf_closeup_subnote_relative_time"
    copy_base_package(base_package, package, source_mod, target_mod)
    stats = patch_package(package, target_mod)
    write_install(package, target_mod)
    return {"package": str(package.relative_to(PROJECT_ROOT)), "mod_name": target_mod, **stats}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup sub_note relative time test package.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_iso_notimesig"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    parser.add_argument("--source-mod", default="clfn_notimesig")
    parser.add_argument("--target-mod", default="clfn_subrel")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_package(args.base_package, args.output_root, args.source_mod, args.target_mod)
    except (OSError, ET.ParseError, SubnoteRelativePackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"package={result['package']} mod_name={result['mod_name']} "
        f"files_changed={result['files_changed']} sub_notes_changed={result['sub_notes_changed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
