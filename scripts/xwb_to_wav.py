#!/usr/bin/env python3
"""Convert simple XACT XWB wave banks to PCM WAV files."""

from __future__ import annotations

import argparse
import struct
import wave
from pathlib import Path


XWB_SEGMENT_NAMES = [
    "bank_data",
    "entry_metadata",
    "seek_tables",
    "entry_names",
    "wave_data",
]
FORMAT_TAGS = {
    0: "PCM",
    1: "XMA",
    2: "ADPCM",
    3: "WMA",
}
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


class XwbError(ValueError):
    """Raised when an XWB file cannot be converted by this script."""


def u32(data: bytes, offset: int) -> int:
    if offset + 4 > len(data):
        raise XwbError(f"Unexpected end of file at 0x{offset:x}.")
    return struct.unpack_from("<I", data, offset)[0]


def s16(data: bytes, offset: int) -> int:
    if offset + 2 > len(data):
        raise XwbError(f"Unexpected end of block at 0x{offset:x}.")
    return struct.unpack_from("<h", data, offset)[0]


def clamp_s16(value: int) -> int:
    return max(-32768, min(32767, value))


def signed_nibble(value: int) -> int:
    value &= 0x0F
    return value - 16 if value & 0x08 else value


def parse_segments(data: bytes) -> dict[str, tuple[int, int]]:
    if data[:4] != b"WBND":
        raise XwbError("Missing WBND signature.")
    segments: dict[str, tuple[int, int]] = {}
    for index, name in enumerate(XWB_SEGMENT_NAMES):
        offset = 0x0C + index * 8
        segments[name] = (u32(data, offset), u32(data, offset + 4))
    return segments


def parse_xwb_entry(data: bytes, entry_index: int) -> dict[str, int | str]:
    segments = parse_segments(data)
    bank_offset, bank_length = segments["bank_data"]
    entry_offset, entry_length = segments["entry_metadata"]
    wave_offset, wave_length = segments["wave_data"]

    if bank_length < 96:
        raise XwbError("Bank data segment is too small.")
    entry_count = u32(data, bank_offset + 4)
    metadata_size = u32(data, bank_offset + 72)
    if metadata_size < 24:
        raise XwbError(f"Unsupported entry metadata size: {metadata_size}.")
    if entry_index < 0 or entry_index >= entry_count:
        raise XwbError(f"Entry index {entry_index} out of range; bank has {entry_count} entries.")
    if entry_length < metadata_size * entry_count:
        raise XwbError("Entry metadata segment is shorter than expected.")

    offset = entry_offset + entry_index * metadata_size
    format_raw = u32(data, offset + 4)
    format_tag = format_raw & 0x3
    channels = (format_raw >> 2) & 0x7
    sample_rate_encoded = (format_raw >> 5) & 0x3FFFF
    block_align_encoded = (format_raw >> 23) & 0xFF
    play_region_offset = u32(data, offset + 8)
    play_region_length = u32(data, offset + 12)
    loop_region_offset = u32(data, offset + 16)
    loop_region_length = u32(data, offset + 20)

    if format_tag not in (0, 2):
        raise XwbError(
            f"Unsupported XWB entry format `{FORMAT_TAGS.get(format_tag, 'unknown')}` "
            f"(tag={format_tag}); this script currently supports PCM and ADPCM only."
        )
    if channels not in (1, 2):
        raise XwbError(f"Unsupported channel count guess: {channels}.")

    if format_tag == 0:
        block_align = block_align_encoded
    else:
        # XACT compact ADPCM stores block alignment in compressed form.
        block_align = (block_align_encoded + 22) * channels
    if block_align <= 0:
        raise XwbError(f"Invalid block alignment: {block_align}.")

    if format_tag == 0 and block_align % channels != 0:
        raise XwbError(f"PCM block alignment {block_align} is not divisible by channels {channels}.")

    start = wave_offset + play_region_offset
    end = start + play_region_length
    if start < wave_offset or end > wave_offset + wave_length or end > len(data):
        raise XwbError("Entry play region points outside wave data.")
    if play_region_length % block_align != 0:
        raise XwbError(
            f"Play region length {play_region_length} is not divisible by block_align {block_align}."
        )

    return {
        "format_raw": format_raw,
        "format_tag": format_tag,
        "channels": channels,
        "sample_rate_encoded": sample_rate_encoded,
        "block_align": block_align,
        "sample_width": block_align // channels if format_tag == 0 else 2,
        "play_region_offset": play_region_offset,
        "play_region_length": play_region_length,
        "loop_region_offset": loop_region_offset,
        "loop_region_length": loop_region_length,
        "wave_data_offset": wave_offset,
        "wave_data_length": wave_length,
        "entry_data_start": start,
        "entry_data_end": end,
    }


