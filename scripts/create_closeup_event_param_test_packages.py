#!/usr/bin/env python3
"""Create closeup packages that isolate event_data value changes."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


BASE_VALUES = {
    1: 120,
    2: 11,
    3: 20,
    4: 61,
    5: 16,
    6: 117,
    7: 0,
    8: 100,
}

C0047_VALUES = {
    1: 122,
    2: 9,
    3: 30,
    4: 50,
    5: 15,
    6: 127,
    7: 0,
    8: 65,
}


class EventParamPackageError(ValueError):
    """Raised when event parameter package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise EventParamPackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def copy_base_package(base_package: Path, destination: Path, mod_name: str) -> None:
    source = base_package / "data_mods" / "clfn_scale12"
    target = destination / "data_mods" / mod_name
    if not source.is_dir():
        raise EventParamPackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise EventParamPackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def patch_events(package_root: Path, mod_name: str, event_types: set[int]) -> dict[str, int]:
    files_changed = 0
    values_changed = 0
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        for event in root.findall("./event_data/event"):
            event_type = int(required_text(event, "type"))
            if event_type not in event_types:
                continue
            value = event.find("value")
            if value is None:
                raise EventParamPackageError("missing event value")
            new_value = str(C0047_VALUES[event_type])
            if value.text != new_value:
                values_changed += 1
            value.text = new_value
        write_xml(root, xml_path)
        files_changed += 1
    return {"files_changed": files_changed, "values_changed": values_changed}


def required_text(parent: ET.Element, tag: str) -> str:
    child = parent.find(tag)
    if child is None or child.text is None:
        raise EventParamPackageError(f"missing field: {tag}")
    return child.text


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


def write_install(package_root: Path, mod_name: str, event_types: set[int]) -> None:
    changes = ", ".join(
        f"type {event_type}: {BASE_VALUES[event_type]} -> {C0047_VALUES[event_type]}"
        for event_type in sorted(event_types)
    )
    text = f"""# Closeup Event Parameter Test Package

Variant: {changes}

Only `event_data/event/value` is changed. Event timing, notes, `sub_note_data`, and banks are unchanged.

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
    event_types: set[int],
) -> dict[str, str | int]:
    package = output_root / package_name
    copy_base_package(base_package, package, mod_name)
    stats = patch_events(package, mod_name, event_types)
    write_install(package, mod_name, event_types)
    return {"package": str(package.relative_to(PROJECT_ROOT)), "mod_name": mod_name, **stats}


def create_packages(base_package: Path, output_root: Path) -> list[dict[str, str | int]]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise EventParamPackageError(f"output root must be inside work/: {output_root}") from exc

    variants = [
        ("lf_closeup_event_t12", "clfn_evt12", {1, 2}),
        ("lf_closeup_event_t345", "clfn_evt345", {3, 4, 5}),
        ("lf_closeup_event_t68", "clfn_evt68", {6, 8}),
        ("lf_closeup_event_t1", "clfn_evt1", {1}),
        ("lf_closeup_event_t2", "clfn_evt2", {2}),
        ("lf_closeup_event_t3", "clfn_evt3", {3}),
        ("lf_closeup_event_t4", "clfn_evt4", {4}),
        ("lf_closeup_event_t5", "clfn_evt5", {5}),
        ("lf_closeup_event_t6", "clfn_evt6", {6}),
        ("lf_closeup_event_t8", "clfn_evt8", {8}),
    ]
    return [create_one(base_package, output_root, *variant) for variant in variants]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup event parameter test packages.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_ab_scale_plus12"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        results = create_packages(args.base_package, args.output_root)
    except (OSError, ET.ParseError, EventParamPackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    for result in results:
        print(
            "OK: "
            f"package={result['package']} mod_name={result['mod_name']} "
            f"files_changed={result['files_changed']} values_changed={result['values_changed']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
