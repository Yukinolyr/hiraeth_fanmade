from __future__ import annotations

import re
from pathlib import Path

FILES = [
    Path("/mnt/e/hiraeth/contents/data/sound/music_list.xml"),
    Path("/mnt/e/hiraeth/contents/data_op2/sound/music_list.xml"),
    Path("/mnt/e/hiraeth/contents/data_op3/sound/music_list.xml"),
    Path("/mnt/e/hiraeth/MonkeyBusiness-main/modules/nostalgia/music_list.xml"),
]

SONGS = {
    142: ("M_C0035_hanon_120", "120"),
    143: ("M_C0036_hanon_108", "108"),
    144: ("M_C0037_hanon_90", "90"),
    145: ("M_C0038_hanon_78", "78"),
}

TITLE = "ピアノ基礎練習 No.1-10"
DESC = "毎日の小さな反復が、確かな音をつくる"


def set_tag(block: str, tag: str, value: str) -> str:
    pattern = rf"(<{tag} __type=\"str\">).*?(</{tag}>)"
    return re.sub(pattern, rf"\g<1>{value}\2", block, count=1)


def update_block(block: str, bpm: str) -> str:
    artist = f"ハノン ({bpm} bpm)"
    block = set_tag(block, "title", TITLE)
    block = set_tag(block, "title_kana", TITLE)
    block = set_tag(block, "artist", artist)
    block = set_tag(block, "artist_kana", artist)
    block = set_tag(block, "description", DESC)
    return block


def update_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    original = text

    for index, (basename, bpm) in SONGS.items():
        block_pattern = re.compile(
            rf"(<music_spec __type=\"void\" index=\"{index}\">.*?</music_spec>)",
            re.DOTALL,
        )

        def repl(match: re.Match[str]) -> str:
            block = match.group(1)
            expected = f'<basename __type="str">{basename}</basename>'
            if expected not in block:
                raise RuntimeError(f"{path}: index {index} does not contain {basename}")
            return update_block(block, bpm)

        text, count = block_pattern.subn(repl, text, count=1)
        if count != 1:
            raise RuntimeError(f"{path}: did not find exactly one block for {basename}")

    if text != original:
        path.write_text(text, encoding="cp932", newline="")


def main() -> None:
    for path in FILES:
        update_file(path)


if __name__ == "__main__":
    main()
