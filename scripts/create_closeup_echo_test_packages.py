#!/usr/bin/env python3
"""Create closeup echo-isolation test packages from the scale+12 package."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class EchoPackageError(ValueError):
    """Raised when echo package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise EchoPackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def copy_base_package(base_package: Path, destination: Path, source_mod: str, target_mod: str) -> None:
    source = base_package / "data_mods" / source_mod
    target = destination / "data_mods" / target_mod
    if not source.is_dir():
        raise EchoPackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise EchoPackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def patch_velocity_zero(package_root: Path, mod_name: str) -> dict[str, int]:
    changed = 0
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        for velocity in root.findall("./note_data/note/sub_note_data/sub_note/velocity"):
            if velocity.text != "0":
                changed += 1
            velocity.text = "0"
        write_xml(root, xml_path)
    return {"velocity_changed": changed}


def patch_note_type_zero(package_root: Path, mod_name: str) -> dict[str, int]:
    changed = 0
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        for note_type in root.findall("./note_data/note/note_type"):
            if note_type.text != "0":
                changed += 1
            note_type.text = "0"
        write_xml(root, xml_path)
    return {"note_type_changed": changed}


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
    text = f"""# Closeup Echo Test Package

Variant: {description}

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


def create_packages(base_package: Path, output_root: Path) -> dict[str, str | int]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise EchoPackageError(f"output root must be inside work/: {output_root}") from exc

    velocity_pkg = output_root / "lf_closeup_echo_velocity0"
    note_type_pkg = output_root / "lf_closeup_echo_notetype0"

    copy_base_package(base_package, velocity_pkg, "clfn_scale12", "clfn_vel0")
    velocity_stats = patch_velocity_zero(velocity_pkg, "clfn_vel0")
    write_install(velocity_pkg, "clfn_vel0", "scale+12 baseline with all sub_note velocity values set to 0")

    copy_base_package(base_package, note_type_pkg, "clfn_scale12", "clfn_nt0")
    note_type_stats = patch_note_type_zero(note_type_pkg, "clfn_nt0")
    write_install(note_type_pkg, "clfn_nt0", "scale+12 baseline with all note_type values set to 0")

    return {
        "velocity_package": str(velocity_pkg.relative_to(PROJECT_ROOT)),
        "note_type_package": str(note_type_pkg.relative_to(PROJECT_ROOT)),
        **velocity_stats,
        **note_type_stats,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup echo-isolation packages.")
    parser.add_argument(
        "--base-package",
        type=Path,
        default=Path("work/lf_closeup_ab_scale_plus12"),
    )
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_packages(args.base_package, args.output_root)
    except (OSError, ET.ParseError, EchoPackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"velocity_package={result['velocity_package']} "
        f"velocity_changed={result['velocity_changed']} "
        f"note_type_package={result['note_type_package']} "
        f"note_type_changed={result['note_type_changed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
