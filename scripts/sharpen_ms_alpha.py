from __future__ import annotations

import struct
import zlib
from pathlib import Path

BROWN = (84, 55, 17)


def paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_png_rgba(path: Path) -> tuple[int, int, list[list[int]]]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path}: not a PNG")

    pos = 8
    width = height = bit = color = None
    raw = b""
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        pos += 4
        chunk_type = data[pos : pos + 4]
        pos += 4
        chunk = data[pos : pos + length]
        pos += length + 4
        if chunk_type == b"IHDR":
            width, height, bit, color, _, _, _ = struct.unpack(">IIBBBBB", chunk)
        elif chunk_type == b"IDAT":
            raw += chunk
        elif chunk_type == b"IEND":
            break

    if bit != 8 or color != 6:
        raise ValueError(f"{path}: expected 8-bit RGBA PNG")

    decoded = zlib.decompress(raw)
    stride = width * 4
    prev = [0] * stride
    rows: list[list[int]] = []
    offset = 0

    for _ in range(height):
        filter_type = decoded[offset]
        offset += 1
        cur = list(decoded[offset : offset + stride])
        offset += stride

        if filter_type == 1:
            for i in range(stride):
                cur[i] = (cur[i] + (cur[i - 4] if i >= 4 else 0)) & 255
        elif filter_type == 2:
            for i in range(stride):
                cur[i] = (cur[i] + prev[i]) & 255
        elif filter_type == 3:
            for i in range(stride):
                left = cur[i - 4] if i >= 4 else 0
                cur[i] = (cur[i] + ((left + prev[i]) // 2)) & 255
        elif filter_type == 4:
            for i in range(stride):
                left = cur[i - 4] if i >= 4 else 0
                up = prev[i]
                up_left = prev[i - 4] if i >= 4 else 0
                cur[i] = (cur[i] + paeth(left, up, up_left)) & 255
        elif filter_type != 0:
            raise ValueError(f"{path}: unsupported PNG filter {filter_type}")

        rows.append(cur)
        prev = cur

    return width, height, rows


def write_png_rgba(path: Path, width: int, height: int, rows: list[list[int]]) -> None:
    def chunk(chunk_type: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + chunk_type
            + payload
            + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
        )

    raw = b"".join(bytes([0]) + bytes(row) for row in rows)
    payload = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    data = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", payload)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(data)


def adjust_alpha(alpha: int, gamma: float, low_cut: int, high_cut: int, quantize: int | None) -> int:
    if alpha == 0:
        return 0
    value = round(((alpha / 255.0) ** gamma) * 255)
    if value < low_cut:
        return 0
    if value > high_cut:
        return 255
    if quantize:
        value = round(value / quantize) * quantize
    return max(0, min(255, value))


def sharpen(src: Path, dst: Path, gamma: float, low_cut: int, high_cut: int, quantize: int | None) -> None:
    width, height, rows = read_png_rgba(src)
    for row in rows:
        for offset in range(0, len(row), 4):
            alpha = adjust_alpha(row[offset + 3], gamma, low_cut, high_cut, quantize)
            if alpha == 0:
                row[offset : offset + 4] = [255, 255, 255, 0]
            else:
                row[offset : offset + 4] = [*BROWN, alpha]
    write_png_rgba(dst, width, height, rows)


def white_to_alpha_sharpen(
    src: Path,
    dst: Path,
    gamma: float,
    low_cut: int,
    high_cut: int,
    quantize: int | None,
) -> None:
    width, height, rows = read_png_rgba(src)
    target_r, target_g, target_b = BROWN
    for row in rows:
        for offset in range(0, len(row), 4):
            red, green, blue = row[offset], row[offset + 1], row[offset + 2]
            base_alpha = max(
                (255.0 - red) / (255.0 - target_r),
                (255.0 - green) / (255.0 - target_g),
                (255.0 - blue) / (255.0 - target_b),
            )
            alpha = max(0, min(255, round(base_alpha * 255)))
            alpha = adjust_alpha(alpha, gamma, low_cut, high_cut, quantize)
            if alpha == 0:
                row[offset : offset + 4] = [255, 255, 255, 0]
            else:
                row[offset : offset + 4] = [*BROWN, alpha]
    write_png_rgba(dst, width, height, rows)


def main() -> None:
    root = Path("/home/yukino/code/nostalgia_fanmade/work/visual_samples/dream_han_serif_jp")
    jobs = [
        ("ms0142_s_hanon_dream_w10.png", "ms0142_s_hanon_dream_w10_soft.png", 0.68, 8, 238, None),
        ("ms0142_s_hanon_dream_w10.png", "ms0142_s_hanon_dream_w10_crisp.png", 0.52, 28, 198, 17),
        ("ms0142_s_hanon_dream_w13.png", "ms0142_s_hanon_dream_w13_soft.png", 0.68, 8, 238, None),
        ("ms0142_s_hanon_dream_w13.png", "ms0142_s_hanon_dream_w13_crisp.png", 0.52, 28, 198, 17),
        ("ms0142_s_hanon_dream_w16.png", "ms0142_s_hanon_dream_w16_soft.png", 0.70, 8, 240, None),
    ]
    for source, target, gamma, low_cut, high_cut, quantize in jobs:
        sharpen(root / source, root / target, gamma, low_cut, high_cut, quantize)
        print(target)


if __name__ == "__main__":
    main()
