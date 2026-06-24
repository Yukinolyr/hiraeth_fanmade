from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_SOURCE = Path("/mnt/e/hiraeth")
DEFAULT_OUTPUT_ROOT = Path("/home/yukino/code/nostalgia_fanmade/work/arcade_migration")

EXCLUDE_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".venv",
    "_cache",
}

EXCLUDE_FILE_NAMES = {
    "log.txt",
    "python-3.12.4-embed-amd64.zip",
    "python-3.8.10-embed-amd64.zip",
}


def should_exclude(path: Path, source: Path) -> bool:
    rel = path.relative_to(source)
    parts = rel.parts

    if any(part in EXCLUDE_DIR_NAMES for part in parts):
        return True

    if any(part.startswith(".venv") for part in parts):
        return True
    if rel.parts[:2] == ("runtime", "python") and len(rel.parts) >= 3:
        return False
    if rel.parts[:1] == ("runtime",) and any(part.startswith("python_") and "backup" in part for part in parts):
        return True

    if any(part.startswith("_backup") for part in parts):
        return True
    if any(part.startswith("backup_before") for part in parts):
        return True
    if any(part.startswith("forelise_only_backup") for part in parts):
        return True
    if any(part.startswith("boot_check_opt_backup") for part in parts):
        return True
    if any(part.endswith("_backup") for part in parts):
        return True
    if any("backup_" in part for part in parts):
        return True

    if path.is_file() and path.name in EXCLUDE_FILE_NAMES:
        return True

    if rel.as_posix() == "contents/card0.txt":
        return True

    if rel.parts[:3] == ("contents", "dev", "nvram"):
        return True

    # Player/server state should be configured per machine.
    if rel.as_posix() in {
        "MonkeyBusiness-main/db.json",
        "MonkeyBusiness-main/fengbei_fbfn_install_state.json",
    }:
        return True

    return False


def copy_tree(source: Path, dest: Path) -> list[dict[str, object]]:
    copied: list[dict[str, object]] = []
    for root, dirs, files in os.walk(source):
        root_path = Path(root)
        dirs[:] = [
            d
            for d in dirs
            if not should_exclude(root_path / d, source)
        ]
        rel_root = root_path.relative_to(source)
        (dest / rel_root).mkdir(parents=True, exist_ok=True)
        for name in files:
            src = root_path / name
            if should_exclude(src, source):
                continue
            dst = dest / src.relative_to(source)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(
                {
                    "path": src.relative_to(source).as_posix(),
                    "size": dst.stat().st_size,
                    "sha256": sha256_file(dst),
                }
            )
    return copied


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_readme(dest: Path) -> None:
    readme = """# Hiraeth Portable Runtime Package

This package is a runtime copy of the verified local `E:\\hiraeth` build.

## First Run

1. Extract this folder to a short path, preferably `E:\\hiraeth`.
2. Configure MonkeyBusiness personal settings for the target machine.
3. Run `tools\\collect_arcade_info.bat` once on the target PC and keep the report.
4. Start the game with `START_HIRAETH_PORTABLE.bat`.

`contents\\start.bat` starts MonkeyBusiness and launches SpiceTools with
`-url http://localhost:8000/core -urlslash 1`, so the copied
`contents\\prop\\ea3-config.xml` service URL is not the primary server selector
for this portable package.

MonkeyBusiness uses the bundled Python 3.8.10 runtime at
`runtime\\python\\python.exe`; no system Python or `.venv` is required for
normal startup.

## Included

- `contents`
- `MonkeyBusiness-main`
- `runtime\\python`
- Hanon four-BPM playable custom songs
- Hanon visual `data_mods`
- Arcade migration helper scripts under `tools`

## Excluded

- Logs
- Cache
- Historical backup folders
- MonkeyBusiness `db.json`
- Machine/player-specific generated state

If the target cabinet already uses another server stack, keep a full backup of that working setup before replacing files.
"""
    (dest / "README_HIRAETH_PORTABLE.md").write_text(readme, encoding="utf-8")


