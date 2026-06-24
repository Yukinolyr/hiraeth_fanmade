#!/usr/bin/env python3
"""Create closeup A/B test packages from the current filename-only package."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class PackageError(ValueError):
    """Raised when A/B package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise PackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def elem_int(parent: ET.Element, tag: str) -> int:
    child = parent.find(tag)
    if child is None or child.text is None:
        raise PackageError(f"missing field: {tag}")
    return int(child.text)


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


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def copy_base_package(base_package: Path, destination: Path, mod_name: str) -> None:
    source_mod = base_package / "data_mods" / "clfn"
    target_mod = destination / "data_mods" / mod_name
    if not source_mod.is_dir():
        raise PackageError(f"source mod folder not found: {source_mod}")
    if destination.exists():
        raise PackageError(f"destination already exists: {destination}")
    target_mod.parent.mkdir(parents=True)
    shutil.copytree(source_mod, target_mod)


def patch_all_track_one(package_root: Path, mod_name: str) -> dict[str, int]:
    changed = 0
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        for sub_note in root.findall("./note_data/note/sub_note_data/sub_note"):
            track_index = sub_note.find("track_index")
            if track_index is None:
                raise PackageError(f"missing track_index in {xml_path}")
            if track_index.text != "1":
                changed += 1
            track_index.text = "1"
        write_xml(root, xml_path)
    return {"track_index_changed": changed}


def patch_scale_plus(package_root: Path, mod_name: str, delta: int) -> dict[str, int]:
    changed = 0
    min_scale: int | None = None
    max_scale: int | None = None
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        values: list[int] = []
        for scale in root.findall(".//scale_piano"):
            value = int(scale.text or "0") + delta
            if not 0 <= value <= 255:
                raise PackageError(f"scale_piano out of u8 range after patch: {value}")
            scale.text = str(value)
            values.append(value)
            changed += 1
        if not values:
            raise PackageError(f"no scale_piano fields found: {xml_path}")
        header = root.find("header")
        if header is None:
            raise PackageError(f"missing header: {xml_path}")
        header.find("min_scale").text = str(min(values))  # type: ignore[union-attr]
        header.find("max_scale").text = str(max(values))  # type: ignore[union-attr]
        min_scale = min(values) if min_scale is None else min(min_scale, min(values))
        max_scale = max(values) if max_scale is None else max(max_scale, max(values))
        write_xml(root, xml_path)
    return {"scale_values_changed": changed, "min_scale": min_scale or 0, "max_scale": max_scale or 0}


def write_install(package_root: Path, mod_name: str, description: str) -> None:
    text = f"""# Closeup A/B Test Package

Variant: {description}

Copy this folder into the test game's `contents/data_mods`:

```text
{package_root.relative_to(PROJECT_ROOT)}/data_mods/{mod_name}
```

Install only one closeup A/B package at a time because all variants use the same song basename:

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
        raise PackageError(f"output root must be inside work/: {output_root}") from exc

    track_pkg = output_root / "lf_closeup_ab_track1"
    scale_pkg = output_root / "lf_closeup_ab_scale_plus12"

    copy_base_package(base_package, track_pkg, "clfn_track1")
    track_stats = patch_all_track_one(track_pkg, "clfn_track1")
    write_install(track_pkg, "clfn_track1", "all sub_note/track_index values set to 1")

    copy_base_package(base_package, scale_pkg, "clfn_scale12")
    scale_stats = patch_scale_plus(scale_pkg, "clfn_scale12", 12)
    write_install(scale_pkg, "clfn_scale12", "all note and sub_note scale_piano values increased by 12")

    return {
        "track_package": str(track_pkg.relative_to(PROJECT_ROOT)),
        "scale_package": str(scale_pkg.relative_to(PROJECT_ROOT)),
        **track_stats,
        **scale_stats,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup track-index and scale A/B packages.")
    parser.add_argument(
        "--base-package",
        type=Path,
        default=Path("work/lf_closeup_add_filenameonly"),
    )
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_packages(args.base_package, args.output_root)
    except (OSError, ET.ParseError, PackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(
        "OK: "
        f"track_package={result['track_package']} "
        f"track_index_changed={result['track_index_changed']} "
        f"scale_package={result['scale_package']} "
        f"scale_values_changed={result['scale_values_changed']} "
        f"scale_range={result['min_scale']}..{result['max_scale']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
