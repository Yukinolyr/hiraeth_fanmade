#!/usr/bin/env python3
"""Add a basic NOSTALGIA track_info block to an XML chart."""

from __future__ import annotations

import argparse
from pathlib import Path


TRACK_INFO_BLOCK = """  <track_info>
    <track>
      <index __type="s32">1</index>
      <name __type="str">key_apiano1</name>
    </track>
    <track>
      <index __type="s32">2</index>
      <name __type="str">key_apiano1</name>
    </track>
  </track_info>
"""


class TrackInfoError(ValueError):
    """Raised when track_info cannot be added safely."""


def add_track_info(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8-sig")
    if "<track_info>" in text:
        raise TrackInfoError("track_info already exists.")

    closing = "</music_score>"
    if closing not in text:
        raise TrackInfoError("missing </music_score> closing tag.")

    updated = text.replace(closing, TRACK_INFO_BLOCK + closing, 1)
    path.write_text(updated, encoding="utf-8", newline="")
    return {"output": str(path), "tracks": "1,2"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add track_info with key_apiano1 tracks 1 and 2.")
    parser.add_argument("xml", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = add_track_info(args.xml)
    except (OSError, UnicodeError, TrackInfoError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(f"OK: {result['output']} tracks={result['tracks']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
