#!/usr/bin/env python3
"""Copy a work song folder and rename files to a new basename."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAFE_BASENAME = re.compile(r"^[A-Za-z0-9_]+$")


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError(f"Path must stay inside project root: {path}") from exc
    return resolved


def infer_old_basename(source: Path) -> str:
    xml_basenames: list[str] = []
    for file_path in source.glob("*.xml"):
        for suffix in ("_00normal", "_01hard", "_02extreme", "_03real"):
            if file_path.stem.endswith(suffix):
                xml_basenames.append(file_path.stem[: -len(suffix)])
                break

    if xml_basenames:
        return max(set(xml_basenames), key=xml_basenames.count)

    for file_path in source.glob("*.xwb"):
        if file_path.stem.endswith("_pre"):
            continue
        return file_path.stem

    raise ValueError(f"Could not infer source basename: {source}")


def renamed_filename(name: str, old_basename: str, new_basename: str) -> str:
    if name == f"{old_basename}.xwb":
        return f"{new_basename}.xwb"
    if name == f"{old_basename}.xsb":
        return f"{new_basename}.xsb"
    if name == f"{old_basename}_pre.xwb":
        return f"{new_basename}_pre.xwb"
    if name == f"{old_basename}_pre.xsb":
        return f"{new_basename}_pre.xsb"
    for suffix in ("_00normal.xml", "_01hard.xml", "_02extreme.xml", "_03real.xml"):
        if name == f"{old_basename}{suffix}":
            return f"{new_basename}{suffix}"
    return name


def create_renamed_copy(source: Path, destination: Path, new_basename: str) -> tuple[str, list[str]]:
    if not SAFE_BASENAME.fullmatch(new_basename):
        raise ValueError("New basename may only contain ASCII letters, digits, and underscores.")

    source = resolve_inside_project(source)
    destination = resolve_inside_project(destination)
    work_root = PROJECT_ROOT / "work"

    if not source.exists() or not source.is_dir():
        raise ValueError(f"Source folder not found: {source}")
    if destination.exists():
        raise ValueError(f"Destination already exists: {destination}")
    try:
        destination.relative_to(work_root)
    except ValueError as exc:
        raise ValueError(f"Destination must be inside work/: {destination}") from exc

    old_basename = infer_old_basename(source)
    destination.mkdir(parents=True)
    copied: list[str] = []

    for source_file in sorted(source.iterdir()):
        if not source_file.is_file():
            continue
        target_name = renamed_filename(source_file.name, old_basename, new_basename)
        target_file = destination / target_name
        shutil.copy2(source_file, target_file)
        copied.append(target_name)

    return old_basename, copied


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a renamed song copy under work/.")
    parser.add_argument("source", type=Path, help="Existing work song folder.")
    parser.add_argument("destination", type=Path, help="Destination folder under work/.")
    parser.add_argument("new_basename", help="New song basename, for example m_f0001_custom_test.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        old_basename, copied = create_renamed_copy(args.source, args.destination, args.new_basename)
    except ValueError as exc:
        print(f"error: {exc}")
        return 1

    print(f"old_basename: {old_basename}")
    print(f"new_basename: {args.new_basename}")
    print(f"created: {args.destination}")
    print("files:")
    for name in copied:
        print(f"- {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
