#!/usr/bin/env python3
"""Pack audio into a single-entry XACT XWB with MS ADPCM wave data."""

from __future__ import annotations

import argparse
import re
import struct
import subprocess
import tempfile
import wave
from pathlib import Path


XWB_HEADER_SIZE = 0xAC
SAFE_BANK_NAME = re.compile(r"^[A-Za-z0-9_]{1,63}$")


class AdpcmXwbError(ValueError):
    """Raised when ADPCM XWB generation cannot proceed safely."""


def pack_u32(value: int) -> bytes:
    return struct.pack("<I", value)


def normalized_bank_name(name: str | None, output_path: Path) -> str:
    if name is None:
        name = output_path.stem
    if not SAFE_BANK_NAME.fullmatch(name):
        raise AdpcmXwbError("Bank name may only contain 1-63 ASCII letters, digits, and underscores.")
    return name


def run_ffmpeg(input_path: Path, output_wav: Path, sample_rate: int, block_size: int) -> None:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_path),
        "-ar",
        str(sample_rate),
        "-ac",
        "2",
        "-c:a",
        "adpcm_ms",
        "-block_size",
        str(block_size),
        str(output_wav),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise AdpcmXwbError(f"ffmpeg failed: {result.stderr.strip()}")


def read_chunks(path: Path) -> dict[bytes, bytes]:
    data = path.read_bytes()
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise AdpcmXwbError("encoded file is not a RIFF/WAVE file")
    chunks: dict[bytes, bytes] = {}
    offset = 12
    while offset + 8 <= len(data):
        chunk_id = data[offset : offset + 4]
        chunk_size = struct.unpack_from("<I", data, offset + 4)[0]
        start = offset + 8
        end = start + chunk_size
        if end > len(data):
            raise AdpcmXwbError(f"chunk {chunk_id!r} points outside file")
        chunks[chunk_id] = data[start:end]
        offset = end + (chunk_size % 2)
    return chunks


