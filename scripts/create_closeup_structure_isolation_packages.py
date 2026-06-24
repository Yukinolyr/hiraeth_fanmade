#!/usr/bin/env python3
"""Create single-variable closeup XML structure isolation packages."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class IsolationPackageError(ValueError):
    """Raised when isolation package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise IsolationPackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def copy_base_package(base_package: Path, destination: Path, target_mod: str) -> None:
    source = base_package / "data_mods" / "clfn_scale12"
    target = destination / "data_mods" / target_mod
    if not source.is_dir():
        raise IsolationPackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise IsolationPackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def child_text(tag: str, value: str | int) -> ET.Element:
    child = ET.Element(tag)
    child.text = str(value)
    return child


def require_text(parent: ET.Element, tag: str) -> str:
    child = parent.find(tag)
    if child is None or child.text is None:
        raise IsolationPackageError(f"missing field: {tag}")
    return child.text


def make_event(index: int, start: int, event_type: int, value: int) -> ET.Element:
    event = ET.Element("event")
    event.extend(
        [
            child_text("index", index),
            child_text("start_timing_msec", start),
            child_text("type", event_type),
            child_text("value", value),
        ]
    )
    return event


def replace_event_data(root: ET.Element, event_specs: list[tuple[int, int, int, int]]) -> int:
    old_event_data = root.find("event_data")
    if old_event_data is None:
        raise IsolationPackageError("missing event_data")
    new_event_data = ET.Element("event_data")
    for spec in event_specs:
        new_event_data.append(make_event(*spec))
    root.insert(list(root).index(old_event_data), new_event_data)
    root.remove(old_event_data)
    return len(event_specs)


def patch_event_values_safe_times(root: ET.Element) -> int:
    header = root.find("header")
    if header is None:
        raise IsolationPackageError("missing header")
    bpm = int(require_text(header, "first_bpm"))
    return replace_event_data(
        root,
        [
            (0, 0, 0, bpm),
            (1, 0, 1, 122),
            (2, 0, 2, 9),
            (3, 80, 3, 30),
            (4, 80, 4, 50),
            (5, 80, 5, 15),
            (6, 161, 6, 127),
            (7, 161, 7, 0),
            (8, 161, 8, 65),
        ],
    )


def patch_event_exact_times(root: ET.Element) -> int:
    header = root.find("header")
    if header is None:
        raise IsolationPackageError("missing header")
    bpm = int(require_text(header, "first_bpm"))
    return replace_event_data(
        root,
        [
            (0, 0, 0, bpm),
            (1, 0, 1, 122),
            (2, 0, 2, 9),
            (3, 473, 3, 30),
            (4, 473, 4, 50),
            (5, 473, 5, 15),
            (6, 949, 6, 127),
            (7, 949, 7, 0),
            (8, 949, 8, 65),
        ],
    )


def patch_track3(root: ET.Element) -> int:
    track_info = root.find("track_info")
    if track_info is None:
        raise IsolationPackageError("missing track_info")
    if any(track.findtext("index") == "3" for track in track_info.findall("track")):
        return 0
    track = ET.Element("track")
    track.extend([child_text("index", 3), child_text("name", "key_apiano1")])
    track_info.append(track)
    return 1


def patch_no_timesig(root: ET.Element) -> int:
    header = root.find("header")
    if header is None:
        raise IsolationPackageError("missing header")
    removed = 0
    for tag in ("time_signature_numerator", "time_signature_denominator", "time_signature"):
        child = header.find(tag)
        if child is not None:
            header.remove(child)
            removed += 1
    return removed


def patch_package(package_root: Path, mod_name: str, patcher: Callable[[ET.Element], int]) -> dict[str, int]:
    files_changed = 0
    fields_changed = 0
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        fields_changed += patcher(root)
        write_xml(root, xml_path)
        files_changed += 1
    return {"files_changed": files_changed, "fields_changed": fields_changed}


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
    text = f"""# Closeup Structure Isolation Package

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


def create_one(
    base_package: Path,
    output_root: Path,
    package_name: str,
    mod_name: str,
    description: str,
    patcher: Callable[[ET.Element], int],
) -> dict[str, str | int]:
    package = output_root / package_name
    copy_base_package(base_package, package, mod_name)
    stats = patch_package(package, mod_name, patcher)
    write_install(package, mod_name, description)
    return {"package": str(package.relative_to(PROJECT_ROOT)), "mod_name": mod_name, **stats}


def create_packages(base_package: Path, output_root: Path) -> list[dict[str, str | int]]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise IsolationPackageError(f"output root must be inside work/: {output_root}") from exc

    variants = [
        (
            "lf_closeup_iso_eventval",
            "clfn_eventval",
            "scale+12 baseline, only c0047 event values with original safe event times",
            patch_event_values_safe_times,
        ),
        (
            "lf_closeup_iso_eventexact",
            "clfn_eventexact",
            "scale+12 baseline, only c0047 event values and c0047 event times",
            patch_event_exact_times,
        ),
        (
            "lf_closeup_iso_track3",
            "clfn_track3",
            "scale+12 baseline, only add unused track_info index=3",
            patch_track3,
        ),
        (
            "lf_closeup_iso_notimesig",
            "clfn_notimesig",
            "scale+12 baseline, only remove time_signature header fields",
            patch_no_timesig,
        ),
    ]
    return [create_one(base_package, output_root, *variant) for variant in variants]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup single-variable structure test packages.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_ab_scale_plus12"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        results = create_packages(args.base_package, args.output_root)
    except (OSError, ET.ParseError, IsolationPackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    for result in results:
        print(
            "OK: "
            f"package={result['package']} mod_name={result['mod_name']} "
            f"files_changed={result['files_changed']} fields_changed={result['fields_changed']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