def write_portable_launchers(dest: Path) -> None:
    mb_runtime_start = """@echo off
TITLE MB
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONNOUSERSITE=1
cd /d %~dp0

set "RUNTIME_PY=%~dp0..\\runtime\\python\\python.exe"

if exist "%RUNTIME_PY%" (
    "%RUNTIME_PY%" pyeamu.py
    goto :eof
)

echo Runtime Python was not found: "%RUNTIME_PY%"
pause
"""
    (dest / "MonkeyBusiness-main" / "start_runtime.bat").write_text(mb_runtime_start, encoding="ascii")

    mb_start = """@echo off
TITLE MB
cd /d %~dp0

if exist "..\\runtime\\python\\python.exe" (
    call start_runtime.bat
    goto :eof
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python pyeamu.py
    goto :eof
)

echo Python was not found.
echo Install Python, or rebuild this package with a portable MonkeyBusiness runtime.
pause
"""
    (dest / "MonkeyBusiness-main" / "start_portable.bat").write_text(mb_start, encoding="ascii")

    root_start = """@echo off
setlocal
cd /d "%~dp0contents"
call start.bat
"""
    (dest / "START_HIRAETH_PORTABLE.bat").write_text(root_start, encoding="ascii")

    content_start = """@echo off
setlocal

set "MB_DIR=%~dp0..\\MonkeyBusiness-main"
set "MB_WINDOW_TITLE=Hiraeth MonkeyBusiness"

if exist "%MB_DIR%\\start_runtime.bat" (
    start "%MB_WINDOW_TITLE%" /D "%MB_DIR%" cmd /c start_runtime.bat
    ping 127.0.0.1 -n 4 >nul
) else (
    echo MonkeyBusiness start_runtime.bat not found: "%MB_DIR%\\start_runtime.bat"
)

cd /d "%~dp0"
spice64.exe -url http://localhost:8000/core -urlslash 1 -k ifs_hook.dll
set "GAME_EXIT_CODE=%ERRORLEVEL%"

rem MonkeyBusiness start_runtime.bat sets its own console title to "MB".
taskkill /FI "WINDOWTITLE eq MB" /T /F >nul 2>nul
taskkill /FI "WINDOWTITLE eq %MB_WINDOW_TITLE%" /T /F >nul 2>nul

exit /b %GAME_EXIT_CODE%
"""
    (dest / "contents" / "start.bat").write_text(content_start, encoding="ascii")


def make_zip(dest: Path) -> Path | None:
    archive = dest.with_suffix(".zip")
    if shutil.which("7z"):
        subprocess.run(["7z", "a", "-tzip", str(archive), str(dest.name)], cwd=dest.parent, check=True)
        return archive
    if shutil.which("powershell.exe"):
        archive_win = wsl_to_windows_path(archive)
        dest_win = wsl_to_windows_path(dest)
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                f"Compress-Archive -Force -Path '{dest_win}\\*' -DestinationPath '{archive_win}'",
            ],
            check=True,
        )
        return archive
    shutil.make_archive(str(dest), "zip", root_dir=dest)
    return archive


def wsl_to_windows_path(path: Path) -> str:
    resolved = path.resolve()
    parts = resolved.parts
    if len(parts) >= 3 and parts[1] == "mnt" and len(parts[2]) == 1:
        drive = parts[2].upper()
        rest = "\\".join(parts[3:])
        return f"{drive}:\\{rest}"
    if str(resolved).startswith("/home/"):
        return "\\\\wsl.localhost\\Ubuntu" + str(resolved).replace("/", "\\")
    raise ValueError(f"Cannot convert to Windows path: {resolved}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Package a portable Hiraeth runtime folder for cabinet migration.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--no-zip", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    if not (source / "contents").is_dir():
        raise SystemExit(f"Missing contents directory: {source / 'contents'}")
    if not (source / "MonkeyBusiness-main").is_dir():
        raise SystemExit(f"Missing MonkeyBusiness-main directory: {source / 'MonkeyBusiness-main'}")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = args.output_root / f"hiraeth_portable_runtime_{stamp}" / "hiraeth"
    if dest.exists():
        raise SystemExit(f"Destination already exists: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)

    manifest = copy_tree(source, dest)

    tools_src = Path(__file__).resolve().parent
    tools_dest = dest / "tools"
    tools_dest.mkdir(parents=True, exist_ok=True)
    for name in ["collect_arcade_info.bat", "collect_arcade_info.ps1"]:
        shutil.copy2(tools_src / name, tools_dest / name)

    write_readme(dest)
    write_portable_launchers(dest)
    manifest_path = dest / "PACKAGE_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(
            {
                "source": str(source),
                "created_at": stamp,
                "file_count": len(manifest),
                "files": manifest,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    total_size = sum(item["size"] for item in manifest)
    print(f"Packaged: {dest}")
    print(f"Files: {len(manifest)}")
    print(f"Payload bytes: {total_size}")

    if not args.no_zip:
        archive = make_zip(dest.parent)
        print(f"Archive: {archive}")


if __name__ == "__main__":
    main()
