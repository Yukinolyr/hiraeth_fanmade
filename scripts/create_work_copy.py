#!/usr/bin/env python3
"""Create a safe working copy of a reference song folder."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError(f"Path must stay inside project root: {path}") from exc
    return resolved


def create_work_copy(source: Path, destination: Path) -> None:
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

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, copy_function=shutil.copy2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Copy a reference song folder into work/.")
    parser.add_argument("source", type=Path, help="Reference song folder to copy.")
    parser.add_argument("destination", type=Path, help="Destination folder under work/.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        create_work_copy(args.source, args.destination)
    except ValueError as exc:
        print(f"error: {exc}")
        return 1
    print(f"created: {args.destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
