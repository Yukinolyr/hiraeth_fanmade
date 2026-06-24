#!/usr/bin/env python3
"""Create a closeup package with BPM metadata and beat_data rebuilt."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class BpmPackageError(ValueError):
    """Raised when BPM test package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise BpmPackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def copy_base_package(base_package: Path, destination: Path, source_mod: str, target_mod: str) -> None:
    source = base_package / "data_mods" / source_mod
    target = destination / "data_mods" / target_mod
    if not source.is_dir():
        raise BpmPackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise BpmPackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def required_child(parent: ET.Element, tag: str) -> ET.Element:
    child = parent.find(tag)
    if child is None:
        raise BpmPackageError(f"missing field: {tag}")
    return child


def child_text(tag: str, value: int | str) -> ET.Element:
    child = ET.Element(tag)
    child.text = str(value)
    return child


def chart_max_end(root: ET.Element) -> int:
    max_end = 0
    for node in root.findall("./note_data/note/end_timing_msec"):
        max_end = max(max_end, int(node.text or "0"))
    for node in root.findall("./note_data/note/sub_note_data/sub_note/end_timing_msec"):
        max_end = max(max_end, int(node.text or "0"))
    return max_end


def rebuild_beat_data(root: ET.Element, bpm: float) -> tuple[int, int]:
    header = required_child(root, "header")
    finish = int(required_child(header, "music_finish_time_msec").text or "0")
    beat_data = required_child(root, "beat_data")
    old_count = len(beat_data.findall("beat"))

    interval = 60000.0 / bpm
    timings: list[int] = []
    index = 0
    while True:
        timing = int(round(index * interval))
        if timing > finish:
            break
        if not timings or timing > timings[-1]:
            timings.append(timing)
        index += 1
    if not timings or timings[0] != 0:
        timings.insert(0, 0)
    if timings[-1] != finish:
        timings.append(finish)

    beat_data[:] = []
    for index, timing in enumerate(timings):
        beat = ET.Element("beat")
        beat.extend([child_text("index", index), child_text("start_timing_msec", timing)])
        beat_data.append(beat)
    return old_count, len(timings)


def patch_xml(
    root: ET.Element,
    bpm: float,
    finish_tail_msec: int | None,
    keep_beat_data: bool,
) -> dict[str, int]:
    bpm_value = int(round(bpm * 100000))

    header = required_child(root, "header")
    finish_node = required_child(header, "music_finish_time_msec")
    old_finish = int(finish_node.text or "0")
    new_finish = old_finish
    if finish_tail_msec is not None:
        new_finish = chart_max_end(root) + finish_tail_msec
        finish_node.text = str(new_finish)

    first_bpm = required_child(header, "first_bpm")
    old_first_bpm = int(first_bpm.text or "0")
    first_bpm.text = str(bpm_value)

    bpm_events = 0
    for event in root.findall("./event_data/event"):
        event_type = required_child(event, "type").text
        if event_type == "0":
            required_child(event, "value").text = str(bpm_value)
            bpm_events += 1
    if bpm_events == 0:
        raise BpmPackageError("event_data has no BPM event type 0")

    beat_data = required_child(root, "beat_data")
    old_beats = len(beat_data.findall("beat"))
    if keep_beat_data:
        new_beats = old_beats
    else:
        old_beats, new_beats = rebuild_beat_data(root, bpm)
    return {
        "old_first_bpm_sum": old_first_bpm,
        "new_first_bpm_sum": bpm_value,
        "old_finish_sum": old_finish,
        "new_finish_sum": new_finish,
        "bpm_events": bpm_events,
        "old_beats": old_beats,
        "new_beats": new_beats,
    }


def patch_package(
    package_root: Path,
    mod_name: str,
    bpm: float,
    finish_tail_msec: int | None,
    keep_beat_data: bool,
) -> dict[str, int]:
    totals = {
        "files_changed": 0,
        "old_first_bpm_sum": 0,
        "new_first_bpm_sum": 0,
        "old_finish_sum": 0,
        "new_finish_sum": 0,
        "bpm_events": 0,
        "old_beats": 0,
        "new_beats": 0,
    }
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        stats = patch_xml(root, bpm, finish_tail_msec, keep_beat_data)
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


def write_install(
    package_root: Path,
    mod_name: str,
    bpm: float,
    finish_tail_msec: int | None,
    keep_beat_data: bool,
) -> None:
    finish_line = (
        f"- `header/music_finish_time_msec` set to last note/sub_note end plus {finish_tail_msec}ms\n"
        if finish_tail_msec is not None
        else ""
    )
    beat_line = "- `beat_data` unchanged" if keep_beat_data else "- `beat_data`"
    text = f"""# Closeup BPM Test Package

Variant: pure XML piano playback with BPM metadata set to {bpm:g}.

Changed:

- `header/first_bpm`
{finish_line}- `event_data/event[type=0]/value`
{beat_line}

Unchanged:

- `note_data`
- nested `sub_note_data`
- non-BPM `event_data`
- `track_info`
- `velocity_zone_data`
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
    bpm: float,
    finish_tail_msec: int | None,
    keep_beat_data: bool,
) -> dict[str, str | int | float]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise BpmPackageError(f"output root must be inside work/: {output_root}") from exc

    package_suffix = f"lf_closeup_bpm_{str(bpm).replace('.', '_')}"
    if finish_tail_msec is not None:
        package_suffix += f"_finish_tail{finish_tail_msec}"
    if keep_beat_data:
        package_suffix += "_keepbeats"
    package = output_root / package_suffix
    copy_base_package(base_package, package, source_mod, target_mod)
    stats = patch_package(package, target_mod, bpm, finish_tail_msec, keep_beat_data)
    write_install(package, target_mod, bpm, finish_tail_msec, keep_beat_data)
    return {
        "package": str(package.relative_to(PROJECT_ROOT)),
        "mod_name": target_mod,
        "bpm": bpm,
        **stats,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup BPM test package.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_iso_notimesig"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    parser.add_argument("--source-mod", default="clfn_notimesig")
    parser.add_argument("--target-mod", default="clfn_bpm71")
    parser.add_argument("--bpm", type=float, default=71.0)
    parser.add_argument("--finish-tail-msec", type=int)
    parser.add_argument("--keep-beat-data", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_package(
            args.base_package,
            args.output_root,
            args.source_mod,
            args.target_mod,
            args.bpm,
            args.finish_tail_msec,
            args.keep_beat_data,
        )
    except (OSError, ET.ParseError, BpmPackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"package={result['package']} mod_name={result['mod_name']} "
        f"bpm={result['bpm']} files_changed={result['files_changed']} "
        f"old_first_bpm_sum={result['old_first_bpm_sum']} "
        f"new_first_bpm_sum={result['new_first_bpm_sum']} "
        f"old_finish_sum={result['old_finish_sum']} "
        f"new_finish_sum={result['new_finish_sum']} "
        f"bpm_events={result['bpm_events']} old_beats={result['old_beats']} "
        f"new_beats={result['new_beats']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
