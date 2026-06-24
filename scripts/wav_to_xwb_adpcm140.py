#!/usr/bin/env python3
"""Pack audio into an XWB with 140-byte stereo MS ADPCM blocks."""

from __future__ import annotations

import argparse
import math
import re
import struct
import subprocess
import tempfile
import wave
from pathlib import Path


XWB_HEADER_SIZE = 0xAC
BLOCK_ALIGN = 140
CHANNELS = 2
SAMPLE_RATE = 44100
SAMPLES_PER_BLOCK = 128
SAFE_BANK_NAME = re.compile(r"^[A-Za-z0-9_]{1,63}$")

ADAPTATION_TABLE = [
    230,
    230,
    230,
    230,
    307,
    409,
    512,
    614,
    768,
    614,
    512,
    409,
    307,
    230,
    230,
    230,
]
COEFFICIENTS = [
    (256, 0),
    (512, -256),
    (0, 0),
    (192, 64),
    (240, 0),
    (460, -208),
    (392, -232),
]


class Adpcm140Error(ValueError):
    """Raised when XWB generation cannot proceed."""


def pack_u32(value: int) -> bytes:
    return struct.pack("<I", value)


def pack_s16(value: int) -> bytes:
    return struct.pack("<h", max(-32768, min(32767, value)))


def clamp_s16(value: int) -> int:
    return max(-32768, min(32767, value))


def signed_nibble(value: int) -> int:
    value &= 0x0F
    return value - 16 if value & 0x08 else value


def normalized_bank_name(name: str | None, output_path: Path) -> str:
    if name is None:
        name = output_path.stem
    if not SAFE_BANK_NAME.fullmatch(name):
        raise Adpcm140Error("Bank name may only contain 1-63 ASCII letters, digits, and underscores.")
    return name


def convert_to_pcm_wav(input_path: Path, output_path: Path) -> None:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_path),
        "-ar",
        str(SAMPLE_RATE),
        "-ac",
        str(CHANNELS),
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise Adpcm140Error(f"ffmpeg failed: {result.stderr.strip()}")


