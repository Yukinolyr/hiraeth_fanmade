#!/usr/bin/env python3
"""Assemble a custom song work folder from prepared parts."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIFFICULTY_SUFFIXES = ["00normal", "01hard", "02extreme", "03real"]
SAFE_BASENAME = re.compile(r"^m_[A-Za-z0-9_]+$")


class AssembleError(ValueError):
    """Raised when a custom song folder cannot be assembled safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise AssembleError(f"Path must stay inside project root: {path}") from exc
    return resolved


def infer_template_basename(template_dir: Path) -> str:
    for suffix in DIFFICULTY_SUFFIXES:
        for path in sorted(template_dir.glob(f"*_{suffix}.xml")):
            return path.name[: -len(f"_{suffix}.xml")]
    raise AssembleError(f"Could not infer template basename from XML files: {template_dir}")


def copy_required_file(source: Path, destination: Path) -> None:
    if not source.exists() or not source.is_file():
        raise AssembleError(f"Required source file not found: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def assemble_custom_song(
    destination: Path,
    basename: str,
    template_dir: Path,
    main_xwb: Path,
    main_xsb: Path,
    preview_xwb: Path | None,
    preview_xsb: Path | None,
    music_list: Path | None,
) -> list[str]:
    if not SAFE_BASENAME.fullmatch(basename):
        raise AssembleError("Basename must start with m_ and contain only ASCII letters, digits, underscores.")

    destination = resolve_inside_project(destination)
    template_dir = resolve_inside_project(template_dir)
    main_xwb = resolve_inside_project(main_xwb)
    main_xsb = resolve_inside_project(main_xsb)
    preview_xwb = resolve_inside_project(preview_xwb) if preview_xwb is not None else None
    preview_xsb = resolve_inside_project(preview_xsb) if preview_xsb is not None else None
    music_list = resolve_inside_project(music_list) if music_list is not None else None

    work_root = PROJECT_ROOT / "work"
    try:
        destination.relative_to(work_root)
    except ValueError as exc:
        raise AssembleError(f"Destination must be inside work/: {destination}") from exc
    if destination.exists():
        raise AssembleError(f"Destination already exists: {destination}")
    if not template_dir.exists() or not template_dir.is_dir():
        raise AssembleError(f"Template song folder not found: {template_dir}")

    template_basename = infer_template_basename(template_dir)
    copied: list[str] = []
    destination.mkdir(parents=True)

    for suffix in DIFFICULTY_SUFFIXES:
        source = template_dir / f"{template_basename}_{suffix}.xml"
        target = destination / f"{basename}_{suffix}.xml"
        copy_required_file(source, target)
        copied.append(target.name)

    bank_pairs = [
        (main_xwb, destination / f"{basename}.xwb"),
        (main_xsb, destination / f"{basename}.xsb"),
    ]
    if preview_xwb is not None:
        bank_pairs.append((preview_xwb, destination / f"{basename}_pre.xwb"))
    if preview_xsb is not None:
        bank_pairs.append((preview_xsb, destination / f"{basename}_pre.xsb"))

    for source, target in bank_pairs:
        copy_required_file(source, target)
        copied.append(target.name)

    if music_list is not None:
        target = destination / "music_list.xml"
        copy_required_file(music_list, target)
        copied.append(target.name)

    return copied


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assemble a custom song work folder.")
    parser.add_argument("destination", type=Path, help="Destination folder under work/.")
    parser.add_argument("--basename", required=True, help="Lowercase song basename, e.g. m_f0002_closeup_test.")
    parser.add_argument("--template-dir", required=True, type=Path, help="Template song folder for XML charts.")
    parser.add_argument("--main-xwb", required=True, type=Path, help="Prepared main .xwb.")
    parser.add_argument("--main-xsb", required=True, type=Path, help="Prepared main .xsb.")
    parser.add_argument("--preview-xwb", type=Path, help="Prepared preview .xwb.")
    parser.add_argument("--preview-xsb", type=Path, help="Prepared preview .xsb.")
    parser.add_argument("--music-list", type=Path, help="Prepared music_list.xml copy.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        copied = assemble_custom_song(
            args.destination,
            args.basename,
            args.template_dir,
            args.main_xwb,
            args.main_xsb,
            args.preview_xwb,
            args.preview_xsb,
            args.music_list,
        )
    except (OSError, AssembleError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(f"OK: created {args.destination}")
    print("files:")
    for name in copied:
        print(f"- {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
