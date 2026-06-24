#!/usr/bin/env python3
"""Set sub_note track_index values from the parent note hand value."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


HAND_RE = re.compile(r"<hand\b[^>]*>\s*(-?\d+)\s*</hand>")
TRACK_RE = re.compile(r"(<track_index\b[^>]*>)(\s*)-?\d+(\s*</track_index>)")


class TrackIndexError(ValueError):
    """Raised when the XML cannot be patched safely."""


def patch_track_index_by_hand(path: Path) -> dict[str, int]:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines(keepends=True)

    current_hand: int | None = None
    in_note = False
    replacements = 0
    hand_counts = {0: 0, 1: 0}

    output: list[str] = []
    for line in lines:
        if "<note" in line:
            in_note = True
            current_hand = None

        hand_match = HAND_RE.search(line)
        if in_note and hand_match:
            current_hand = int(hand_match.group(1))
            if current_hand in hand_counts:
                hand_counts[current_hand] += 1

        if in_note and "<track_index" in line:
            if current_hand not in (0, 1):
                raise TrackIndexError(
                    f"Encountered track_index before supported hand value in line: {line.strip()}"
                )
            target = "1" if current_hand == 0 else "2"
            line, count = TRACK_RE.subn(rf"\g<1>\g<2>{target}\g<3>", line, count=1)
            replacements += count

        output.append(line)

        if "</note>" in line:
            in_note = False
            current_hand = None

    if replacements == 0:
        raise TrackIndexError("No track_index values were replaced.")

    path.write_text("".join(output), encoding="utf-8", newline="")
    return {
        "hand_0_notes": hand_counts[0],
        "hand_1_notes": hand_counts[1],
        "track_index_replacements": replacements,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Set each sub_note/track_index from its parent note hand value."
    )
    parser.add_argument("xml", type=Path, help="XML file to update in place.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = patch_track_index_by_hand(args.xml)
    except (OSError, UnicodeError, TrackIndexError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"{args.xml} hand_0_notes={result['hand_0_notes']} "
        f"hand_1_notes={result['hand_1_notes']} "
        f"track_index_replacements={result['track_index_replacements']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
