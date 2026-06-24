#!/usr/bin/env python3
"""Create a closeup package with chart length metadata tightened to chart end."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class FinishPackageError(ValueError):
    """Raised when finish-time package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise FinishPackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def copy_base_package(base_package: Path, destination: Path, mod_name: str) -> None:
    source = base_package / "data_mods" / "clfn_scale12"
    target = destination / "data_mods" / mod_name
    if not source.is_dir():
        raise FinishPackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise FinishPackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def required_child(parent: ET.Element, tag: str) -> ET.Element:
    child = parent.find(tag)
    if child is None:
        raise FinishPackageError(f"missing field: {tag}")
    return child


def child_text(tag: str, value: str | int) -> ET.Element:
    child = ET.Element(tag)
    child.text = str(value)
    return child


def trim_beat_data(root: ET.Element, new_finish: int) -> int:
    beat_data = required_child(root, "beat_data")
    beats = beat_data.findall("beat")
    kept = [beat for beat in beats if int(required_child(beat, "start_timing_msec").text or "0") <= new_finish]
    removed = len(beats) - len(kept)
    if kept and int(required_child(kept[-1], "start_timing_msec").text or "0") != new_finish:
        index = int(required_child(kept[-1], "index").text or "0") + 1
        beat = ET.Element("beat")
        beat.extend([child_text("index", index), child_text("start_timing_msec", new_finish)])
        kept.append(beat)
    beat_data[:] = kept
    return removed


def clamp_velocity_zones(root: ET.Element, new_finish: int) -> int:
    velocity_zone_data = root.find("velocity_zone_data")
    if velocity_zone_data is None:
        return 0
    changed = 0
    kept = []
    for zone in velocity_zone_data.findall("velocity_zone"):
        start = int(required_child(zone, "start_timing_msec").text or "0")
        end_node = required_child(zone, "end_timing_msec")
        end = int(end_node.text or "0")
        if start > new_finish:
            changed += 1
            continue
        if end > new_finish:
            end_node.text = str(new_finish)
            changed += 1
        kept.append(zone)
    velocity_zone_data[:] = kept
    for index, zone in enumerate(velocity_zone_data.findall("velocity_zone")):
        required_child(zone, "index").text = str(index)
    return changed


def patch_xml(root: ET.Element, tail_msec: int) -> dict[str, int]:
    header = required_child(root, "header")
    finish = required_child(header, "music_finish_time_msec")
    old_finish = int(finish.text or "0")

    max_end = 0
    for node in root.findall("./note_data/note/end_timing_msec"):
        max_end = max(max_end, int(node.text or "0"))
    for node in root.findall("./note_data/note/sub_note_data/sub_note/end_timing_msec"):
        max_end = max(max_end, int(node.text or "0"))

    new_finish = max_end + tail_msec
    finish.text = str(new_finish)
    removed_beats = trim_beat_data(root, new_finish)
    changed_zones = clamp_velocity_zones(root, new_finish)
    return {
        "old_finish_sum": old_finish,
        "new_finish_sum": new_finish,
        "max_end": max_end,
        "removed_beats": removed_beats,
        "changed_zones": changed_zones,
    }


def patch_package(package_root: Path, mod_name: str, tail_msec: int) -> dict[str, int]:
    totals = {
        "files_changed": 0,
        "old_finish_sum": 0,
        "new_finish_sum": 0,
        "max_end": 0,
        "removed_beats": 0,
        "changed_zones": 0,
    }
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        stats = patch_xml(root, tail_msec)
        totals["old_finish_sum"] += stats["old_finish_sum"]
        totals["new_finish_sum"] += stats["new_finish_sum"]
        totals["max_end"] = max(totals["max_end"], stats["max_end"])
        totals["removed_beats"] += stats["removed_beats"]
        totals["changed_zones"] += stats["changed_zones"]
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


def write_install(package_root: Path, mod_name: str, tail_msec: int) -> None:
    text = f"""# Closeup Finish Time Test Package

Variant: set chart length metadata to the last note/sub_note end plus {tail_msec}ms.

Changed:

- `header/music_finish_time_msec`
- `beat_data`, trimmed to the new finish
- `velocity_zone_data`, clamped to the new finish

Notes, sub_notes, events, and banks are unchanged.

Copy this folder into the test game's `contents/data_mods`:

```text
{package_root.relative_to(PROJECT_ROOT)}/data_mods/{mod_name}
```
"""
    (package_root / "INSTALL.md").write_text(text, encoding="utf-8", newline="\n")


def create_package(base_package: Path, output_root: Path, tail_msec: int) -> dict[str, str | int]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise FinishPackageError(f"output root must be inside work/: {output_root}") from exc

    package = output_root / f"lf_closeup_finish_tail{tail_msec}"
    mod_name = f"clfn_finish{tail_msec}"
    copy_base_package(base_package, package, mod_name)
    stats = patch_package(package, mod_name, tail_msec)
    write_install(package, mod_name, tail_msec)
    return {"package": str(package.relative_to(PROJECT_ROOT)), "mod_name": mod_name, "tail_msec": tail_msec, **stats}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup finish-time test package.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_ab_scale_plus12"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    parser.add_argument("--tail-msec", type=int, default=2000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_package(args.base_package, args.output_root, args.tail_msec)
    except (OSError, ET.ParseError, FinishPackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"package={result['package']} mod_name={result['mod_name']} "
        f"tail_msec={result['tail_msec']} files_changed={result['files_changed']} "
        f"max_end={result['max_end']} old_finish_sum={result['old_finish_sum']} "
        f"new_finish_sum={result['new_finish_sum']} removed_beats={result['removed_beats']} "
        f"changed_zones={result['changed_zones']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