def read_pcm_frames(path: Path) -> list[tuple[int, int]]:
    with wave.open(str(path), "rb") as wav:
        if wav.getcomptype() != "NONE":
            raise Adpcm140Error(f"Unsupported WAV compression: {wav.getcomptype()}")
        if wav.getnchannels() != CHANNELS:
            raise Adpcm140Error(f"Expected stereo WAV, got {wav.getnchannels()} channels.")
        if wav.getsampwidth() != 2:
            raise Adpcm140Error(f"Expected 16-bit PCM WAV, got sample width {wav.getsampwidth()}.")
        if wav.getframerate() != SAMPLE_RATE:
            raise Adpcm140Error(f"Expected {SAMPLE_RATE} Hz WAV, got {wav.getframerate()} Hz.")
        raw = wav.readframes(wav.getnframes())
    samples = struct.unpack("<" + "h" * (len(raw) // 2), raw)
    return list(zip(samples[0::2], samples[1::2]))


def choose_predictor(channel_samples: list[int]) -> int:
    if len(channel_samples) < 8:
        return 0
    best_predictor = 0
    best_error: int | None = None
    for index, (coef1, coef2) in enumerate(COEFFICIENTS):
        error = 0
        sample2 = channel_samples[0]
        sample1 = channel_samples[1]
        for actual in channel_samples[2: min(len(channel_samples), 18)]:
            predicted = (sample1 * coef1 + sample2 * coef2) // 256
            error += abs(actual - predicted)
            sample2, sample1 = sample1, actual
        if best_error is None or error < best_error:
            best_error = error
            best_predictor = index
    return best_predictor


def initial_delta(channel_samples: list[int], predictor: int) -> int:
    coef1, coef2 = COEFFICIENTS[predictor]
    residuals: list[int] = []
    sample2 = channel_samples[0]
    sample1 = channel_samples[1]
    for actual in channel_samples[2: min(len(channel_samples), 18)]:
        predicted = (sample1 * coef1 + sample2 * coef2) // 256
        residuals.append(abs(actual - predicted))
        sample2, sample1 = sample1, actual
    if not residuals:
        return 16
    return max(16, min(4096, int(sum(residuals) / len(residuals) / 4) or 16))


def encode_channel_sample(actual: int, predictor: int, delta: int, sample1: int, sample2: int) -> tuple[int, int, int, int]:
    coef1, coef2 = COEFFICIENTS[predictor]
    predicted = (sample1 * coef1 + sample2 * coef2) // 256
    nibble_signed = int(round((actual - predicted) / delta)) if delta else 0
    nibble_signed = max(-8, min(7, nibble_signed))
    nibble = nibble_signed & 0x0F
    decoded = clamp_s16(predicted + signed_nibble(nibble) * delta)
    new_delta = max(16, (ADAPTATION_TABLE[nibble] * delta) // 256)
    return nibble, new_delta, decoded, sample1


def encode_block(frames: list[tuple[int, int]]) -> bytes:
    if not frames:
        frames = [(0, 0)]
    while len(frames) < SAMPLES_PER_BLOCK:
        frames.append(frames[-1])
    frames = frames[:SAMPLES_PER_BLOCK]

    left = [frame[0] for frame in frames]
    right = [frame[1] for frame in frames]
    predictors = [choose_predictor(left), choose_predictor(right)]
    deltas = [initial_delta(left, predictors[0]), initial_delta(right, predictors[1])]
    sample2 = [left[0], right[0]]
    sample1 = [left[1], right[1]]

    output = bytearray()
    output.extend(bytes(predictors))
    output.extend(pack_s16(deltas[0]))
    output.extend(pack_s16(deltas[1]))
    output.extend(pack_s16(sample1[0]))
    output.extend(pack_s16(sample1[1]))
    output.extend(pack_s16(sample2[0]))
    output.extend(pack_s16(sample2[1]))

    for frame in frames[2:]:
        left_nibble, deltas[0], sample1[0], sample2[0] = encode_channel_sample(
            frame[0], predictors[0], deltas[0], sample1[0], sample2[0]
        )
        right_nibble, deltas[1], sample1[1], sample2[1] = encode_channel_sample(
            frame[1], predictors[1], deltas[1], sample1[1], sample2[1]
        )
        output.append((left_nibble << 4) | right_nibble)

    if len(output) != BLOCK_ALIGN:
        raise Adpcm140Error(f"Internal block size mismatch: {len(output)} != {BLOCK_ALIGN}")
    return bytes(output)


def encode_adpcm(frames: list[tuple[int, int]]) -> bytes:
    output = bytearray()
    for start in range(0, len(frames), SAMPLES_PER_BLOCK):
        output.extend(encode_block(frames[start : start + SAMPLES_PER_BLOCK]))
    return bytes(output)


def adpcm_format_raw() -> int:
    encoded_block_align = BLOCK_ALIGN // CHANNELS - 22
    return 2 | (CHANNELS << 2) | (SAMPLE_RATE << 5) | (encoded_block_align << 23)


def build_xwb(adpcm_data: bytes, decoded_samples: int, bank_name: str) -> bytes:
    header = bytearray(XWB_HEADER_SIZE)
    bank_data_offset = 0x34
    bank_data_length = 96
    entry_metadata_offset = 0x94
    entry_metadata_length = 24
    wave_data_offset = XWB_HEADER_SIZE
    wave_data_length = len(adpcm_data)

    header[0x00:0x04] = b"WBND"
    header[0x04:0x08] = pack_u32(46)
    header[0x08:0x0C] = pack_u32(44)
    for cursor, pair in zip(
        range(0x0C, 0x34, 8),
        [
            (bank_data_offset, bank_data_length),
            (entry_metadata_offset, entry_metadata_length),
            (wave_data_offset, 0),
            (0, 0),
            (wave_data_offset, wave_data_length),
        ],
    ):
        header[cursor : cursor + 4] = pack_u32(pair[0])
        header[cursor + 4 : cursor + 8] = pack_u32(pair[1])

    name = bank_name.encode("ascii")
    header[bank_data_offset : bank_data_offset + 4] = pack_u32(0x00080000)
    header[bank_data_offset + 4 : bank_data_offset + 8] = pack_u32(1)
    header[bank_data_offset + 8 : bank_data_offset + 72] = b"\x00" * 64
    header[bank_data_offset + 8 : bank_data_offset + 8 + len(name)] = name
    header[bank_data_offset + 72 : bank_data_offset + 76] = pack_u32(entry_metadata_length)
    header[bank_data_offset + 76 : bank_data_offset + 80] = pack_u32(64)
    header[bank_data_offset + 80 : bank_data_offset + 84] = pack_u32(4)
    header[bank_data_offset + 84 : bank_data_offset + 88] = pack_u32(0)

    header[entry_metadata_offset : entry_metadata_offset + 4] = pack_u32(decoded_samples << 4)
    header[entry_metadata_offset + 4 : entry_metadata_offset + 8] = pack_u32(adpcm_format_raw())
    header[entry_metadata_offset + 8 : entry_metadata_offset + 12] = pack_u32(0)
    header[entry_metadata_offset + 12 : entry_metadata_offset + 16] = pack_u32(wave_data_length)
    header[entry_metadata_offset + 16 : entry_metadata_offset + 20] = pack_u32(0)
    header[entry_metadata_offset + 20 : entry_metadata_offset + 24] = pack_u32(0)
    return bytes(header) + adpcm_data


def convert(input_path: Path, output_path: Path, bank_name: str | None) -> dict[str, int | str]:
    bank = normalized_bank_name(bank_name, output_path)
    with tempfile.TemporaryDirectory() as tmpdir:
        pcm_wav = Path(tmpdir) / "pcm44100.wav"
        convert_to_pcm_wav(input_path, pcm_wav)
        frames = read_pcm_frames(pcm_wav)
    if not frames:
        raise Adpcm140Error("Input audio has no frames.")
    adpcm_data = encode_adpcm(frames)
    xwb = build_xwb(adpcm_data, len(frames), bank)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(xwb)
    return {
        "input": str(input_path),
        "output": str(output_path),
        "bank_name": bank,
        "sample_rate": SAMPLE_RATE,
        "channels": CHANNELS,
        "block_align": BLOCK_ALIGN,
        "samples_per_block": SAMPLES_PER_BLOCK,
        "decoded_samples": len(frames),
        "duration_seconds": f"{len(frames) / SAMPLE_RATE:.3f}",
        "xwb_size": len(xwb),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pack audio into a 140-byte-block MS ADPCM XWB.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--bank-name")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = convert(args.input, args.output, args.bank_name)
    except (OSError, subprocess.SubprocessError, wave.Error, Adpcm140Error) as exc:
        print(f"FAIL: {exc}")
        return 1
    print(
        "OK: "
        f"{result['input']} -> {result['output']} bank_name={result['bank_name']} "
        f"channels={result['channels']} rate={result['sample_rate']} "
        f"block_align={result['block_align']} samples_per_block={result['samples_per_block']} "
        f"decoded_samples={result['decoded_samples']} duration={result['duration_seconds']}s "
        f"xwb_size={result['xwb_size']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
