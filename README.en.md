# Nostalgia Fanmade Tools

Python tools and notes for researching local song, chart, audio, `music_list.xml`, LayeredFS, and MonkeyBusiness workflows.

This repository contains tooling, documentation, and a current Fengbei v0.1 test release package.

## Status

Current verified workflow:

- Inspect song folders, XML charts, XSB/XWB banks, and `music_list.xml`.
- Decode simple XWB banks to WAV.
- Pack PCM WAV into simple single-entry XWB banks.
- Normalize imported `music_score` XML into the observed game chart structure.
- Validate a song work folder before testing.
- Add one test song through `data_mods` with IFS LayeredFS and MonkeyBusiness songlist alignment.
- Launch the game with `spice64.exe -k ifs_hook.dll`; direct `spice64.exe` launch does not load the modded song.

Current test release:

```text
work/hiraeth_fanmade_fengbei_v0.1_test.zip
```

The package includes `CHECK_ENV.bat` for read-only pre-install diagnostics and writes `logs/check_env_*.log`, `logs/install_*.log`, and `logs/rollback_*.log`.

Release notes:

```text
docs/release_fengbei_v0.1_test.md
```

Known limitations:

- Generated XWB audio is currently PCM. ADPCM XWB generation is not implemented yet.
- Low sample-rate PCM, such as 16000 Hz, is a temporary workaround for wavebank size limits.
- XSB GUID/hash/unknown tables are not rebuilt; current workflows reuse existing XSB files or patch visible bank names only.
- The v0.1 package is a single-song Fengbei test release, not a universal multi-song installer.
- This project does not bypass DRM, signatures, online checks, anti-cheat, licensing, or integrity systems.

## Repository Layout

```text
scripts/             Reproducible inspection, conversion, and assembly tools
docs/                Notes from local format research and test workflows
validate_song.py     Song folder validator
reference/           Local-only samples, ignored by Git
work/                Local generated files; the current v0.1 test release zip is force-tracked
```

## Safety Rules

- Do not modify original game files directly.
- Keep all experiments in `work/` or a separate game test copy.
- Keep `reference/` as local-only input samples.
- Do not commit copyrighted assets, extracted game files, logs with personal paths, or generated replacement packages.

## Basic Usage

Inspect a sample folder:

```bash
python3 scripts/inspect_folder.py reference/m_t0168_marigoldjazzy
python3 scripts/inspect_banks.py reference/m_t0168_marigoldjazzy
python3 scripts/inspect_xml_structure.py reference/m_t0168_marigoldjazzy/*.xml
```

Validate a work folder:

```bash
python3 validate_song.py work/custom_song_folder
```

Convert XWB to WAV:

```bash
python3 scripts/xwb_to_wav.py reference/m_t0168_marigoldjazzy/m_t0168_marigoldjazzy.xwb -o work/decoded
```

Pack PCM WAV to XWB:

```bash
python3 scripts/wav_to_xwb.py input.wav work/test/m_t0168_marigoldjazzy.xwb --bank-name M_T0168_marigoldjazzy
```

Normalize an imported chart XML:

```bash
python3 scripts/normalize_chart_xml.py input.xml work/test/m_t0168_marigoldjazzy_02extreme.xml
```

## Documentation

- `docs/file_inventory.md`: observed file types and folder contents.
- `docs/format_notes.md`: chart XML structure notes.
- `docs/audio_bank_notes.md`: XSB/XWB observations and audio conversion notes.
- `docs/music_list_notes.md`: `music_list.xml` parsing and entry notes.
- `docs/ifs_layeredfs_notes.md`: LayeredFS, `data_mods`, and Fengbei test notes.
- `docs/chart_xml_requirements.md`: verified chart XML requirements.
- `docs/validation.md`: validator behavior.
- `docs/workflow.md`: tested workflows and results.

## Requirements

- Python 3.11 or newer recommended.
- `ffmpeg` is optional but useful for resampling WAV files before XWB packing.

Most scripts use only the Python standard library.

## License

MIT License. See `LICENSE`.
