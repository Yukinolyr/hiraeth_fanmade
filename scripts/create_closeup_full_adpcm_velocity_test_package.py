#!/usr/bin/env python3
"""Create a full-ADPCM closeup package with audible sub_note velocities."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class FullAdpcmVelocityError(ValueError):
    """Raised when the velocity test package cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise FullAdpcmVelocityError(f"Path must stay inside project root: {path}") from exc
    return resolved


def copy_base_package(base_package: Path, destination: Path, source_mod: str, target_mod: str) -> None:
    source = base_package / "data_mods" / source_mod
    target = destination / "data_mods" / target_mod
    if not source.is_dir():
        raise FullAdpcmVelocityError(f"source mod folder not found: {source}")
    if destination.exists():
        raise FullAdpcmVelocityError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def set_velocity(package_root: Path, mod_name: str, velocity_value: int) -> dict[str, int]:
    files_changed = 0
    velocities_changed = 0
    total = 0
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        for velocity in root.findall("./note_data/note/sub_note_data/sub_note/velocity"):
            total += 1
            new_value = str(velocity_value)
            if velocity.text != new_value:
                velocities_changed += 1
            velocity.text = new_value
        write_xml(root, xml_path)
        files_changed += 1
    return {
        "files_changed": files_changed,
        "sub_notes_seen": total,
        "velocities_changed": velocities_changed,
    }


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


def write_install(package_root: Path, mod_name: str, velocity_value: int) -> None:
    text = f"""# Closeup Full ADPCM + sub_note Velocity Test

Variant: full ADPCM main audio plus audible `sub_note_data`.

Changed:

- all XML `sub_note/velocity` set to `{velocity_value}`

Unchanged:

- ADPCM main XWB
- preview XWB
- note timing
- scale
- track_index

Purpose:

- compare against `clfn_fulladpcm` where every sub_note velocity is 0
- if echo returns here, the issue is the internal `key_apiano1` sub_note playback path

Copy this folder into the test game's `contents/data_mods`:

```text
{package_root.relative_to(PROJECT_ROOT)}/data_mods/{mod_name}
```
"""
    (package_root / "INSTALL.md").write_text(text, encoding="utf-8", newline="\n")


def create_package(base_package: Path, output_root: Path, velocity_value: int) -> dict[str, str | int]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise FullAdpcmVelocityError(f"output root must be inside work/: {output_root}") from exc

    package = output_root / f"lf_closeup_full_adpcm_vel{velocity_value}"
    mod_name = f"clfn_fullv{velocity_value}"
    copy_base_package(base_package, package, "clfn_fulladpcm", mod_name)
    stats = set_velocity(package, mod_name, velocity_value)
    write_install(package, mod_name, velocity_value)
    return {"package": str(package.relative_to(PROJECT_ROOT)), "mod_name": mod_name, **stats}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create full-ADPCM sub_note velocity test package.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_full_audio_adpcm"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    parser.add_argument("--velocity", type=int, default=100)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_package(args.base_package, args.output_root, args.velocity)
    except (OSError, ET.ParseError, FullAdpcmVelocityError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(
        "OK: "
        f"package={result['package']} mod_name={result['mod_name']} "
        f"files_changed={result['files_changed']} sub_notes_seen={result['sub_notes_seen']} "
        f"velocities_changed={result['velocities_changed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
