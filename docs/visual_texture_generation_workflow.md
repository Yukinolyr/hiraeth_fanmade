# NOSTALGIA Visual Texture Generation Workflow

This note records the current local workflow for generated `ms####_l` and `ms####_s` title textures.

## Current Font And Color

- Font: `DreamHanSerifJP-W10.ttf`
- Windows font path: `C:/Users/Yukino/AppData/Local/Microsoft/Windows/Fonts/DreamHanSerifJP-W10.ttf`
- Official sampled text color: `rgb(68, 46, 14)`
- Color source: alpha-weighted sampling from official `ms0324_l.png` and `ms0324_s.png`.

## Large Texture Profile

Output format:

```text
326 x 50
RGBA PNG
transparent background
no white fringe
```

Official alignment target from `ms0324_l.png`:

```text
title:  y=3-19, height=17
artist: y=24-37, height=14
rule:   x=0,1,2 and x=5, height=42
alpha average reference: about 158
```

Current generator:

```bash
python3 scripts/generate_ms_l_texture.py \
  --title 'ピアノ基礎練習 No.1-10' \
  --artist 'ハノン (120 bpm)' \
  --output work/visual_samples/dream_han_serif_jp/ms0142_l_hanon_dream_w10_officialcolor.png
```

The generator renders transparent text at 8x through Edge, resizes to the game texture size with PowerShell/System.Drawing, then strengthens alpha while preserving transparent RGB values. Preserving transparent RGB is important; changing transparent pixels to white can create a visible white fringe in-game.

## Small Texture Profile

Output format:

```text
248 x 64
RGBA PNG
transparent background
no white fringe
```

Official alignment target from `ms0324_s.png`:

```text
title:       y=4-18, height=15
artist:      y=25-36, height=12
description: y=49-60, height=12
rule:        x=2,3 and x=5, height=36
```

The small generator uses the same rendering method as the large generator: transparent 8x render, transparent resize, nofringe alpha strengthening, and fixed pixel rules for the left vertical bars.

## Known Limits

- Long titles may still need manual font-size or horizontal fitting.
- Different strings cannot match official sample widths exactly because glyphs and text content differ.
- The current process is calibrated for this machine's Edge, Windows font install, and System.Drawing output.
