#!/usr/bin/env python3
"""Create a resampled PCM WAV copy without modifying the source."""

from __future__ import annotations

import argparse
import audioop
import wave
from pathlib import Path


class ResampleError(ValueError):
    """Raised when the WAV cannot be converted by this simple script."""


def resample_wav(input_path: Path, output_path: Path, sample_rate: int) -> dict[str, str]:
    if sample_rate <= 0:
        raise ResampleError("sample rate must be greater than zero")

    with wave.open(str(input_path), "rb") as source:
        if source.getcomptype() != "NONE":
            raise ResampleError(f"Unsupported compressed WAV type: {source.getcomptype()}")
        channels = source.getnchannels()
        sample_width = source.getsampwidth()
        source_rate = source.getframerate()
        frames = source.getnframes()
        pcm = source.readframes(frames)

    converted, _ = audioop.ratecv(
        pcm,
        sample_width,
        channels,
        source_rate,
        sample_rate,
        None,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as target:
        target.setnchannels(channels)
        target.setsampwidth(sample_width)
        target.setframerate(sample_rate)
        target.writeframes(converted)

    output_frames = len(converted) // (channels * sample_width)
    return {
        "input": str(input_path),
        "output": str(output_path),
        "channels": str(channels),
        "sample_width": str(sample_width),
        "source_rate": str(source_rate),
        "sample_rate": str(sample_rate),
        "frames": str(output_frames),
        "duration": f"{output_frames / sample_rate:.3f}",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resample a PCM WAV file.")
    parser.add_argument("input", type=Path, help="Input WAV file.")
    parser.add_argument("output", type=Path, help="Output WAV file.")
    parser.add_argument("--sample-rate", required=True, type=int, help="Target sample rate.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = resample_wav(args.input, args.output, args.sample_rate)
    except (OSError, ResampleError, wave.Error) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"{result['input']} -> {result['output']} "
        f"channels={result['channels']} sample_width={result['sample_width']} "
        f"source_rate={result['source_rate']} rate={result['sample_rate']} "
        f"frames={result['frames']} duration={result['duration']}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
