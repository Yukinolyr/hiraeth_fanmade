#!/usr/bin/env python3
"""Create a closeup full-audio XSB/XWB test package from a WAV file."""

from __future__ import annotations

import argparse
import audioop
import shutil
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

from wav_to_xwb import convert_wav_to_xwb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SONG_BASENAME = "M_T0170_closeup"
MAIN_BANK_NAME = "M_T0168_marigoldjazzy"
PRE_BANK_NAME = "M_T0168_marigoldjazzy_pre"


class FullAudioPackageError(ValueError):
    """Raised when full-audio package creation cannot proceed safely."""


def resolve_inside_project(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise FullAudioPackageError(f"Path must stay inside project root: {path}") from exc
    return resolved


def copy_base_package(base_package: Path, destination: Path, mod_name: str) -> Path:
    source = base_package / "data_mods" / "clfn_scale12"
    target = destination / "data_mods" / mod_name
    if not source.is_dir():
        raise FullAudioPackageError(f"source mod folder not found: {source}")
    if destination.exists():
        raise FullAudioPackageError(f"destination already exists: {destination}")
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)
    return target


def song_dir(package_root: Path, mod_name: str) -> Path:
    return package_root / "data_mods" / mod_name / "data_Op3" / "sound" / "music" / SONG_BASENAME


def read_wav(path: Path) -> tuple[bytes, wave._wave_params]:
    with wave.open(str(path), "rb") as source:
        if source.getcomptype() != "NONE":
            raise FullAudioPackageError(f"unsupported compressed WAV type: {source.getcomptype()}")
        params = source.getparams()
        pcm = source.readframes(params.nframes)
    return pcm, params


