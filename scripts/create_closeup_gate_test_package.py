#!/usr/bin/env python3
"""Create a closeup test package with fixed short note/sub_note gates."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class GatePackageError(ValueError):
    """Raised when gate package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise GatePackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def copy_base_package(base_package: Path, destination: Path, source_mod: str, target_mod: str) -> None:
    source = base_package / "data_mods" / source_mod
    target = destination / "data_mods" / target_mod
    if not source.is_dir():
        raise GatePackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise GatePackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def elem_int(parent: ET.Element, tag: str) -> int:
    child = parent.find(tag)
    if child is None or child.text is None:
        raise GatePackageError(f"missing field: {tag}")
    return int(child.text)


def set_child(parent: ET.Element, tag: str, value: int) -> None:
    child = parent.find(tag)
    if child is None:
        raise GatePackageError(f"missing field: {tag}")
    child.text = str(value)


def patch_gate(package_root: Path, mod_name: str, gate_msec: int) -> dict[str, int]:
    changed_notes = 0
    changed_sub_notes = 0
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        for note in root.findall("./note_data/note"):
            start = elem_int(note, "start_timing_msec")
            set_child(note, "end_timing_msec", start + gate_msec)
            set_child(note, "gate_time_msec", gate_msec)
            changed_notes += 1
            for sub_note in note.findall("./sub_note_data/sub_note"):
                sub_start = elem_int(sub_note, "start_timing_msec")
                set_child(sub_note, "end_timing_msec", sub_start + gate_msec)
                changed_sub_notes += 1
        write_xml(root, xml_path)
    return {"notes_changed": changed_notes, "sub_notes_changed": changed_sub_notes}


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


def write_install(package_root: Path, mod_name: str, gate_msec: int) -> None:
    text = f"""# Closeup Gate Test Package

Variant: scale+12 baseline with every note and sub_note gate forced to {gate_msec}ms.

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


def create_package(base_package: Path, output_root: Path, gate_msec: int) -> dict[str, str | int]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise GatePackageError(f"output root must be inside work/: {output_root}") from exc

    package = output_root / f"lf_closeup_gate_{gate_msec}ms"
    mod_name = f"clfn_gate{gate_msec}"
    copy_base_package(base_package, package, "clfn_scale12", mod_name)
    stats = patch_gate(package, mod_name, gate_msec)
    write_install(package, mod_name, gate_msec)
    return {
        "package": str(package.relative_to(PROJECT_ROOT)),
        "mod_name": mod_name,
        "gate_msec": gate_msec,
        **stats,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup fixed-gate package.")
    parser.add_argument(
        "--base-package",
        type=Path,
        default=Path("work/lf_closeup_ab_scale_plus12"),
    )
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    parser.add_argument("--gate-msec", type=int, default=60)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_package(args.base_package, args.output_root, args.gate_msec)
    except (OSError, ET.ParseError, GatePackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"package={result['package']} mod_name={result['mod_name']} "
        f"gate_msec={result['gate_msec']} notes_changed={result['notes_changed']} "
        f"sub_notes_changed={result['sub_notes_changed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
