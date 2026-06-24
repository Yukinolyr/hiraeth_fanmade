#!/usr/bin/env python3
"""Create a closeup package that reindexes notes by hand/track groups."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class IndexPackageError(ValueError):
    """Raised when index package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise IndexPackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def copy_base_package(base_package: Path, destination: Path, mod_name: str) -> None:
    source = base_package / "data_mods" / "clfn_scale12"
    target = destination / "data_mods" / mod_name
    if not source.is_dir():
        raise IndexPackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise IndexPackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def required_text(parent: ET.Element, tag: str) -> str:
    child = parent.find(tag)
    if child is None or child.text is None:
        raise IndexPackageError(f"missing field: {tag}")
    return child.text


def patch_indexes(root: ET.Element) -> dict[str, int]:
    notes = root.findall("./note_data/note")
    right_hand = []
    left_hand = []
    other_hand = []
    for note in notes:
        hand = required_text(note, "hand")
        if hand == "0":
            right_hand.append(note)
        elif hand == "1":
            left_hand.append(note)
        else:
            other_hand.append(note)

    next_index = 1
    changed = 0
    for group in (right_hand, left_hand, other_hand):
        for note in group:
            index = note.find("index")
            if index is None:
                raise IndexPackageError("missing note index")
            new_index = str(next_index)
            if index.text != new_index:
                changed += 1
            index.text = new_index
            next_index += 1

    return {
        "notes_seen": len(notes),
        "right_hand_notes": len(right_hand),
        "left_hand_notes": len(left_hand),
        "other_hand_notes": len(other_hand),
        "indexes_changed": changed,
    }


def patch_package(package_root: Path, mod_name: str) -> dict[str, int]:
    totals = {
        "files_changed": 0,
        "notes_seen": 0,
        "right_hand_notes": 0,
        "left_hand_notes": 0,
        "other_hand_notes": 0,
        "indexes_changed": 0,
    }
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        stats = patch_indexes(root)
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


def write_install(package_root: Path, mod_name: str) -> None:
    text = f"""# Closeup Index By Hand Test Package

Variant: reindex outer `note_data/note/index` by hand groups.

Rules:

- `hand=0` right hand first, starting at `1`.
- `hand=1` left hand after right hand.
- Other hand values, if any, are placed last.

Unchanged:

- `sub_note_data`
- note timings
- note scales
- note velocity
- note track_index
- banks

Copy this folder into the test game's `contents/data_mods`:

```text
{package_root.relative_to(PROJECT_ROOT)}/data_mods/{mod_name}
```
"""
    (package_root / "INSTALL.md").write_text(text, encoding="utf-8", newline="\n")


def create_package(base_package: Path, output_root: Path) -> dict[str, str | int]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise IndexPackageError(f"output root must be inside work/: {output_root}") from exc

    package = output_root / "lf_closeup_index_by_hand"
    mod_name = "clfn_idxhand"
    copy_base_package(base_package, package, mod_name)
    stats = patch_package(package, mod_name)
    write_install(package, mod_name)
    return {"package": str(package.relative_to(PROJECT_ROOT)), "mod_name": mod_name, **stats}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup index-by-hand test package.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_ab_scale_plus12"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_package(args.base_package, args.output_root)
    except (OSError, ET.ParseError, IndexPackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"package={result['package']} mod_name={result['mod_name']} "
        f"files_changed={result['files_changed']} notes_seen={result['notes_seen']} "
        f"right_hand_notes={result['right_hand_notes']} "
        f"left_hand_notes={result['left_hand_notes']} "
        f"other_hand_notes={result['other_hand_notes']} "
        f"indexes_changed={result['indexes_changed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
