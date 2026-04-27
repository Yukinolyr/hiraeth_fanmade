#!/usr/bin/env python3
"""Patch visible internal bank names in simple XSB/XWB files."""

from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path


SAFE_BANK_NAME = re.compile(r"^[A-Za-z0-9_]{1,63}$")
VISIBLE_BANK_NAME = re.compile(rb"M_[A-Za-z0-9_]+")


class PatchError(ValueError):
    """Raised when a bank file cannot be patched safely."""


def u32(data: bytes, offset: int) -> int:
    if offset + 4 > len(data):
        raise PatchError(f"Unexpected end of file at 0x{offset:x}.")
    return struct.unpack_from("<I", data, offset)[0]


def validate_name(bank_name: str) -> bytes:
    if not SAFE_BANK_NAME.fullmatch(bank_name):
        raise PatchError("Bank name may only contain 1-63 ASCII letters, digits, and underscores.")
    return bank_name.encode("ascii")


def write_padded_name(data: bytearray, offset: int, bank_name: bytes, slot_size: int = 64) -> None:
    if offset < 0 or offset + slot_size > len(data):
        raise PatchError(f"Name slot 0x{offset:x}..0x{offset + slot_size:x} is outside file.")
    data[offset : offset + slot_size] = b"\x00" * slot_size
    data[offset : offset + len(bank_name)] = bank_name


def patch_xwb(data: bytes, bank_name: bytes) -> tuple[bytes, list[int]]:
    if data[:4] != b"WBND":
        raise PatchError("XWB file does not start with WBND.")
    bank_data_offset = u32(data, 0x0C)
    bank_data_length = u32(data, 0x10)
    if bank_data_length < 96:
        raise PatchError("XWB bank_data segment is too small.")

    output = bytearray(data)
    name_offset = bank_data_offset + 8
    write_padded_name(output, name_offset, bank_name)
    return bytes(output), [name_offset]


def patch_xsb(data: bytes, bank_name: bytes) -> tuple[bytes, list[int]]:
    if data[:4] != b"SDBK":
        raise PatchError("XSB file does not start with SDBK.")

    matches = [
        match.start()
        for match in VISIBLE_BANK_NAME.finditer(data)
        if match.group().startswith(b"M_")
    ]
    if not matches:
        raise PatchError("No visible M_* bank name strings found in XSB.")

    output = bytearray(data)
    patched: list[int] = []
    for offset in matches:
        # The current simple XSB samples store bank names in 64-byte NUL-padded slots.
        write_padded_name(output, offset, bank_name)
        patched.append(offset)
    return bytes(output), patched


def patch_file(input_path: Path, output_path: Path, bank_name: str) -> list[int]:
    name_bytes = validate_name(bank_name)
    data = input_path.read_bytes()
    suffix = input_path.suffix.lower()
    if suffix == ".xwb":
        patched, offsets = patch_xwb(data, name_bytes)
    elif suffix == ".xsb":
        patched, offsets = patch_xsb(data, name_bytes)
    else:
        raise PatchError(f"Unsupported file extension: {input_path.suffix}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(patched)
    return offsets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Patch simple XSB/XWB internal bank names.")
    parser.add_argument("input", type=Path, help="Input .xsb or .xwb file.")
    parser.add_argument("output", type=Path, help="Output patched file.")
    parser.add_argument("bank_name", help="New internal bank name, for example M_F0002_closeup_test.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        offsets = patch_file(args.input, args.output, args.bank_name)
    except (OSError, PatchError) as exc:
        print(f"FAIL: {exc}")
        return 1

    offsets_text = ", ".join(f"0x{offset:04x}" for offset in offsets)
    print(f"OK: {args.input} -> {args.output} bank_name={args.bank_name} offsets={offsets_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
