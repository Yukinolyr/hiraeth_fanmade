#!/usr/bin/env python3
"""Create a closeup package with XML structure closer to m_c0047."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class StructurePackageError(ValueError):
    """Raised when structure package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise StructurePackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def copy_base_package(base_package: Path, destination: Path, source_mod: str, target_mod: str) -> None:
    source = base_package / "data_mods" / source_mod
    target = destination / "data_mods" / target_mod
    if not source.is_dir():
        raise StructurePackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise StructurePackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def elem_text(parent: ET.Element, tag: str) -> str:
    child = parent.find(tag)
    if child is None or child.text is None:
        raise StructurePackageError(f"missing field: {tag}")
    return child.text


def child_text(parent: ET.Element, tag: str, value: str | int) -> ET.Element:
    child = ET.Element(tag)
    child.text = str(value)
    return child


def make_event(index: int, start: int, event_type: int, value: int) -> ET.Element:
    event = ET.Element("event")
    event.extend(
        [
            child_text(event, "index", index),
            child_text(event, "start_timing_msec", start),
            child_text(event, "type", event_type),
            child_text(event, "value", value),
        ]
    )
    return event


def replace_event_data(root: ET.Element) -> int:
    header = root.find("header")
    if header is None:
        raise StructurePackageError("missing header")
    bpm_value = int(elem_text(header, "first_bpm"))

    old_event_data = root.find("event_data")
    if old_event_data is None:
        raise StructurePackageError("missing event_data")

    new_event_data = ET.Element("event_data")
    event_specs = [
        (0, 0, 0, bpm_value),
        (1, 0, 1, 122),
        (2, 0, 2, 9),
        (3, 473, 3, 30),
        (4, 473, 4, 50),
        (5, 473, 5, 15),
        (6, 949, 6, 127),
        (7, 949, 7, 0),
        (8, 949, 8, 65),
    ]
    for spec in event_specs:
        new_event_data.append(make_event(*spec))

    root.insert(list(root).index(old_event_data), new_event_data)
    root.remove(old_event_data)
    return len(event_specs)


def patch_track_info(root: ET.Element) -> bool:
    track_info = root.find("track_info")
    if track_info is None:
        raise StructurePackageError("missing track_info")
    if any(track.findtext("index") == "3" for track in track_info.findall("track")):
        return False
    track = ET.Element("track")
    track.extend([child_text(track, "index", 3), child_text(track, "name", "key_apiano1")])
    track_info.append(track)
    return True


def remove_time_signature_fields(root: ET.Element) -> int:
    header = root.find("header")
    if header is None:
        raise StructurePackageError("missing header")
    removed = 0
    for tag in ("time_signature_numerator", "time_signature_denominator", "time_signature"):
        child = header.find(tag)
        if child is not None:
            header.remove(child)
            removed += 1
    return removed


def patch_xml_files(package_root: Path, mod_name: str) -> dict[str, int]:
    files_changed = 0
    events_written = 0
    tracks_added = 0
    header_fields_removed = 0
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        events_written += replace_event_data(root)
        if patch_track_info(root):
            tracks_added += 1
        header_fields_removed += remove_time_signature_fields(root)
        write_xml(root, xml_path)
        files_changed += 1
    return {
        "files_changed": files_changed,
        "events_written": events_written,
        "tracks_added": tracks_added,
        "header_fields_removed": header_fields_removed,
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


def write_install(package_root: Path, mod_name: str) -> None:
    text = f"""# Closeup m_c0047 Structure Test Package

Variant: scale+12 baseline with XML structure adjusted toward m_c0047.

Changed XML fields:

- `event_data`: m_c0047 initial event values, keeping Closeup BPM.
- `track_info`: add unused `index=3 key_apiano1`.
- `header`: remove `time_signature*` fields.

Unchanged:

- note timings
- note count
- sub_note timings
- scale_piano values
- xsb/xwb files

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


def create_package(base_package: Path, output_root: Path) -> dict[str, str | int]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise StructurePackageError(f"output root must be inside work/: {output_root}") from exc

    package = output_root / "lf_closeup_c0047_structure"
    mod_name = "clfn_c0047struct"
    copy_base_package(base_package, package, "clfn_scale12", mod_name)
    stats = patch_xml_files(package, mod_name)
    write_install(package, mod_name)
    return {"package": str(package.relative_to(PROJECT_ROOT)), "mod_name": mod_name, **stats}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup m_c0047 structure test package.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_ab_scale_plus12"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_package(args.base_package, args.output_root)
    except (OSError, ET.ParseError, StructurePackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"package={result['package']} mod_name={result['mod_name']} "
        f"files_changed={result['files_changed']} events_written={result['events_written']} "
        f"tracks_added={result['tracks_added']} "
        f"header_fields_removed={result['header_fields_removed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
