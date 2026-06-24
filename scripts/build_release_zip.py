#!/usr/bin/env python3
"""Build the checked-in Fengbei v0.1 release package zip."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE_ROOT = (
    PROJECT_ROOT
    / "packages"
    / "fengbei_v0.1_test"
    / "hiraeth_fanmade_fengbei_v0.1_test"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "work" / "hiraeth_fanmade_fengbei_v0.1_test.zip"
ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)


class BuildReleaseError(ValueError):
    """Raised when the release zip cannot be built."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise BuildReleaseError(f"Path must stay inside project root: {path}") from exc
    return resolved


def add_directory(zip_file: zipfile.ZipFile, arcname: str) -> None:
    info = zipfile.ZipInfo(arcname.rstrip("/") + "/", ZIP_TIMESTAMP)
    info.external_attr = 0o755 << 16
    zip_file.writestr(info, b"")


def add_file(zip_file: zipfile.ZipFile, path: Path, arcname: str) -> None:
    info = zipfile.ZipInfo(arcname, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    zip_file.writestr(info, path.read_bytes())


def build_zip(package_root: Path, output: Path) -> list[str]:
    package_root = resolve_inside_project(package_root)
    output = resolve_inside_project(output)

    if not package_root.is_dir():
        raise BuildReleaseError(f"Package root not found: {package_root}")

    output.parent.mkdir(parents=True, exist_ok=True)
    root_name = package_root.name
    written = [root_name + "/"]

    with zipfile.ZipFile(output, "w") as zip_file:
        add_directory(zip_file, root_name)
        for path in sorted(package_root.rglob("*")):
            relative = path.relative_to(package_root)
            arcname = f"{root_name}/{relative.as_posix()}"
            if path.is_dir():
                add_directory(zip_file, arcname)
                written.append(arcname.rstrip("/") + "/")
            elif path.is_file():
                add_file(zip_file, path, arcname)
                written.append(arcname)

    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Fengbei v0.1 release zip.")
    parser.add_argument(
        "--package-root",
        type=Path,
        default=DEFAULT_PACKAGE_ROOT,
        help="Package root directory whose basename becomes the zip root.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output zip path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        written = build_zip(args.package_root, args.output)
    except (OSError, BuildReleaseError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(f"OK: wrote {args.output}")
    print(f"entries: {len(written)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
