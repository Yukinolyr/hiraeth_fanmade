#!/usr/bin/env python3
"""Create a closeup package using a different pure-piano backtrack bank template."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"


class BankTemplatePackageError(ValueError):
    """Raised when bank template package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise BankTemplatePackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def create_package(base_package: Path, output_root: Path, template_dir: Path) -> dict[str, str | int]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    template_dir = resolve_inside_project(template_dir)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise BankTemplatePackageError(f"output root must be inside work/: {output_root}") from exc

    source_mod = base_package / "data_mods" / "clfn_scale12"
    package = output_root / "lf_closeup_bank_m_c0064"
    mod_name = "clfn_bank64"
    target_mod = package / "data_mods" / mod_name
    target_song = target_mod / "data_Op3" / "sound" / "music" / SONG_BASENAME

    if not source_mod.is_dir():
        raise BankTemplatePackageError(f"source mod folder not found: {source_mod}")
    if package.exists():
        raise BankTemplatePackageError(f"destination already exists: {package}")

    target_mod.parent.mkdir(parents=True)
    shutil.copytree(source_mod, target_mod)

    replacements = [
        (template_dir / "m_c0064_hungary06.xsb", target_song / f"{SONG_BASENAME}.xsb"),
        (template_dir / "m_c0064_hungary06.xwb", target_song / f"{SONG_BASENAME}.xwb"),
    ]
    bytes_written = 0
    for src, dst in replacements:
        if not src.is_file():
            raise BankTemplatePackageError(f"template file not found: {src}")
        shutil.copy2(src, dst)
        bytes_written += dst.stat().st_size

    write_install(package, mod_name)
    return {
        "package": str(package.relative_to(PROJECT_ROOT)),
        "mod_name": mod_name,
        "files_replaced": len(replacements),
        "bytes_written": bytes_written,
    }


def write_install(package: Path, mod_name: str) -> None:
    text = f"""# Closeup Bank Template Test Package

Variant: replace only the main `_backtrack` bank files with `m_c0064_hungary06` templates.

Changed:

- `{SONG_BASENAME}.xsb`
- `{SONG_BASENAME}.xwb`

Unchanged:

- XML
- pre bank
- sub_note_data
- music_list

Copy this folder into the test game's `contents/data_mods`:

```text
{package.relative_to(PROJECT_ROOT)}/data_mods/{mod_name}
```
"""
    (package / "INSTALL.md").write_text(text, encoding="utf-8", newline="\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup bank template test package.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_ab_scale_plus12"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    parser.add_argument("--template-dir", type=Path, default=Path("reference/m_c0064_hungary06"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_package(args.base_package, args.output_root, args.template_dir)
    except (OSError, BankTemplatePackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"package={result['package']} mod_name={result['mod_name']} "
        f"files_replaced={result['files_replaced']} bytes_written={result['bytes_written']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
