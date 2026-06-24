from __future__ import annotations

import argparse
import html
import shutil
import subprocess
from pathlib import Path

from sharpen_ms_alpha import adjust_alpha, read_png_rgba, write_png_rgba

OFFICIAL_BROWN = (68, 46, 14)
EDGE = Path("/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
DEFAULT_FONT = "C:/Users/Yukino/AppData/Local/Microsoft/Windows/Fonts/DreamHanSerifJP-W10.ttf"
DEFAULT_WORK_DIR = Path("/home/yukino/code/nostalgia_fanmade/work/visual_samples/dream_han_serif_jp/generated")


def to_windows_path(path: Path) -> str:
    resolved = path.resolve()
    parts = resolved.parts
    if len(parts) >= 3 and parts[1] == "mnt" and len(parts[2]) == 1:
        drive = parts[2].upper()
        rest = "\\".join(parts[3:])
        return f"{drive}:\\{rest}" if rest else f"{drive}:\\"
    if str(resolved).startswith("/home/"):
        return "\\\\wsl.localhost\\Ubuntu" + str(resolved).replace("/", "\\")
    raise ValueError(f"Cannot convert path to Windows path: {resolved}")


def to_file_url(path: Path) -> str:
    resolved = path.resolve()
    if str(resolved).startswith("/home/"):
        return "file://wsl.localhost/Ubuntu" + str(resolved)
    if str(resolved).startswith("/mnt/"):
        return "file:///" + to_windows_path(resolved).replace("\\", "/")
    raise ValueError(f"Cannot convert path to file URL: {resolved}")


def parse_color(value: str) -> tuple[int, int, int]:
    parts = tuple(int(part) for part in value.split(","))
    if len(parts) != 3 or any(part < 0 or part > 255 for part in parts):
        raise ValueError("--color must be R,G,B with values 0-255")
    return parts


def render_html(title: str, artist: str, description: str, font_path: str, color: tuple[int, int, int]) -> str:
    title_html = html.escape(title)
    artist_html = html.escape(artist)
    desc_html = html.escape(description)
    color_css = f"rgb({color[0]}, {color[1]}, {color[2]})"
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <style>
    @font-face {{
      font-family: "DreamHanSerifJP-W10";
      src: url("file:///{font_path}") format("truetype");
    }}

    html,
    body {{
      width: 1984px;
      height: 512px;
      margin: 0;
      overflow: hidden;
      background: transparent;
    }}

    .ms {{
      position: relative;
      width: 1984px;
      height: 512px;
      font-family: "DreamHanSerifJP-W10", serif;
      color: {color_css};
      -webkit-font-smoothing: antialiased;
      text-rendering: geometricPrecision;
    }}

    .bar {{
      position: absolute;
      left: 16px;
      top: 0;
      width: 16px;
      height: 288px;
      background: {color_css};
    }}

    .bar::after {{
      content: "";
      position: absolute;
      left: 24px;
      top: 0;
      width: 8px;
      height: 288px;
      background: {color_css};
    }}

    .line {{
      position: absolute;
      left: 72px;
      right: 24px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      letter-spacing: 0;
      line-height: 1;
      font-weight: 400;
    }}

    .title {{
      top: 24px;
      font-size: 120px;
    }}

    .artist {{
      top: 192px;
      font-size: 96px;
    }}

    .desc {{
      top: 392px;
      font-size: 88px;
      text-shadow:
        2px 0 {color_css},
        -2px 0 {color_css};
    }}
  </style>
</head>
<body>
  <div class="ms">
    <div class="bar"></div>
    <div class="line title">{title_html}</div>
    <div class="line artist">{artist_html}</div>
    <div class="line desc">{desc_html}</div>
  </div>
</body>
</html>
"""


def run_edge(html_path: Path, raw_png_win: str) -> None:
    subprocess.run(
        [
            str(EDGE),
            "--headless",
            "--disable-gpu",
            "--hide-scrollbars",
            "--default-background-color=00000000",
            "--force-device-scale-factor=1",
            "--window-size=1984,512",
            f"--screenshot={raw_png_win}",
            to_file_url(html_path),
        ],
        check=True,
    )


def resize_with_powershell(raw_png_win: str, output_path: Path) -> None:
    output_win = to_windows_path(output_path)
    ps = f"""
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
$src = [Drawing.Image]::FromFile('{raw_png_win}')
$dst = New-Object Drawing.Bitmap 248, 64, ([Drawing.Imaging.PixelFormat]::Format32bppArgb)
$g = [Drawing.Graphics]::FromImage($dst)
$g.Clear([Drawing.Color]::Transparent)
$g.CompositingMode = [Drawing.Drawing2D.CompositingMode]::SourceOver
$g.CompositingQuality = [Drawing.Drawing2D.CompositingQuality]::HighQuality
$g.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.SmoothingMode = [Drawing.Drawing2D.SmoothingMode]::HighQuality
$g.PixelOffsetMode = [Drawing.Drawing2D.PixelOffsetMode]::HighQuality
$g.DrawImage($src, 0, 0, 248, 64)
$dst.Save('{output_win}', [Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$dst.Dispose()
$src.Dispose()
"""
    subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], check=True)


def postprocess_no_fringe(path: Path, color: tuple[int, int, int]) -> None:
    width, height, rows = read_png_rgba(path)
    if (width, height) != (248, 64):
        raise ValueError(f"{path}: expected 248x64, got {width}x{height}")

    for row in rows:
        for offset in range(0, len(row), 4):
            alpha = adjust_alpha(row[offset + 3], 0.55, 8, 238, None)
            if alpha == 0:
                row[offset + 3] = 0
            else:
                row[offset : offset + 3] = list(color)
                row[offset + 3] = alpha

    clear = [0, 0, 0, 0]
    rule = [*color, 255]
    for y in range(44):
        for x in range(8):
            rows[y][x * 4 : x * 4 + 4] = clear
    for y in range(36):
        for x in (2, 3, 5):
            rows[y][x * 4 : x * 4 + 4] = rule

    write_png_rgba(path, width, height, rows)


def row_groups(rows: list[list[int]], width: int, x0: int = 8, threshold: int = 16) -> list[tuple[int, int, int, int, int]]:
    profile = []
    for row in rows:
        count = 0
        for x in range(x0, width):
            off = x * 4
            if row[off + 3] > threshold and sum(row[off : off + 3]) < 500:
                count += 1
        profile.append(count)

    groups = []
    start = None
    for i, count in enumerate(profile + [0]):
        if count > 0 and start is None:
            start = i
        if (count == 0 or i == len(profile)) and start is not None:
            segment = profile[start:i]
            groups.append((start, i - 1, i - start, max(segment), sum(segment)))
            start = None
    return groups


def measure(path: Path) -> dict[str, object]:
    width, height, rows = read_png_rgba(path)
    alpha_values = [row[offset] for row in rows for offset in range(3, len(row), 4)]
    nonzero = [value for value in alpha_values if value]
    left_columns = []
    for x in range(18):
        count = 0
        for y in range(height):
            off = x * 4
            if rows[y][off + 3] > 16 and sum(rows[y][off : off + 3]) < 500:
                count += 1
        if count:
            left_columns.append((x, count))

    return {
        "size": (width, height),
        "row_groups": row_groups(rows, width),
        "alpha_zero": alpha_values.count(0),
        "alpha_mid": sum(1 for value in alpha_values if 0 < value < 255),
        "alpha_full": alpha_values.count(255),
        "alpha_avg_nonzero": round(sum(nonzero) / len(nonzero), 1) if nonzero else 0,
        "left_columns": left_columns,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate NOSTALGIA ms####_s select texture using the tuned Dream Han Serif JP W10 profile.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--artist", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--font-path", default=DEFAULT_FONT)
    parser.add_argument("--color", default="68,46,14", help="RGB text color, default sampled from official ms0324 textures.")
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--keep-temp", action="store_true")
    args = parser.parse_args()

    if not EDGE.exists():
        raise SystemExit(f"Edge not found: {EDGE}")
    if not shutil.which("powershell.exe"):
        raise SystemExit("powershell.exe not found in PATH")

    color = parse_color(args.color)
    args.work_dir.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    stem = args.output.stem
    html_path = args.work_dir / f"{stem}.html"
    raw_png_win = f"C:\\Users\\Yukino\\Downloads\\{stem}_raw.png"

    html_path.write_text(render_html(args.title, args.artist, args.description, args.font_path, color), encoding="utf-8")
    run_edge(html_path, raw_png_win)
    resize_with_powershell(raw_png_win, args.output)
    postprocess_no_fringe(args.output, color)

    print(f"wrote {args.output}")
    print(measure(args.output))

    if not args.keep_temp:
        try:
            html_path.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
