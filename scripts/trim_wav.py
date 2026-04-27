#!/usr/bin/env python3
"""Create a clipped PCM WAV copy without modifying the source."""

from __future__ import annotations

import argparse
import wave
from pathlib import Path


def trim_wav(input_path: Path, output_path: Path, duration_sec: float) -> dict[str, str]:
    if duration_sec <= 0:
        raise ValueError("duration must be greater than zero")

    with wave.open(str(input_path), "rb") as source:
        params = source.getparams()
        target_frames = min(source.getnframes(), round(duration_sec * source.getframerate()))
        frames = source.readframes(target_frames)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as target:
        target.setparams(params)
        target.writeframes(frames)

    return {
        "input": str(input_path),
        "output": str(output_path),
        "channels": str(params.nchannels),
        "sample_width": str(params.sampwidth),
        "rate": str(params.framerate),
        "frames": str(target_frames),
        "duration": f"{target_frames / params.framerate:.3f}",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trim a WAV file to a target duration.")
    parser.add_argument("input", type=Path, help="Input WAV file.")
    parser.add_argument("output", type=Path, help="Output WAV file.")
    parser.add_argument("--duration", required=True, type=float, help="Target duration in seconds.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = trim_wav(args.input, args.output, args.duration)
    except (OSError, ValueError, wave.Error) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"{result['input']} -> {result['output']} "
        f"channels={result['channels']} sample_width={result['sample_width']} "
        f"rate={result['rate']} frames={result['frames']} duration={result['duration']}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
