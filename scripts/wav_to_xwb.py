#!/usr/bin/env python3
"""Pack a PCM WAV file into a simple single-entry XACT XWB file."""

from __future__ import annotations

import argparse
import hashlib
import re
import struct
import wave
from pathlib import Path


XWB_HEADER_SIZE = 0xAC
SAFE_BANK_NAME = re.compile(r"^[A-Za-z0-9_]{1,63}$")


class WavToXwbError(ValueError):
    """Raised when the input WAV cannot be packed by this script."""


def pack_u32(value: int) -> bytes:
    return struct.pack("<I", value)


def pcm_format_raw(channels: int, sample_rate: int, block_align: int, sample_width: int) -> int:
    if not 1 <= channels <= 7:
        raise WavToXwbError(f"Unsupported channel count: {channels}")
    if not 0 <= sample_rate < (1 << 18):
        raise WavToXwbError(f"Sample rate is out of XWB compact range: {sample_rate}")
    if not 0 <= block_align <= 0xFF:
        raise WavToXwbError(f"Block align is out of XWB compact range: {block_align}")
    if sample_width not in (1, 2):
        raise WavToXwbError(
            f"Unsupported PCM sample width: {sample_width}; only 8-bit and 16-bit PCM are supported."
        )

    format_tag = 0
    bits_flag = 1 if sample_width == 2 else 0
    return (
        format_tag
        | (channels << 2)
        | (sample_rate << 5)
        | (block_align << 23)
        | (bits_flag << 31)
    )


def normalized_bank_name(name: str | None, output_path: Path) -> str:
    if name is None:
        name = output_path.stem
    if not SAFE_BANK_NAME.fullmatch(name):
        raise WavToXwbError(
            "Bank name may only contain 1-63 ASCII letters, digits, and underscores."
        )
    return name


def read_pcm_wav(path: Path) -> tuple[bytes, dict[str, int]]:
    with wave.open(str(path), "rb") as wav:
        if wav.getcomptype() != "NONE":
            raise WavToXwbError(f"Unsupported compressed WAV type: {wav.getcomptype()}")
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frames = wav.getnframes()
        pcm = wav.readframes(frames)

    block_align = channels * sample_width
    expected_size = frames * block_align
    if len(pcm) != expected_size:
        raise WavToXwbError(
            f"WAV data size mismatch: expected {expected_size} bytes, got {len(pcm)} bytes."
        )
    return pcm, {
        "channels": channels,
        "sample_width": sample_width,
        "sample_rate": sample_rate,
        "frames": frames,
        "block_align": block_align,
    }


def build_xwb(pcm: bytes, info: dict[str, int], bank_name: str) -> bytes:
    header = bytearray(XWB_HEADER_SIZE)

    entry_count = 1
    wave_data_offset = XWB_HEADER_SIZE
    wave_data_length = len(pcm)
    bank_data_offset = 0x34
    bank_data_length = 96
    entry_metadata_offset = 0x94
    entry_metadata_length = 24

    header[0x00:0x04] = b"WBND"
    header[0x04:0x08] = pack_u32(46)
    header[0x08:0x0C] = pack_u32(44)

    segments = [
        (bank_data_offset, bank_data_length),
        (entry_metadata_offset, entry_metadata_length),
        (wave_data_offset, 0),
        (0, 0),
        (wave_data_offset, wave_data_length),
    ]
    offset = 0x0C
    for segment_offset, segment_length in segments:
        header[offset : offset + 4] = pack_u32(segment_offset)
        header[offset + 4 : offset + 8] = pack_u32(segment_length)
        offset += 8

    bank_name_bytes = bank_name.encode("ascii")
    header[bank_data_offset : bank_data_offset + 4] = pack_u32(0x00080000)
    header[bank_data_offset + 4 : bank_data_offset + 8] = pack_u32(entry_count)
    header[bank_data_offset + 8 : bank_data_offset + 8 + len(bank_name_bytes)] = bank_name_bytes
    header[bank_data_offset + 72 : bank_data_offset + 76] = pack_u32(entry_metadata_length)
    header[bank_data_offset + 76 : bank_data_offset + 80] = pack_u32(64)
    header[bank_data_offset + 80 : bank_data_offset + 84] = pack_u32(4)
    header[bank_data_offset + 84 : bank_data_offset + 88] = pack_u32(0)
    header[bank_data_offset + 88 : bank_data_offset + 96] = b"\x00" * 8

    format_raw = pcm_format_raw(
        info["channels"],
        info["sample_rate"],
        info["block_align"],
        info["sample_width"],
    )
    flags_and_duration = info["frames"] << 4
    header[entry_metadata_offset : entry_metadata_offset + 4] = pack_u32(flags_and_duration)
    header[entry_metadata_offset + 4 : entry_metadata_offset + 8] = pack_u32(format_raw)
    header[entry_metadata_offset + 8 : entry_metadata_offset + 12] = pack_u32(0)
    header[entry_metadata_offset + 12 : entry_metadata_offset + 16] = pack_u32(wave_data_length)
    header[entry_metadata_offset + 16 : entry_metadata_offset + 20] = pack_u32(0)
    header[entry_metadata_offset + 20 : entry_metadata_offset + 24] = pack_u32(0)

    return bytes(header) + pcm


def pcm_sha256_from_wav(path: Path) -> str:
    with wave.open(str(path), "rb") as wav:
        digest = hashlib.sha256()
        remaining = wav.getnframes()
        while remaining:
            chunk = wav.readframes(min(remaining, 65536))
            if not chunk:
                break
            digest.update(chunk)
            remaining -= len(chunk) // (wav.getnchannels() * wav.getsampwidth())
    return digest.hexdigest()


def convert_wav_to_xwb(input_path: Path, output_path: Path, bank_name: str | None) -> dict[str, str | int]:
    pcm, info = read_pcm_wav(input_path)
    bank = normalized_bank_name(bank_name, output_path)
    xwb = build_xwb(pcm, info, bank)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(xwb)

    return {
        "input": str(input_path),
        "output": str(output_path),
        "bank_name": bank,
        "channels": info["channels"],
        "sample_width": info["sample_width"],
        "sample_rate": info["sample_rate"],
        "frames": info["frames"],
        "duration_seconds": f"{info['frames'] / info['sample_rate']:.3f}",
        "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
        "xwb_size": len(xwb),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pack a PCM WAV file into a simple XWB.")
    parser.add_argument("input", type=Path, help="Input PCM WAV file.")
    parser.add_argument("output", type=Path, help="Output .xwb file.")
    parser.add_argument("--bank-name", help="Internal XWB bank name. Defaults to output stem.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = convert_wav_to_xwb(args.input, args.output, args.bank_name)
    except (OSError, wave.Error, WavToXwbError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"{result['input']} -> {result['output']} "
        f"bank_name={result['bank_name']} channels={result['channels']} "
        f"sample_width={result['sample_width']} rate={result['sample_rate']} "
        f"frames={result['frames']} duration={result['duration_seconds']}s "
        f"xwb_size={result['xwb_size']} pcm_sha256={result['pcm_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
