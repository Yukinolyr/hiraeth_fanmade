#!/usr/bin/env python3
"""Create closeup packages that mute abnormal long same-pitch sub_note runs."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class LongRunPackageError(ValueError):
    """Raised when long-run package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise LongRunPackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def copy_base_package(base_package: Path, destination: Path, mod_name: str) -> None:
    source = base_package / "data_mods" / "clfn_scale12"
    target = destination / "data_mods" / mod_name
    if not source.is_dir():
        raise LongRunPackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise LongRunPackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def required_text(parent: ET.Element, tag: str) -> str:
    child = parent.find(tag)
    if child is None or child.text is None:
        raise LongRunPackageError(f"missing field: {tag}")
    return child.text


def set_velocity(sub_note: ET.Element, value: int) -> None:
    velocity = sub_note.find("velocity")
    if velocity is None:
        raise LongRunPackageError("missing sub_note velocity")
    velocity.text = str(value)


def find_runs(rows: list[tuple[int, ET.Element]], gap_msec: int) -> list[list[tuple[int, ET.Element]]]:
    if not rows:
        return []
    rows = sorted(rows, key=lambda row: row[0])
    runs = []
    current = [rows[0]]
    for row in rows[1:]:
        if row[0] - current[-1][0] <= gap_msec:
            current.append(row)
        else:
            runs.append(current)
            current = [row]
    runs.append(current)
    return runs


def patch_xml(root: ET.Element, gap_msec: int, min_run_len: int, keep_every: int) -> dict[str, int]:
    by_key: dict[tuple[int, int], list[tuple[int, ET.Element]]] = defaultdict(list)
    total = 0
    for sub_note in root.findall("./note_data/note/sub_note_data/sub_note"):
        start = int(required_text(sub_note, "start_timing_msec"))
        track = int(required_text(sub_note, "track_index"))
        scale = int(required_text(sub_note, "scale_piano"))
        by_key[(track, scale)].append((start, sub_note))
        total += 1

    muted = 0
    long_runs = 0
    longest_run = 0
    for rows in by_key.values():
        for run in find_runs(rows, gap_msec):
            longest_run = max(longest_run, len(run))
            if len(run) < min_run_len:
                continue
            long_runs += 1
            for offset, (_start, sub_note) in enumerate(run):
                if offset % keep_every == 0:
                    continue
                set_velocity(sub_note, 0)
                muted += 1

    return {
        "sub_notes_seen": total,
        "long_runs_seen": long_runs,
        "longest_run": longest_run,
        "sub_notes_muted": muted,
    }


def patch_package(package_root: Path, mod_name: str, gap_msec: int, min_run_len: int, keep_every: int) -> dict[str, int]:
    totals = {
        "files_changed": 0,
        "sub_notes_seen": 0,
        "long_runs_seen": 0,
        "longest_run": 0,
        "sub_notes_muted": 0,
    }
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        stats = patch_xml(root, gap_msec, min_run_len, keep_every)
        for key, value in stats.items():
            if key == "longest_run":
                totals[key] = max(totals[key], value)
            else:
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


def write_install(package_root: Path, mod_name: str, gap_msec: int, min_run_len: int, keep_every: int) -> None:
    text = f"""# Closeup Long Same-Pitch Run Test Package

Variant: mute abnormal long same-pitch sub_note runs.

Rules:

- group by `track_index + scale_piano`
- a run continues while adjacent starts are <= {gap_msec}ms apart
- only runs with length >= {min_run_len} are modified
- keep every {keep_every}th sub_note audible
- muted sub_notes remain present with `velocity=0`

Unchanged:

- outer `note_data`
- timings
- scales
- track_index
- banks

Copy this folder into the test game's `contents/data_mods`:

```text
{package_root.relative_to(PROJECT_ROOT)}/data_mods/{mod_name}
```
"""
    (package_root / "INSTALL.md").write_text(text, encoding="utf-8", newline="\n")


def create_package(
    base_package: Path,
    output_root: Path,
    gap_msec: int,
    min_run_len: int,
    keep_every: int,
) -> dict[str, str | int]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise LongRunPackageError(f"output root must be inside work/: {output_root}") from exc

    package = output_root / f"lf_closeup_longrun_g{gap_msec}_n{min_run_len}_k{keep_every}"
    mod_name = f"clfn_run{min_run_len}k{keep_every}"
    copy_base_package(base_package, package, mod_name)
    stats = patch_package(package, mod_name, gap_msec, min_run_len, keep_every)
    write_install(package, mod_name, gap_msec, min_run_len, keep_every)
    return {
        "package": str(package.relative_to(PROJECT_ROOT)),
        "mod_name": mod_name,
        "gap_msec": gap_msec,
        "min_run_len": min_run_len,
        "keep_every": keep_every,
        **stats,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup long same-pitch run test package.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_ab_scale_plus12"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    parser.add_argument("--gap-msec", type=int, default=200)
    parser.add_argument("--min-run-len", type=int, default=8)
    parser.add_argument("--keep-every", type=int, default=4)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_package(
            args.base_package,
            args.output_root,
            args.gap_msec,
            args.min_run_len,
            args.keep_every,
        )
    except (OSError, ET.ParseError, LongRunPackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"package={result['package']} mod_name={result['mod_name']} "
        f"gap_msec={result['gap_msec']} min_run_len={result['min_run_len']} "
        f"keep_every={result['keep_every']} files_changed={result['files_changed']} "
        f"sub_notes_seen={result['sub_notes_seen']} long_runs_seen={result['long_runs_seen']} "
        f"longest_run={result['longest_run']} sub_notes_muted={result['sub_notes_muted']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
