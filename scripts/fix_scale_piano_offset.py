#!/usr/bin/env python3
"""Fix scale_piano values with an offset and optional octave lift."""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path


SCALE_RE = re.compile(r"(<scale_piano\b[^>]*>)(\s*)-?\d+(\s*</scale_piano>)")
MIN_SCALE_RE = re.compile(r"(<min_scale\b[^>]*>)(\s*)-?\d+(\s*</min_scale>)")
MAX_SCALE_RE = re.compile(r"(<max_scale\b[^>]*>)(\s*)-?\d+(\s*</max_scale>)")


class ScaleFixError(ValueError):
    """Raised when scale values cannot be fixed safely."""


def fix_value(value: int, subtract: int, min_allowed: int, octave: int) -> int:
    fixed = value - subtract
    if fixed < min_allowed:
        fixed += octave
    return fixed


def fix_scale_piano(path: Path, subtract: int, min_allowed: int, octave: int) -> dict[str, int | str]:
    text = path.read_text(encoding="utf-8-sig")
    scale_values: list[int] = []
    lifted = 0

    def replace_scale(match: re.Match[str]) -> str:
        nonlocal lifted
        original = int(match.group(0).split(">")[1].split("<")[0].strip())
        fixed = original - subtract
        if fixed < min_allowed:
            fixed += octave
            lifted += 1
        scale_values.append(fixed)
        return f"{match.group(1)}{match.group(2)}{fixed}{match.group(3)}"

    updated, count = SCALE_RE.subn(replace_scale, text)
    if count == 0:
        raise ScaleFixError("No scale_piano values were found.")

    min_scale = min(scale_values)
    max_scale = max(scale_values)
    updated, min_count = MIN_SCALE_RE.subn(rf"\g<1>\g<2>{min_scale}\g<3>", updated, count=1)
    updated, max_count = MAX_SCALE_RE.subn(rf"\g<1>\g<2>{max_scale}\g<3>", updated, count=1)
    if min_count != 1 or max_count != 1:
        raise ScaleFixError("Expected exactly one min_scale and one max_scale field.")

    path.write_text(updated, encoding="utf-8", newline="")
    counts = Counter(scale_values)
    return {
        "output": str(path),
        "scale_values": count,
        "min_scale": min_scale,
        "max_scale": max_scale,
        "lifted": lifted,
        "distinct_scales": len(counts),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply scale_piano -= N, then lift values below min by one octave.")
    parser.add_argument("xml", type=Path)
    parser.add_argument("--subtract", type=int, default=32)
    parser.add_argument("--min-allowed", type=int, default=1)
    parser.add_argument("--octave", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = fix_scale_piano(args.xml, args.subtract, args.min_allowed, args.octave)
    except (OSError, UnicodeError, ScaleFixError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"{result['output']} scale_values={result['scale_values']} "
        f"min_scale={result['min_scale']} max_scale={result['max_scale']} "
        f"lifted={result['lifted']} distinct_scales={result['distinct_scales']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