def decode_channel_nibble(
    nibble_value: int,
    predictor: int,
    delta: int,
    sample1: int,
    sample2: int,
) -> tuple[int, int, int]:
    coef1, coef2 = COEFFICIENTS[predictor]
    nibble = signed_nibble(nibble_value)
    sample = ((sample1 * coef1 + sample2 * coef2) // 256) + nibble * delta
    sample = clamp_s16(sample)
    delta = max(16, (ADAPTATION_TABLE[nibble_value & 0x0F] * delta) // 256)
    return sample, delta, sample1


def decode_ms_adpcm_block(block: bytes, channels: int) -> list[tuple[int, ...]]:
    if channels == 1:
        header_size = 7
    elif channels == 2:
        header_size = 14
    else:
        raise XwbError(f"Unsupported ADPCM channel count: {channels}.")
    if len(block) < header_size:
        raise XwbError("ADPCM block is too small.")

    predictors = list(block[:channels])
    for predictor in predictors:
        if predictor >= len(COEFFICIENTS):
            raise XwbError(f"Unsupported ADPCM predictor index: {predictor}.")

    cursor = channels
    deltas = [s16(block, cursor + channel * 2) for channel in range(channels)]
    cursor += channels * 2
    sample1 = [s16(block, cursor + channel * 2) for channel in range(channels)]
    cursor += channels * 2
    sample2 = [s16(block, cursor + channel * 2) for channel in range(channels)]
    cursor += channels * 2

    frames: list[tuple[int, ...]] = [tuple(sample2), tuple(sample1)]

    if channels == 1:
        for byte in block[cursor:]:
            for nibble in (byte >> 4, byte & 0x0F):
                sample, deltas[0], sample2[0] = decode_channel_nibble(
                    nibble, predictors[0], deltas[0], sample1[0], sample2[0]
                )
                sample1[0] = sample
                frames.append((sample,))
    else:
        for byte in block[cursor:]:
            left, deltas[0], sample2[0] = decode_channel_nibble(
                byte >> 4, predictors[0], deltas[0], sample1[0], sample2[0]
            )
            sample1[0] = left
            right, deltas[1], sample2[1] = decode_channel_nibble(
                byte & 0x0F, predictors[1], deltas[1], sample1[1], sample2[1]
            )
            sample1[1] = right
            frames.append((left, right))

    return frames


def decode_ms_adpcm(data: bytes, channels: int, block_align: int) -> bytes:
    pcm = bytearray()
    for offset in range(0, len(data), block_align):
        block = data[offset : offset + block_align]
        frames = decode_ms_adpcm_block(block, channels)
        for frame in frames:
            for sample in frame:
                pcm += struct.pack("<h", sample)
    return bytes(pcm)


def convert_xwb_to_wav(input_path: Path, output_path: Path, entry_index: int, sample_rate: int | None) -> dict[str, int | str]:
    data = input_path.read_bytes()
    entry = parse_xwb_entry(data, entry_index)
    channels = int(entry["channels"])
    block_align = int(entry["block_align"])
    format_tag = int(entry["format_tag"])
    format_name = FORMAT_TAGS.get(format_tag, "unknown")
    encoded_rate = int(entry["sample_rate_encoded"])
    effective_rate = sample_rate if sample_rate is not None else encoded_rate
    if effective_rate <= 0:
        raise XwbError(f"Invalid sample rate: {effective_rate}.")

    start = int(entry["entry_data_start"])
    end = int(entry["entry_data_end"])
    entry_data = data[start:end]
    sample_width = int(entry["sample_width"])
    if format_tag == 0:
        if sample_width not in (1, 2, 3, 4):
            raise XwbError(f"Unsupported PCM sample width: {sample_width}.")
        pcm = entry_data
    elif format_tag == 2:
        sample_width = 2
        pcm = decode_ms_adpcm(entry_data, channels, block_align)
    else:
        raise XwbError(
            f"Unsupported XWB entry format `{format_name}` (tag={format_tag}); "
            "this script currently supports PCM and ADPCM only."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(effective_rate)
        wav.writeframes(pcm)

    frame_count = len(pcm) // (channels * sample_width)
    return {
        "input": str(input_path),
        "output": str(output_path),
        "format": format_name,
        "channels": channels,
        "sample_rate": effective_rate,
        "sample_rate_encoded": encoded_rate,
        "block_align": block_align,
        "source_bytes": len(entry_data),
        "pcm_bytes": len(pcm),
        "sample_width": sample_width,
        "frames": frame_count,
        "duration_seconds": f"{frame_count / effective_rate:.3f}",
    }


def output_path_for(input_path: Path, output: Path | None) -> Path:
    if output is None:
        return input_path.with_suffix(".wav")
    if output.suffix.lower() == ".wav":
        return output
    return output / f"{input_path.stem}.wav"


def collect_inputs(path: Path) -> list[Path]:
    if path.is_dir():
        return sorted(path.glob("*.xwb"))
    return [path]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert ADPCM XWB files to PCM WAV.")
    parser.add_argument("input", type=Path, help="Input .xwb file or folder containing .xwb files.")
    parser.add_argument("-o", "--output", type=Path, help="Output .wav path or output directory.")
    parser.add_argument("--entry", type=int, default=0, help="XWB entry index to convert; default: 0.")
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=None,
        help="Override WAV sample rate. If omitted, use the rate encoded in the XWB entry.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inputs = collect_inputs(args.input)
    if not inputs:
        print(f"error: no .xwb files found: {args.input}")
        return 1

    ok = True
    for input_path in inputs:
        try:
            output_path = output_path_for(input_path, args.output)
            if len(inputs) > 1 and args.output is not None and args.output.suffix.lower() == ".wav":
                raise XwbError("A single .wav output path cannot be used when converting a folder.")
            result = convert_xwb_to_wav(input_path, output_path, args.entry, args.sample_rate)
        except (OSError, XwbError, wave.Error) as exc:
            ok = False
            print(f"FAIL: {input_path}: {exc}")
            continue

        print(
            "OK: "
            f"{result['input']} -> {result['output']} "
            f"format={result['format']} channels={result['channels']} rate={result['sample_rate']} "
            f"encoded_rate={result['sample_rate_encoded']} block_align={result['block_align']} "
            f"frames={result['frames']} duration={result['duration_seconds']}s"
        )

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
