#!/usr/bin/env python3
"""Insert one music_spec while preserving the original music_list.xml bytes style."""

from __future__ import annotations

import argparse
import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path


SAFE_BASENAME = re.compile(r"^M_[A-Za-z0-9_]+$")
SPEC_RE = re.compile(r"\t<music_spec\b[^>]*>.*?\n\t</music_spec>[ \t]*\n?", re.DOTALL)


class MusicListRawError(ValueError):
    """Raised when raw insertion cannot be performed safely."""


def read_shift_jis(path: Path) -> str:
    return path.read_bytes().decode("shift_jis", errors="replace")


def write_shift_jis(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("shift_jis", errors="xmlcharrefreplace"))


def find_spec_block(text: str, basename: str) -> str:
    needle = f"<basename __type='str'>{basename}</basename>"
    alt_needle = f'<basename __type="str">{basename}</basename>'
    for match in SPEC_RE.finditer(text):
        block = match.group(0)
        if needle in block or alt_needle in block:
            return block
    raise MusicListRawError(f"Template basename not found: {basename}")


def basename_exists(text: str, basename: str) -> bool:
    return (
        f"<basename __type='str'>{basename}</basename>" in text
        or f'<basename __type="str">{basename}</basename>' in text
    )


def replace_index(block: str, index: str) -> str:
    if not index.isdigit():
        raise MusicListRawError("Index must be a non-negative integer.")

    def repl(match: re.Match[str]) -> str:
        return f"{match.group(1)}{match.group(2)}{index}{match.group(4)}"

    updated, count = re.subn(r"(index=)(['\"])([^'\"]*)(\2)", repl, block, count=1)
    if count != 1:
        raise MusicListRawError("Could not replace music_spec index.")
    return updated


def set_tag_text(block: str, tag: str, value: str) -> str:
    escaped = html.escape(value, quote=False)
    full_re = re.compile(rf"(<{tag}\b[^>]*>)(.*?)(</{tag}>)", re.DOTALL)
    updated, count = full_re.subn(rf"\g<1>{escaped}\g<3>", block, count=1)
    if count:
        return updated

    empty_re = re.compile(rf"(<{tag}\b[^>]*)/>")
    updated, count = empty_re.subn(rf"\g<1>>{escaped}</{tag}>", block, count=1)
    if count:
        return updated

    raise MusicListRawError(f"Tag not found in template block: {tag}")


def insert_before_root_close(text: str, block: str) -> str:
    close = "</music_list>"
    pos = text.rfind(close)
    if pos == -1:
        raise MusicListRawError("Missing </music_list> root close.")
    if not block.endswith("\n"):
        block += "\n"
    return text[:pos] + block + text[pos:]


def create_raw_entry(
    input_path: Path,
    output_path: Path,
    template_basename: str,
    new_basename: str,
    index: str,
    title: str,
    artist: str,
    levels: str | None,
) -> None:
    if not SAFE_BASENAME.fullmatch(new_basename):
        raise MusicListRawError("New basename must start with M_ and contain only ASCII letters, digits, underscores.")

    text = read_shift_jis(input_path)
    if basename_exists(text, new_basename):
        raise MusicListRawError(f"Basename already exists in music_list: {new_basename}")

    block = find_spec_block(text, template_basename)
    block = replace_index(block, index)
    block = set_tag_text(block, "basename", new_basename)
    block = set_tag_text(block, "title", title)
    block = set_tag_text(block, "title_kana", title)
    block = set_tag_text(block, "artist", artist)
    block = set_tag_text(block, "artist_kana", artist)
    block = set_tag_text(block, "offline", "1")
    block = set_tag_text(block, "start_date", "2023-12-20 10:00")
    block = set_tag_text(block, "end_date", "9999-12-31 23:59")
    block = set_tag_text(block, "expiration_date", "9999-12-31 23:59")

    if levels:
        parts = levels.split("/")
        if len(parts) != 4 or not all(part.lstrip("-").isdigit() for part in parts):
            raise MusicListRawError("Levels must be formatted as N/H/E/R, for example 3/5/7/0.")
        for tag, value in zip(
            ["level_normal", "level_hard", "level_extreme", "level_real"],
            parts,
            strict=True,
        ):
            block = set_tag_text(block, tag, value)

    output_text = insert_before_root_close(text, block)
    ET.fromstring(output_text)
    write_shift_jis(output_path, output_text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Raw-insert one music_spec into music_list.xml.")
    parser.add_argument("input", type=Path, help="Input music_list.xml.")
    parser.add_argument("output", type=Path, help="Output music_list.xml.")
    parser.add_argument("--template", required=True, help="Template basename.")
    parser.add_argument("--basename", required=True, help="New basename.")
    parser.add_argument("--index", required=True, help="New music_spec index.")
    parser.add_argument("--title", required=True, help="New title.")
    parser.add_argument("--artist", required=True, help="New artist.")
    parser.add_argument("--levels", help="Optional levels formatted as N/H/E/R.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        create_raw_entry(
            args.input,
            args.output,
            args.template,
            args.basename,
            args.index,
            args.title,
            args.artist,
            args.levels,
        )
    except (OSError, MusicListRawError, ET.ParseError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(f"OK: {args.output} basename={args.basename} index={args.index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
