# qt_editor Handoff

This note is for another computer or Codex instance that only needs the chart editor workflow.

## Repositories

Use two repositories:

- `qt_editor`: the PyQt5 editor used to create, import MIDI, and export Nostalgia XML.
- `nostalgia_fanmade`: workflow notes, format notes, import rules, and handoff manifests.

Do not copy a full game folder into either repository.

## Local Editor Setup

Clone the editor:

```bash
git clone https://github.com/xu3545k7/qt_editor.git
cd qt_editor
```

If using the original upstream repository, apply our local CJK font patch from `nostalgia_fanmade`:

```bash
git apply ../nostalgia_fanmade/patches/qt_editor_cjk_font_fallback.patch
```

Recommended Python dependencies:

```bash
python -m venv .venv
.venv/bin/pip install PyQt5 mido lxml matplotlib pillow numpy
```

In WSL, `xcb` may fail. Use Wayland:

```bash
QT_QPA_PLATFORM=wayland .venv/bin/python -m qt_editor.app
```

If Chinese text renders as square boxes, install or expose a CJK font. On this workstation we linked Windows fonts into WSL:

```bash
mkdir -p ~/.local/share/fonts/windows-cjk
ln -sf /mnt/c/Windows/Fonts/msyh.ttc ~/.local/share/fonts/windows-cjk/msyh.ttc
ln -sf /mnt/c/Windows/Fonts/msyhbd.ttc ~/.local/share/fonts/windows-cjk/msyhbd.ttc
ln -sf /mnt/c/Windows/Fonts/simhei.ttf ~/.local/share/fonts/windows-cjk/simhei.ttf
ln -sf /mnt/c/Windows/Fonts/simsun.ttc ~/.local/share/fonts/windows-cjk/simsun.ttc
fc-cache -f ~/.local/share/fonts/windows-cjk
```

The local editor patch in `/home/yukino/code/qt_editor/qt_editor/app.py` also chooses a CJK-capable UI font at startup.

## Editor Functions We Use

- Open `*.xml`, `*.json`, `*.mid`, `*.midi`.
- Create a new chart.
- Import MIDI as right-hand or left-hand notes.
- Load WAV for playback alignment.
- Edit note timing, lane, width, hand, and note type.
- Save as JSON for editor work-in-progress.
- Save as XML for official Nostalgia chart format.

The editor's "Export Full Song" feature targets a Unity `songs/register.json` structure. For `E:\hiraeth`, use the XML output, then place it into the official song folder manually or through our scripts.

## Current Hiraeth Baseline

The active game sandbox is:

```text
E:\hiraeth
```

It has been reduced to one song:

```text
contents\data\sound\music\m_c0003_lvb_elise
```

The four active chart files are:

```text
m_c0003_lvb_elise_00normal.xml
m_c0003_lvb_elise_01hard.xml
m_c0003_lvb_elise_02extreme.xml
m_c0003_lvb_elise_03real.xml
```

Use this song as the first controlled import target.

## Recommended Two-Computer Workflow

Computer A prepares MIDI:

1. Clean MIDI tracks.
2. Split or label right-hand and left-hand material.
3. Write BPM, offset, and track mapping into a manifest.
4. Commit or sync the MIDI plus manifest.

Computer B imports and verifies:

1. Pull the MIDI and manifest.
2. Open `qt_editor`.
3. Import right-hand and left-hand tracks.
4. Load WAV and align playback offset.
5. Save editor JSON as a working copy.
6. Save official XML.
7. Replace the target difficulty XML in `E:\hiraeth`.
8. Run `validate_song.py` and then test in game.

## Handoff Manifest

Use one folder per song:

```text
custom_charts/<song_id>/
  source.mid
  metadata.json
  notes.md
  exported/
    <basename>_03real.xml
```

Minimal `metadata.json`:

```json
{
  "song_id": "forelise_test",
  "target_basename": "m_c0003_lvb_elise",
  "bpm": 120,
  "audio_offset_ms": 0,
  "right_hand_tracks": [],
  "left_hand_tracks": [],
  "target_difficulty": "03real",
  "status": "midi_prepared"
}
```
