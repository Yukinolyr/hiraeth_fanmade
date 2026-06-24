#!/usr/bin/env python3
"""Create closeup packages that alter note key-index trigger ranges."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class KeyRangePackageError(ValueError):
    """Raised when key range package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise KeyRangePackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def copy_base_package(base_package: Path, destination: Path, source_mod: str, target_mod: str) -> None:
    source = base_package / "data_mods" / source_mod
    target = destination / "data_mods" / target_mod
    if not source.is_dir():
        raise KeyRangePackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise KeyRangePackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def required_child(parent: ET.Element, tag: str) -> ET.Element:
    child = parent.find(tag)
    if child is None:
        raise KeyRangePackageError(f"missing field: {tag}")
    return child


def patch_xml(root: ET.Element, mode: str) -> dict[str, int]:
    changed = 0
    for note in root.findall("./note_data/note"):
        min_node = required_child(note, "min_key_index")
        max_node = required_child(note, "max_key_index")
        old_min = int(min_node.text or "0")
        old_max = int(max_node.text or "0")
        if old_max < old_min:
            raise KeyRangePackageError(f"invalid key range: {old_min}..{old_max}")

        if mode == "single":
            center = (old_min + old_max) // 2
            new_min = center
            new_max = center
        elif mode == "width2":
            new_min = old_min
            new_max = old_min + 2
        else:
            raise KeyRangePackageError(f"unsupported mode: {mode}")

        if old_min != new_min or old_max != new_max:
            changed += 1
        min_node.text = str(new_min)
        max_node.text = str(new_max)
    return {"key_ranges_changed": changed}


def patch_package(package_root: Path, mod_name: str, mode: str) -> dict[str, int]:
    totals = {"files_changed": 0, "key_ranges_changed": 0}
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        stats = patch_xml(root, mode)
        totals["key_ranges_changed"] += stats["key_ranges_changed"]
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


def write_install(package_root: Path, mod_name: str, mode: str) -> None:
    text = f"""# Closeup Key Range Test Package

Variant: `{mode}` key-index trigger ranges.

Changed:

- `note_data/note/min_key_index`
- `note_data/note/max_key_index`

Unchanged:

- `scale_piano`
- nested `sub_note_data`
- `track_info`
- `.xsb/.xwb`

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
    mode: str,
) -> dict[str, str | int]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise KeyRangePackageError(f"output root must be inside work/: {output_root}") from exc

    package = output_root / f"lf_closeup_keyrange_{mode}"
    copy_base_package(base_package, package, source_mod, target_mod)
    stats = patch_package(package, target_mod, mode)
    write_install(package, target_mod, mode)
    return {
        "package": str(package.relative_to(PROJECT_ROOT)),
        "mod_name": target_mod,
        "mode": mode,
        **stats,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup key range test package.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_iso_notimesig"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    parser.add_argument("--source-mod", default="clfn_notimesig")
    parser.add_argument("--target-mod", default="clfn_keysingle")
    parser.add_argument("--mode", choices=("single", "width2"), default="single")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_package(
            args.base_package,
            args.output_root,
            args.source_mod,
            args.target_mod,
            args.mode,
        )
    except (OSError, ET.ParseError, KeyRangePackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"package={result['package']} mod_name={result['mod_name']} mode={result['mode']} "
        f"files_changed={result['files_changed']} key_ranges_changed={result['key_ranges_changed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
