#!/usr/bin/env python3
"""Create a closeup full-audio test package with an ADPCM main XWB."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from create_closeup_full_audio_test_package import (
    MAIN_BANK_NAME,
    PROJECT_ROOT,
    SONG_BASENAME,
    FullAudioPackageError,
    create_package as create_pcm_package,
    resolve_inside_project,
)
from wav_to_xwb_adpcm import convert_to_adpcm_xwb


def create_package(base_package: Path, output_root: Path, source_wav: Path, template_dir: Path) -> dict[str, str | int]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    source_wav = resolve_inside_project(source_wav)
    template_dir = resolve_inside_project(template_dir)
    package = output_root / "lf_closeup_full_audio_adpcm"
    mod_name = "clfn_fulladpcm"
    if package.exists():
        raise FullAudioPackageError(f"destination already exists: {package}")

    # Reuse the PCM full-audio builder in a temporary sibling, then replace only the main XWB.
    temp_root = output_root / "_tmp_closeup_full_audio_adpcm"
    if temp_root.exists():
        raise FullAudioPackageError(f"temporary destination already exists: {temp_root}")
    try:
        pcm_result = create_pcm_package(base_package, temp_root, source_wav, template_dir)
        temp_package = temp_root / "lf_closeup_full_audio_wav"
        shutil.move(str(temp_package), str(package))
        shutil.rmtree(temp_root)
    except Exception:
        if temp_root.exists():
            shutil.rmtree(temp_root)
        raise

    old_mod = package / "data_mods" / "clfn_fullaudio"
    new_mod = package / "data_mods" / mod_name
    old_mod.rename(new_mod)
    target_song = new_mod / "data_Op3" / "sound" / "music" / SONG_BASENAME
    audio_work = package / "audio_work"
    main_wav = audio_work / f"{SONG_BASENAME}_main_44100.wav"
    main_xwb = target_song / f"{SONG_BASENAME}.xwb"
    adpcm_stats = convert_to_adpcm_xwb(main_wav, main_xwb, MAIN_BANK_NAME, 44100, 128)
    write_install(package, mod_name, source_wav)

    return {
        "package": str(package.relative_to(PROJECT_ROOT)),
        "mod_name": mod_name,
        "pcm_duration_msec": pcm_result["duration_msec"],
        "adpcm_xwb_size": adpcm_stats["xwb_size"],
        "adpcm_block_align": adpcm_stats["block_align"],
        "adpcm_duration_seconds": adpcm_stats["duration_seconds"],
    }


def write_install(package: Path, mod_name: str, source_wav: Path) -> None:
    text = f"""# Closeup Full Audio ADPCM Test Package

Variant: normal full-audio main XWB generated from `{source_wav.relative_to(PROJECT_ROOT)}` as MS ADPCM.

Changed:

- main `{SONG_BASENAME}.xwb` is ADPCM instead of PCM
- main/pre XSB use the normal song template
- all XML `sub_note/velocity` set to `0`

Purpose:

- test the normal full-song route using an ADPCM main XWB closer to official songs
- avoid internal `key_apiano1` playback while testing

Copy this folder into the test game's `contents/data_mods`:

```text
{package.relative_to(PROJECT_ROOT)}/data_mods/{mod_name}
```
"""
    (package / "INSTALL.md").write_text(text, encoding="utf-8", newline="\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup full-audio ADPCM test package.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_ab_scale_plus12"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    parser.add_argument("--source-wav", type=Path, default=Path("reference/closeup/Pianomidi_2.wav"))
    parser.add_argument("--template-dir", type=Path, default=Path("reference/m_t0168_marigoldjazzy"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_package(args.base_package, args.output_root, args.source_wav, args.template_dir)
    except (OSError, FullAudioPackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(
        "OK: "
        f"package={result['package']} mod_name={result['mod_name']} "
        f"pcm_duration_msec={result['pcm_duration_msec']} "
        f"adpcm_xwb_size={result['adpcm_xwb_size']} "
        f"adpcm_block_align={result['adpcm_block_align']} "
        f"adpcm_duration_seconds={result['adpcm_duration_seconds']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
