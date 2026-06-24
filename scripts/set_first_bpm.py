#!/usr/bin/env python3
"""Set header first_bpm to the NOSTALGIA fixed-point BPM value."""

from __future__ import annotations

import argparse
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path


FIRST_BPM_RE = re.compile(r"(<first_bpm\b[^>]*>)(\s*)-?\d+(\s*</first_bpm>)", re.MULTILINE)


class FirstBpmError(ValueError):
    """Raised when first_bpm cannot be set safely."""


def bpm_to_fixed(raw_bpm: str) -> int:
    try:
        bpm = Decimal(raw_bpm)
    except InvalidOperation as exc:
        raise FirstBpmError(f"Invalid BPM: {raw_bpm}") from exc
    if bpm <= 0:
        raise FirstBpmError("BPM must be positive.")
    return int(bpm * Decimal(100000))


def set_first_bpm(path: Path, raw_bpm: str) -> dict[str, str | int]:
    fixed_bpm = bpm_to_fixed(raw_bpm)
    text = path.read_text(encoding="utf-8-sig")
    updated, count = FIRST_BPM_RE.subn(rf"\g<1>\g<2>{fixed_bpm}\g<3>", text, count=1)
    if count != 1:
        raise FirstBpmError(f"Expected exactly one first_bpm field, replaced {count}.")

    path.write_text(updated, encoding="utf-8", newline="")
    return {"output": str(path), "bpm": raw_bpm, "fixed_bpm": fixed_bpm}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set header first_bpm to BPM * 100000.")
    parser.add_argument("xml", type=Path)
    parser.add_argument("--bpm", required=True, help="Song BPM, e.g. 10 or 160.5.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = set_first_bpm(args.xml, args.bpm)
    except (OSError, UnicodeError, FirstBpmError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(f"OK: {result['output']} bpm={result['bpm']} fixed_bpm={result['fixed_bpm']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