def parse_adpcm_wav(path: Path) -> dict[str, int | bytes]:
    chunks = read_chunks(path)
    fmt = chunks.get(b"fmt ")
    data = chunks.get(b"data")
    if fmt is None or data is None:
        raise AdpcmXwbError("encoded WAV is missing fmt or data chunk")
    if len(fmt) < 20:
        raise AdpcmXwbError("fmt chunk is too small for MS ADPCM")

    format_tag, channels, sample_rate, _avg, block_align, bits_per_sample = struct.unpack_from(
        "<HHIIHH", fmt, 0
    )
    if format_tag != 2:
        raise AdpcmXwbError(f"expected MS ADPCM format tag 2, got {format_tag}")
    if channels != 2:
        raise AdpcmXwbError(f"expected stereo ADPCM, got {channels} channels")
    if bits_per_sample != 4:
        raise AdpcmXwbError(f"expected 4-bit ADPCM, got {bits_per_sample}")
    if block_align <= 0 or len(data) % block_align != 0:
        raise AdpcmXwbError(
            f"ADPCM data length {len(data)} is not divisible by block_align {block_align}"
        )

    samples_per_block = 2 + (block_align - 7 * channels) * 2 // channels
    fact = chunks.get(b"fact")
    if fact is not None and len(fact) >= 4:
        decoded_samples = struct.unpack_from("<I", fact, 0)[0]
    else:
        decoded_samples = (len(data) // block_align) * samples_per_block

    return {
        "channels": channels,
        "sample_rate": sample_rate,
        "block_align": block_align,
        "samples_per_block": samples_per_block,
        "decoded_samples": decoded_samples,
        "adpcm_data": data,
    }


def adpcm_format_raw(channels: int, sample_rate: int, block_align: int) -> int:
    if channels not in (1, 2):
        raise AdpcmXwbError(f"unsupported channel count: {channels}")
    if block_align % channels != 0:
        raise AdpcmXwbError(f"block_align {block_align} is not divisible by channels {channels}")
    encoded_block_align = block_align // channels - 22
    if not 0 <= encoded_block_align <= 0xFF:
        raise AdpcmXwbError(f"block_align {block_align} is outside compact XWB range")
    return 2 | (channels << 2) | (sample_rate << 5) | (encoded_block_align << 23)


def build_xwb(info: dict[str, int | bytes], bank_name: str) -> bytes:
    adpcm_data = info["adpcm_data"]
    if not isinstance(adpcm_data, bytes):
        raise AdpcmXwbError("internal error: adpcm_data is not bytes")

    header = bytearray(XWB_HEADER_SIZE)
    entry_count = 1
    bank_data_offset = 0x34
    bank_data_length = 96
    entry_metadata_offset = 0x94
    entry_metadata_length = 24
    wave_data_offset = XWB_HEADER_SIZE
    wave_data_length = len(adpcm_data)

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
    cursor = 0x0C
    for offset, length in segments:
        header[cursor : cursor + 4] = pack_u32(offset)
        header[cursor + 4 : cursor + 8] = pack_u32(length)
        cursor += 8

    bank_name_bytes = bank_name.encode("ascii")
    header[bank_data_offset : bank_data_offset + 4] = pack_u32(0x00080000)
    header[bank_data_offset + 4 : bank_data_offset + 8] = pack_u32(entry_count)
    header[bank_data_offset + 8 : bank_data_offset + 72] = b"\x00" * 64
    header[bank_data_offset + 8 : bank_data_offset + 8 + len(bank_name_bytes)] = bank_name_bytes
    header[bank_data_offset + 72 : bank_data_offset + 76] = pack_u32(entry_metadata_length)
    header[bank_data_offset + 76 : bank_data_offset + 80] = pack_u32(64)
    header[bank_data_offset + 80 : bank_data_offset + 84] = pack_u32(4)
    header[bank_data_offset + 84 : bank_data_offset + 88] = pack_u32(0)
    header[bank_data_offset + 88 : bank_data_offset + 96] = b"\x00" * 8

    channels = int(info["channels"])
    sample_rate = int(info["sample_rate"])
    block_align = int(info["block_align"])
    decoded_samples = int(info["decoded_samples"])
    format_raw = adpcm_format_raw(channels, sample_rate, block_align)

    header[entry_metadata_offset : entry_metadata_offset + 4] = pack_u32(decoded_samples << 4)
    header[entry_metadata_offset + 4 : entry_metadata_offset + 8] = pack_u32(format_raw)
    header[entry_metadata_offset + 8 : entry_metadata_offset + 12] = pack_u32(0)
    header[entry_metadata_offset + 12 : entry_metadata_offset + 16] = pack_u32(wave_data_length)
    header[entry_metadata_offset + 16 : entry_metadata_offset + 20] = pack_u32(0)
    header[entry_metadata_offset + 20 : entry_metadata_offset + 24] = pack_u32(0)

    return bytes(header) + adpcm_data


def convert_to_adpcm_xwb(
    input_path: Path,
    output_path: Path,
    bank_name: str | None,
    sample_rate: int,
    block_size: int,
) -> dict[str, int | str]:
    bank = normalized_bank_name(bank_name, output_path)
    with tempfile.TemporaryDirectory() as tmpdir:
        encoded_wav = Path(tmpdir) / "encoded_adpcm.wav"
        run_ffmpeg(input_path, encoded_wav, sample_rate, block_size)
        info = parse_adpcm_wav(encoded_wav)
    xwb = build_xwb(info, bank)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(xwb)

    decoded_samples = int(info["decoded_samples"])
    return {
        "input": str(input_path),
        "output": str(output_path),
        "bank_name": bank,
        "channels": int(info["channels"]),
        "sample_rate": int(info["sample_rate"]),
        "block_align": int(info["block_align"]),
        "samples_per_block": int(info["samples_per_block"]),
        "decoded_samples": decoded_samples,
        "duration_seconds": f"{decoded_samples / int(info['sample_rate']):.3f}",
        "xwb_size": len(xwb),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pack audio into an MS ADPCM XWB.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--bank-name")
    parser.add_argument("--sample-rate", type=int, default=44100)
    parser.add_argument("--block-size", type=int, default=128)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = convert_to_adpcm_xwb(
            args.input,
            args.output,
            args.bank_name,
            args.sample_rate,
            args.block_size,
        )
    except (OSError, subprocess.SubprocessError, AdpcmXwbError, wave.Error) as exc:
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