def write_wav(path: Path, pcm: bytes, params: wave._wave_params, sample_rate: int, frames: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as target:
        target.setnchannels(params.nchannels)
        target.setsampwidth(params.sampwidth)
        target.setframerate(sample_rate)
        target.writeframes(pcm[: frames * params.nchannels * params.sampwidth])


def resample_to_44100(input_wav: Path, output_wav: Path) -> dict[str, int | str]:
    pcm, params = read_wav(input_wav)
    if params.sampwidth not in (1, 2):
        raise FullAudioPackageError(f"unsupported sample width: {params.sampwidth}")
    if params.framerate == 44100:
        converted = pcm
    else:
        converted, _ = audioop.ratecv(
            pcm,
            params.sampwidth,
            params.nchannels,
            params.framerate,
            44100,
            None,
        )
    frames = len(converted) // (params.nchannels * params.sampwidth)
    write_wav(output_wav, converted, params, 44100, frames)
    return {
        "source_rate": params.framerate,
        "sample_rate": 44100,
        "channels": params.nchannels,
        "sample_width": params.sampwidth,
        "frames": frames,
        "duration_msec": round(frames / 44100 * 1000),
    }


def trim_preview(input_wav: Path, output_wav: Path, duration_sec: float) -> dict[str, int]:
    pcm, params = read_wav(input_wav)
    frames = min(params.nframes, round(duration_sec * params.framerate))
    write_wav(output_wav, pcm, params, params.framerate, frames)
    return {"preview_frames": frames, "preview_duration_msec": round(frames / params.framerate * 1000)}


def mute_sub_notes(song_path: Path) -> dict[str, int]:
    files_changed = 0
    velocities_changed = 0
    for xml_path in sorted(song_path.glob(f"{SONG_BASENAME}_*.xml")):
        root = ET.parse(xml_path).getroot()
        for velocity in root.findall("./note_data/note/sub_note_data/sub_note/velocity"):
            if velocity.text != "0":
                velocities_changed += 1
            velocity.text = "0"
        write_xml(root, xml_path)
        files_changed += 1
    return {"xml_files_changed": files_changed, "sub_note_velocities_zeroed": velocities_changed}


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


def write_install(package: Path, mod_name: str, source_wav: Path) -> None:
    text = f"""# Closeup Full Audio Test Package

Variant: normal full-audio main XWB generated from `{source_wav.relative_to(PROJECT_ROOT)}`.

Changed:

- main `{SONG_BASENAME}.xsb/.xwb`
- preview `{SONG_BASENAME}_pre.xsb/.xwb`
- all XML `sub_note/velocity` set to `0`

Purpose:

- isolate whether a normal full-song XWB/XSB route has the echo issue
- prevent internal `key_apiano1` sub_note playback from mixing over the WAV

Copy this folder into the test game's `contents/data_mods`:

```text
{package.relative_to(PROJECT_ROOT)}/data_mods/{mod_name}
```
"""
    (package / "INSTALL.md").write_text(text, encoding="utf-8", newline="\n")


def create_package(base_package: Path, output_root: Path, source_wav: Path, template_dir: Path) -> dict[str, str | int]:
    base_package = resolve_inside_project(base_package)
    output_root = resolve_inside_project(output_root)
    source_wav = resolve_inside_project(source_wav)
    template_dir = resolve_inside_project(template_dir)
    try:
        output_root.relative_to(PROJECT_ROOT / "work")
    except ValueError as exc:
        raise FullAudioPackageError(f"output root must be inside work/: {output_root}") from exc

    package = output_root / "lf_closeup_full_audio_wav"
    mod_name = "clfn_fullaudio"
    copy_base_package(base_package, package, mod_name)
    target_song = song_dir(package, mod_name)
    audio_work = package / "audio_work"

    main_wav = audio_work / f"{SONG_BASENAME}_main_44100.wav"
    pre_wav = audio_work / f"{SONG_BASENAME}_pre_44100.wav"
    resample_stats = resample_to_44100(source_wav, main_wav)
    preview_stats = trim_preview(main_wav, pre_wav, 15.0)

    shutil.copy2(template_dir / "m_t0168_marigoldjazzy.xsb", target_song / f"{SONG_BASENAME}.xsb")
    shutil.copy2(template_dir / "m_t0168_marigoldjazzy_pre.xsb", target_song / f"{SONG_BASENAME}_pre.xsb")

    main_xwb_stats = convert_wav_to_xwb(
        main_wav,
        target_song / f"{SONG_BASENAME}.xwb",
        MAIN_BANK_NAME,
    )
    pre_xwb_stats = convert_wav_to_xwb(
        pre_wav,
        target_song / f"{SONG_BASENAME}_pre.xwb",
        PRE_BANK_NAME,
    )
    mute_stats = mute_sub_notes(target_song)
    write_install(package, mod_name, source_wav)

    return {
        "package": str(package.relative_to(PROJECT_ROOT)),
        "mod_name": mod_name,
        "source_rate": resample_stats["source_rate"],
        "sample_rate": resample_stats["sample_rate"],
        "duration_msec": resample_stats["duration_msec"],
        "preview_duration_msec": preview_stats["preview_duration_msec"],
        "main_xwb_size": main_xwb_stats["xwb_size"],
        "pre_xwb_size": pre_xwb_stats["xwb_size"],
        **mute_stats,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create closeup full-audio test package.")
    parser.add_argument("--base-package", type=Path, default=Path("work/lf_closeup_ab_scale_plus12"))
    parser.add_argument("--output-root", type=Path, default=Path("work"))
    parser.add_argument("--source-wav", type=Path, default=Path("reference/closeup/Pianomidi_2.wav"))
    parser.add_argument("--template-dir", type=Path, default=Path("reference/m_t0168_marigoldjazzy"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_package(args.base_package, args.output_root, args.source_wav, args.template_dir)
    except (OSError, wave.Error, ET.ParseError, FullAudioPackageError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(
        "OK: "
        f"package={result['package']} mod_name={result['mod_name']} "
        f"source_rate={result['source_rate']} sample_rate={result['sample_rate']} "
        f"duration_msec={result['duration_msec']} preview_duration_msec={result['preview_duration_msec']} "
        f"main_xwb_size={result['main_xwb_size']} pre_xwb_size={result['pre_xwb_size']} "
        f"xml_files_changed={result['xml_files_changed']} "
        f"sub_note_velocities_zeroed={result['sub_note_velocities_zeroed']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
