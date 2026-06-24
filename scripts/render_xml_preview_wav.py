#!/usr/bin/env python3
"""Render a simple piano-like preview WAV from NOSTALGIA XML sub_note_data."""

from __future__ import annotations

import argparse
import math
import struct
import wave
import xml.etree.ElementTree as ET
from pathlib import Path


class RenderError(ValueError):
    """Raised when preview rendering cannot proceed safely."""


def elem_int(parent: ET.Element, tag: str) -> int:
    child = parent.find(tag)
    if child is None or child.text is None:
        raise RenderError(f"missing field: {tag}")
    return int(child.text)


def read_sub_notes(xml_path: Path) -> list[dict[str, int]]:
    root = ET.parse(xml_path).getroot()
    sub_notes: list[dict[str, int]] = []
    for note in root.findall("./note_data/note"):
        for sub_note in note.findall("./sub_note_data/sub_note"):
            start = elem_int(sub_note, "start_timing_msec")
            end = elem_int(sub_note, "end_timing_msec")
            scale = elem_int(sub_note, "scale_piano")
            velocity = elem_int(sub_note, "velocity")
            if end <= start:
                continue
            sub_notes.append(
                {
                    "start": start,
                    "end": end,
                    "scale": scale,
                    "velocity": max(0, min(127, velocity)),
                }
            )
    if not sub_notes:
        raise RenderError("no usable sub_note entries found")
    sub_notes.sort(key=lambda item: (item["start"], item["scale"]))
    return sub_notes


def midi_frequency(scale_piano: int) -> float:
    midi_note = scale_piano + 20
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def envelope(position: int, gate_frames: int, release_frames: int, sample_rate: int) -> float:
    attack = max(1, round(sample_rate * 0.006))
    decay = max(1, round(sample_rate * 0.09))
    sustain = 0.42
    total = gate_frames + release_frames

    if position < attack:
        return position / attack
    if position < attack + decay:
        t = (position - attack) / decay
        return 1.0 + (sustain - 1.0) * t
    if position < gate_frames:
        return sustain
    if position < total:
        t = (position - gate_frames) / max(1, release_frames)
        return sustain * (1.0 - t)
    return 0.0


def render_preview(
    xml_path: Path,
    output_path: Path,
    start_msec: int,
    duration_msec: int,
    sample_rate: int,
) -> dict[str, int | str]:
    if duration_msec <= 0:
        raise RenderError("duration must be positive")
    if sample_rate <= 0:
        raise RenderError("sample rate must be positive")

    sub_notes = read_sub_notes(xml_path)
    frame_count = round(duration_msec * sample_rate / 1000)
    buffer = [0.0] * frame_count
    rendered_notes = 0

    window_start = start_msec
    window_end = start_msec + duration_msec
    release_frames = round(sample_rate * 0.18)

    for sub_note in sub_notes:
        if sub_note["end"] < window_start or sub_note["start"] > window_end:
            continue

        note_start = round((sub_note["start"] - window_start) * sample_rate / 1000)
        gate_frames = max(1, round((sub_note["end"] - sub_note["start"]) * sample_rate / 1000))
        render_start = max(0, note_start)
        render_end = min(frame_count, note_start + gate_frames + release_frames)
        if render_end <= render_start:
            continue

        freq = midi_frequency(sub_note["scale"])
        velocity_gain = (sub_note["velocity"] / 127.0) ** 1.35
        base_gain = 0.055 * velocity_gain
        phase_offset = max(0, -note_start)
        for frame in range(render_start, render_end):
            pos = frame - note_start
            env = envelope(pos, gate_frames, release_frames, sample_rate)
            t = (pos + phase_offset) / sample_rate
            sample = (
                math.sin(2 * math.pi * freq * t)
                + 0.42 * math.sin(2 * math.pi * freq * 2 * t)
                + 0.20 * math.sin(2 * math.pi * freq * 3 * t)
            )
            buffer[frame] += sample * env * base_gain
        rendered_notes += 1

    peak = max((abs(value) for value in buffer), default=0.0)
    normalizer = 0.92 / peak if peak > 0.92 else 1.0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for value in buffer:
            pcm = int(max(-1.0, min(1.0, value * normalizer)) * 32767)
            packed = struct.pack("<h", pcm)
            frames.extend(packed)
            frames.extend(packed)
        wav.writeframes(bytes(frames))

    return {
        "output": str(output_path),
        "sample_rate": sample_rate,
        "frames": frame_count,
        "duration_msec": duration_msec,
        "rendered_notes": rendered_notes,
        "peak_before_normalize": f"{peak:.4f}",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a simple preview WAV from XML sub_note_data.")
    parser.add_argument("xml", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--start-msec", type=int, default=0)
    parser.add_argument("--duration-msec", type=int, default=15000)
    parser.add_argument("--sample-rate", type=int, default=44100)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = render_preview(
            args.xml,
            args.output,
            args.start_msec,
            args.duration_msec,
            args.sample_rate,
        )
    except (OSError, ET.ParseError, RenderError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"{result['output']} sample_rate={result['sample_rate']} "
        f"frames={result['frames']} duration_msec={result['duration_msec']} "
        f"rendered_notes={result['rendered_notes']} peak={result['peak_before_normalize']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
