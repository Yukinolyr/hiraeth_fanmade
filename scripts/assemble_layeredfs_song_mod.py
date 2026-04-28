#!/usr/bin/env python3
"""Assemble one song folder into a LayeredFS data_mods package."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAFE_MOD_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
SAFE_DATA_ROOT = re.compile(r"^(sound|data_op2|data_op3)$")


class LayeredFSError(ValueError):
    """Raised when a LayeredFS package cannot be assembled safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise LayeredFSError(f"Path must stay inside project root: {path}") from exc
    return resolved


def infer_song_basename(song_dir: Path) -> str:
    for path in sorted(song_dir.glob("*.xwb")):
        if path.name.endswith("_pre.xwb"):
            continue
        return path.stem
    raise LayeredFSError(f"Could not infer song basename from main .xwb: {song_dir}")


def is_song_file(path: Path, basename: str) -> bool:
    if path.suffix.lower() not in {".xsb", ".xwb", ".xml"}:
        return False
    return path.name == f"{basename}.xsb" or path.name == f"{basename}.xwb" or path.name.startswith(f"{basename}_")


def copy_song_files(source: Path, destination: Path, basename: str) -> list[str]:
    copied: list[str] = []
    destination.mkdir(parents=True, exist_ok=True)
    for source_file in sorted(path for path in source.iterdir() if path.is_file() and is_song_file(path, basename)):
        target = destination / source_file.name
        shutil.copy2(source_file, target)
        copied.append(str(target.relative_to(PROJECT_ROOT)))
    if not copied:
        raise LayeredFSError(f"No song files copied for basename {basename}: {source}")
    return copied


def assemble_layeredfs_song_mod(
    destination: Path,
    mod_name: str,
    data_root: str,
    song_dir: Path,
    music_list_merged: Path,
) -> list[str]:
    if not SAFE_MOD_NAME.fullmatch(mod_name):
        raise LayeredFSError("Mod name may contain only ASCII letters, digits, underscore, dash, and dot.")
    if not SAFE_DATA_ROOT.fullmatch(data_root):
        raise LayeredFSError("Data root must be one of: sound, data_op2, data_op3.")

    destination = resolve_inside_project(destination)
    song_dir = resolve_inside_project(song_dir)
    music_list_merged = resolve_inside_project(music_list_merged)

    work_root = PROJECT_ROOT / "work"
    try:
        destination.relative_to(work_root)
    except ValueError as exc:
        raise LayeredFSError(f"Destination must be inside work/: {destination}") from exc
    if destination.exists():
        raise LayeredFSError(f"Destination already exists: {destination}")
    if not song_dir.is_dir():
        raise LayeredFSError(f"Song directory not found: {song_dir}")
    if not music_list_merged.is_file():
        raise LayeredFSError(f"music_list.merged.xml not found: {music_list_merged}")

    basename = infer_song_basename(song_dir)
    sound_root = destination / "data_mods" / mod_name
    if data_root != "sound":
        sound_root = sound_root / data_root

    song_target = sound_root / "sound" / "music" / basename
    copied = copy_song_files(song_dir, song_target, basename)

    list_target = sound_root / "sound" / "music_list.merged.xml"
    list_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(music_list_merged, list_target)
    copied.append(str(list_target.relative_to(PROJECT_ROOT)))

    return copied


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assemble a LayeredFS data_mods package for one custom song.")
    parser.add_argument("destination", type=Path, help="Destination package directory under work/.")
    parser.add_argument("--mod-name", default="fanmade", help="LayeredFS mod folder name under data_mods/.")
    parser.add_argument(
        "--data-root",
        default="data_op3",
        choices=["sound", "data_op2", "data_op3"],
        help="Target data root. Use data_op3 for current Nostalgia Op.3 tests.",
    )
    parser.add_argument("--song-dir", required=True, type=Path, help="Prepared song directory to copy.")
    parser.add_argument(
        "--music-list-merged",
        required=True,
        type=Path,
        help="Prepared music_list.merged.xml to copy.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        copied = assemble_layeredfs_song_mod(
            args.destination,
            args.mod_name,
            args.data_root,
            args.song_dir,
            args.music_list_merged,
        )
    except (OSError, LayeredFSError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(f"OK: created {args.destination}")
    print("files:")
    for path in copied:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
