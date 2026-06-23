# Nostalgia Chart Format Quick Reference

This is a practical quick reference for using `qt_editor` output with the official Nostalgia XML files.

## File Placement

Official chart XML files live beside the song XSB/XWB files:

```text
contents/data/sound/music/<song_folder>/<basename>_00normal.xml
contents/data/sound/music/<song_folder>/<basename>_01hard.xml
contents/data/sound/music/<song_folder>/<basename>_02extreme.xml
contents/data/sound/music/<song_folder>/<basename>_03real.xml
```

For the current `E:\hiraeth` baseline:

```text
contents/data/sound/music/m_c0003_lvb_elise/
```

## Root Structure

The XML root is:

```xml
<music_score>
  <header>...</header>
  <beat_data>...</beat_data>
  <event_data>...</event_data>
  <note_data>...</note_data>
</music_score>
```

The validator and game are most sensitive to:

- `header/music_finish_time_msec`
- `header/first_bpm`
- `beat_data/beat/start_timing_msec`
- `note_data/note/start_timing_msec`
- `note_data/note/end_timing_msec`
- `note_data/note/scale_piano`
- key range / lane fields
- sub-note `track_index`

## BPM

Observed official files store `first_bpm` as BPM multiplied by `100000` in many cases.

Example:

```xml
<first_bpm __type="s64">12000000</first_bpm>
```

Some editor-generated files may use plain BPM internally and normalize on export. Always validate against a known working official XML before game testing.

## Piano Scale

Nostalgia chart XML uses an official piano range. Current validation rules:

- `scale_piano` must be `1..88`
- values above `88` should be fixed before importing

Existing helper:

```bash
python3 scripts/fix_scale_piano_offset.py input.xml output.xml
```

## Sub Notes

Known requirement:

- `sub_note/track_index` must not be `0`

Existing helper:

```bash
python3 scripts/normalize_chart_xml.py input.xml output.xml \
  --clamp-scale-piano \
  --shift-sub-note-track-index 1
```

## Event Data

Some generated XML can miss `event_data`. The game is safer with a basic event section present.

Existing helper:

```bash
python3 scripts/add_basic_event_data.py input.xml output.xml
```

## Validation

Validate the whole song folder after replacing any chart XML:

```bash
python3 validate_song.py /mnt/e/hiraeth/contents/data/sound/music/m_c0003_lvb_elise
```

The current clean baseline should pass with:

```text
errors: 0
warnings: 0
```

## Safe Import Procedure

1. Export XML from `qt_editor`.
2. Copy the current target XML to a timestamped backup.
3. Replace only one difficulty XML first, usually `03real`.
4. Run `validate_song.py`.
5. Start the game and confirm the difficulty is selectable.
6. If the game fails to enter the chart, restore the backup XML and compare structure against the original file.

## Current Test Target

For first import experiments, replace only:

```text
E:\hiraeth\contents\data\sound\music\m_c0003_lvb_elise\m_c0003_lvb_elise_03real.xml
```

Do not replace all four difficulties until one difficulty has been verified.

