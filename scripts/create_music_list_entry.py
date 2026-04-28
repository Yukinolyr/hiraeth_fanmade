#!/usr/bin/env python3
"""Create a work-copy music_list.xml or LayeredFS merged XML entry."""

from __future__ import annotations

import argparse
import copy
import re
import xml.etree.ElementTree as ET
from pathlib import Path


SAFE_BASENAME = re.compile(r"^M_[A-Za-z0-9_]+$")


class MusicListError(ValueError):
    """Raised when music_list.xml cannot be edited safely."""


def load_music_list(path: Path) -> tuple[str, ET.Element]:
    raw = path.read_bytes()
    text = raw.decode("shift_jis", errors="replace")
    text = re.sub(r"<\?xml[^>]*\?>", "<?xml version='1.0'?>", text, count=1)
    return text, ET.fromstring(text)


def indent(elem: ET.Element, level: int = 0) -> None:
    prefix = "\n" + "\t" * level
    child_prefix = "\n" + "\t" * (level + 1)
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = child_prefix
        for child in elem:
            indent(child, level + 1)
        if not elem[-1].tail or not elem[-1].tail.strip():
            elem[-1].tail = prefix
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = prefix


def find_spec(root: ET.Element, basename: str) -> ET.Element | None:
    for spec in root.findall("music_spec"):
        value = spec.findtext("basename")
        if value and value.lower() == basename.lower():
            return spec
    return None


def set_text(spec: ET.Element, tag: str, value: str) -> None:
    elem = spec.find(tag)
    if elem is None:
        elem = ET.SubElement(spec, tag)
        elem.set("__type", "str")
    elem.text = value


def next_index(root: ET.Element) -> str:
    indexes = []
    for spec in root.findall("music_spec"):
        raw = spec.attrib.get("index")
        if raw and raw.isdigit():
            indexes.append(int(raw))
    return str(max(indexes, default=0) + 1)


def create_entry(
    input_path: Path,
    output_path: Path,
    template_basename: str,
    new_basename: str,
    title: str,
    artist: str,
    levels: str | None,
    merged: bool,
    index: str | None,
) -> dict[str, str]:
    if not SAFE_BASENAME.fullmatch(new_basename):
        raise MusicListError("New basename must start with M_ and contain only ASCII letters, digits, underscores.")

    _, root = load_music_list(input_path)
    if find_spec(root, new_basename) is not None:
        raise MusicListError(f"Basename already exists in music_list: {new_basename}")

    template = find_spec(root, template_basename)
    if template is None:
        raise MusicListError(f"Template basename not found: {template_basename}")

    new_spec = copy.deepcopy(template)
    if index is not None:
        if not index.isdigit():
            raise MusicListError("Index must be a non-negative integer.")
        new_spec.set("index", index)
    else:
        new_spec.set("index", next_index(root))
    set_text(new_spec, "basename", new_basename)
    set_text(new_spec, "title", title)
    set_text(new_spec, "title_kana", title)
    set_text(new_spec, "artist", artist)
    set_text(new_spec, "artist_kana", artist)

    if levels:
        parts = levels.split("/")
        if len(parts) != 4 or not all(part.lstrip("-").isdigit() for part in parts):
            raise MusicListError("Levels must be formatted as N/H/E/R, for example 3/6/9/12.")
        for tag, value in zip(
            ["level_normal", "level_hard", "level_extreme", "level_real"],
            parts,
            strict=True,
        ):
            set_text(new_spec, tag, value)

    if merged:
        output_root = ET.Element(root.tag)
        output_root.append(new_spec)
    else:
        root.append(new_spec)
        output_root = root

    indent(output_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    xml_text = "<?xml version='1.0' encoding='Shift_JIS'?>\n" + ET.tostring(
        output_root,
        encoding="unicode",
        short_empty_elements=True,
    )
    output_path.write_bytes(xml_text.encode("shift_jis", errors="xmlcharrefreplace"))

    return {
        "output": str(output_path),
        "template_basename": template_basename,
        "new_basename": new_basename,
        "new_index": new_spec.attrib.get("index", ""),
        "title": title,
        "artist": artist,
        "merged": str(merged),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clone one music_spec entry into a music_list XML file.")
    parser.add_argument("input", type=Path, help="Input music_list.xml.")
    parser.add_argument("output", type=Path, help="Output music_list.xml under work/.")
    parser.add_argument("--template", required=True, help="Template basename, e.g. M_T0168_marigoldjazzy.")
    parser.add_argument("--basename", required=True, help="New basename, e.g. M_F0002_closeup_test.")
    parser.add_argument("--title", required=True, help="New title.")
    parser.add_argument("--artist", required=True, help="New artist.")
    parser.add_argument("--levels", help="Optional levels formatted as N/H/E/R.")
    parser.add_argument(
        "--merged",
        action="store_true",
        help="Output only the cloned entry under <music_list>, for LayeredFS music_list.merged.xml.",
    )
    parser.add_argument("--index", help="Optional explicit music_spec index. Useful for merged XML packages.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = create_entry(
            args.input,
            args.output,
            args.template,
            args.basename,
            args.title,
            args.artist,
            args.levels,
            args.merged,
            args.index,
        )
    except (OSError, MusicListError, ET.ParseError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(
        "OK: "
        f"{result['output']} new_index={result['new_index']} merged={result['merged']} "
        f"template={result['template_basename']} basename={result['new_basename']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
