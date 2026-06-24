#!/usr/bin/env python3
"""Create a closeup package that mutes most sub_notes by note order."""

from __future__ import annotations

import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class SparsePackageError(ValueError):
    """Raised when sparse package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise SparsePackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def copy_base_package(base_package: Path, destination: Path, source_mod: str, target_mod: str) -> None:
    source = base_package / "data_mods" / source_mod
    target = destination / "data_mods" / target_mod
    if not source.is_dir():
        raise SparsePackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise SparsePackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)


def patch_xml(root: ET.Element, keep_every: int) -> dict[str, int]:
    if keep_every <= 0:
        raise SparsePackageError("keep_every must be positive")
    kept = 0
    muted = 0
    notes = root.findall("./note_data/note")
    for note_pos, note in enumerate(notes):
        audible = note_pos % keep_every == 0
        for velocity in note.findall("./sub_note_data/sub_note/velocity"):
            if audible:
                kept += 1
            else:
                if velocity.text != "0":
                    muted += 1
                velocity.text = "0"
    return {"notes_seen": len(notes), "sub_notes_kept": kept, "sub_notes_muted": muted}


def patch_package(package_root: Path, mod_name: str, keep_every: int) -> dict[str, int]:
    totals = {"files_changed": 0, "notes_seen": 0, "sub_notes_kept": 0, "sub_notes_muted": 0}
    for xml_path in sorted(song_dir(package_root, mod_name).glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        stats = patch_xml(root, keep_every)
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


def write_install(package_root: Path, mod_name: str, keep_every: int) -> None:
    text = f"""# Closeup Sparse Subnote Test Package

Variant: keep only one audible sub_note for every {keep_every} visible notes; all other sub_notes have `velocity=0`.

Changed:

- nested `sub_note/velocity`

Unchanged:

- visible `note_data`
- `sub_note` timing, scale, track_index
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
    keep_every: int,
) -> dict[str, str | int]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise SparsePackageError(f"output root must be inside work/: {output_root}") from exc

    package = output_root / f"lf_closeup_sparse_subnote_keep1of{keep_every}"
    copy_base_package(base_package, package, source_mod, target_mod)
    stats = patch_package(package, target_mod, keep_every)
    write_install(package, target_mod, keep_every)
    return {
        "package": str(package.relative_to(PROJECT_ROOT)),
        "mod_name": target_mod,
        "keep_every": keep_every,
        **stats,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup sparse sub_note test package.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_iso_notimesig"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    parser.add_argument("--source-mod", default="clfn_notimesig")
    parser.add_argument("--target-mod", default="clfn_sparse8")
    parser.add_argument("--keep-every", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_package(
            args.base_package,
            args.output_root,
            args.source_mod,
            args.target_mod,
            args.keep_every,
        )
    except (OSError, ET.ParseError, SparsePackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"package={result['package']} mod_name={result['mod_name']} "
        f"keep_every={result['keep_every']} files_changed={result['files_changed']} "
        f"notes_seen={result['notes_seen']} sub_notes_kept={result['sub_notes_kept']} "
        f"sub_notes_muted={result['sub_notes_muted']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
