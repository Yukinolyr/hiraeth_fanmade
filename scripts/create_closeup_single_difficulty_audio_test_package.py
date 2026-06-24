#!/usr/bin/env python3
"""Create a closeup package where only one difficulty keeps audible sub_notes."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class SingleDifficultyPackageError(ValueError):
    """Raised when package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise SingleDifficultyPackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def copy_base_package(base_package: Path, destination: Path, source_mod: str, target_mod: str) -> None:
    source = base_package / "data_mods" / source_mod
    target = destination / "data_mods" / target_mod
    if not source.is_dir():
        raise SingleDifficultyPackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise SingleDifficultyPackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def set_sub_note_velocity(xml_path: Path, velocity: int) -> int:
    root = ET.parse(xml_path).getroot()
    changed = 0
    for node in root.findall("./note_data/note/sub_note_data/sub_note/velocity"):
        if node.text != str(velocity):
            changed += 1
        node.text = str(velocity)
    write_xml(root, xml_path)
    return changed


def patch_package(package_root: Path, mod_name: str, audible_suffix: str) -> dict[str, int]:
    totals = {
        "files_changed": 0,
        "muted_files": 0,
        "audible_files": 0,
        "velocities_changed": 0,
    }
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        keep_audible = xml_path.name.endswith(f"_{audible_suffix}.xml")
        velocity = -1 if keep_audible else 0
        if keep_audible:
            totals["audible_files"] += 1
        else:
            totals["muted_files"] += 1
        if velocity >= 0:
            totals["velocities_changed"] += set_sub_note_velocity(xml_path, velocity)
        totals["files_changed"] += 1
    if totals["audible_files"] != 1:
        raise SingleDifficultyPackageError(f"expected exactly one audible file, got {totals['audible_files']}")
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


def write_install(package_root: Path, mod_name: str, audible_suffix: str) -> None:
    text = f"""# Closeup Single Difficulty Audio Test Package

Variant: only `{audible_suffix}` keeps audible XML `sub_note_data`; the other difficulties have every `sub_note/velocity` set to 0.

Test by selecting the `{audible_suffix}` difficulty.

Install only one closeup package at a time:

```text
{package_root.relative_to(PROJECT_ROOT)}/data_mods/{mod_name}
```
"""
    (package_root / "INSTALL.md").write_text(text, encoding="utf-8", newline="\n")


def create_package(
    base_package: Path,
    output_root: Path,
    source_mod: str,
    target_mod: str,
    audible_suffix: str,
) -> dict[str, str | int]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise SingleDifficultyPackageError(f"output root must be inside work/: {output_root}") from exc

    package = output_root / f"lf_closeup_audio_only_{audible_suffix}"
    copy_base_package(base_package, package, source_mod, target_mod)
    stats = patch_package(package, target_mod, audible_suffix)
    write_install(package, target_mod, audible_suffix)
    return {
        "package": str(package.relative_to(PROJECT_ROOT)),
        "mod_name": target_mod,
        "audible_suffix": audible_suffix,
        **stats,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup single-difficulty audio test package.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_iso_notimesig"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    parser.add_argument("--source-mod", default="clfn_notimesig")
    parser.add_argument("--target-mod", default="clfn_onlyextreme")
    parser.add_argument("--audible-suffix", default="02extreme")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_package(
            args.base_package,
            args.output_root,
            args.source_mod,
            args.target_mod,
            args.audible_suffix,
        )
    except (OSError, ET.ParseError, SingleDifficultyPackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"package={result['package']} mod_name={result['mod_name']} "
        f"audible_suffix={result['audible_suffix']} files_changed={result['files_changed']} "
        f"audible_files={result['audible_files']} muted_files={result['muted_files']} "
        f"velocities_changed={result['velocities_changed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
