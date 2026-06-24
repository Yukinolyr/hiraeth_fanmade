#!/usr/bin/env python3
"""Create closeup beat_data and velocity isolation test packages."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class BeatVelocityPackageError(ValueError):
    """Raised when package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise BeatVelocityPackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def copy_base_package(base_package: Path, destination: Path, mod_name: str) -> None:
    source = base_package / "data_mods" / "clfn_scale12"
    target = destination / "data_mods" / mod_name
    if not source.is_dir():
        raise BeatVelocityPackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise BeatVelocityPackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def child_text(tag: str, value: str | int) -> ET.Element:
    child = ET.Element(tag)
    child.text = str(value)
    return child


def required_text(parent: ET.Element, tag: str) -> str:
    child = parent.find(tag)
    if child is None or child.text is None:
        raise BeatVelocityPackageError(f"missing field: {tag}")
    return child.text


def patch_dense_beat_data(root: ET.Element, interval_msec: int) -> dict[str, int]:
    beat_data = root.find("beat_data")
    if beat_data is None:
        raise BeatVelocityPackageError("missing beat_data")
    header = root.find("header")
    if header is None:
        raise BeatVelocityPackageError("missing header")
    finish = int(required_text(header, "music_finish_time_msec"))

    old_count = len(beat_data.findall("beat"))
    beats: list[ET.Element] = []
    index = 0
    timing = 0
    while timing <= finish:
        beat = ET.Element("beat")
        beat.extend([child_text("index", index), child_text("start_timing_msec", timing)])
        beats.append(beat)
        index += 1
        timing += interval_msec
    if beats[-1].findtext("start_timing_msec") != str(finish):
        beat = ET.Element("beat")
        beat.extend([child_text("index", index), child_text("start_timing_msec", finish)])
        beats.append(beat)

    beat_data[:] = beats
    return {"old_beats": old_count, "new_beats": len(beats), "velocities_changed": 0}


def patch_velocity_100(root: ET.Element) -> dict[str, int]:
    changed = 0
    total = 0
    for velocity in root.findall("./note_data/note/sub_note_data/sub_note/velocity"):
        total += 1
        if velocity.text != "100":
            changed += 1
        velocity.text = "100"
    return {"old_beats": 0, "new_beats": 0, "velocities_changed": changed, "sub_notes_seen": total}


def patch_package(package_root: Path, mod_name: str, patcher) -> dict[str, int]:
    totals = {
        "files_changed": 0,
        "old_beats": 0,
        "new_beats": 0,
        "velocities_changed": 0,
        "sub_notes_seen": 0,
    }
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        stats = patcher(root)
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


def write_install(package_root: Path, mod_name: str, description: str) -> None:
    text = f"""# Closeup Beat/Velocity Test Package

Variant: {description}

Copy this folder into the test game's `contents/data_mods`:

```text
{package_root.relative_to(PROJECT_ROOT)}/data_mods/{mod_name}
```
"""
    (package_root / "INSTALL.md").write_text(text, encoding="utf-8", newline="\n")


def create_one(base_package: Path, output_root: Path, package_name: str, mod_name: str, description: str, patcher):
    package = output_root / package_name
    copy_base_package(base_package, package, mod_name)
    stats = patch_package(package, mod_name, patcher)
    write_install(package, mod_name, description)
    return {"package": str(package.relative_to(PROJECT_ROOT)), "mod_name": mod_name, **stats}


def create_packages(base_package: Path, output_root: Path, beat_interval: int) -> list[dict[str, str | int]]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise BeatVelocityPackageError(f"output root must be inside work/: {output_root}") from exc

    return [
        create_one(
            base_package,
            output_root,
            f"lf_closeup_beat_{beat_interval}ms",
            f"clfn_beat{beat_interval}",
            f"rebuild only beat_data at {beat_interval}ms intervals",
            lambda root: patch_dense_beat_data(root, beat_interval),
        ),
        create_one(
            base_package,
            output_root,
            "lf_closeup_subnote_velocity100",
            "clfn_vel100",
            "set every sub_note velocity to 100",
            patch_velocity_100,
        ),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup beat/velocity test packages.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_ab_scale_plus12"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    parser.add_argument("--beat-interval", type=int, default=375)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        results = create_packages(args.base_package, args.output_root, args.beat_interval)
    except (OSError, ET.ParseError, BeatVelocityPackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    for result in results:
        print(
            "OK: "
            f"package={result['package']} mod_name={result['mod_name']} "
            f"files_changed={result['files_changed']} old_beats={result['old_beats']} "
            f"new_beats={result['new_beats']} sub_notes_seen={result['sub_notes_seen']} "
            f"velocities_changed={result['velocities_changed']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
