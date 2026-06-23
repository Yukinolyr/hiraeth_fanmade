# Custom Song Workflow

This is the recommended workflow after the 2026-06-23 cleanup audit. It starts from the verified Fengbei v0.1 package shape and avoids relying on old `work/` experiments.

## Inputs

Prepare these inputs before building a package:

```text
audio source WAV
chart XML source
song title / artist / levels
target index
jacket/select image assets for that index
template song folder or package source
target game + MonkeyBusiness version
```

For the currently verified environment:

```text
target game: NOSTALGIA op.3 PAN
music_list revision: 22621M
release_code: 2024123100
MonkeyBusiness module: modules/nostalgia
```

## Current Safe Strategy

The safe strategy is not a fully generic song builder yet. It is:

- use the verified package source under `packages/fengbei_v0.1_test/` as the packaging template;
- keep generated files out of `reference/`;
- use `work/` only for temporary generated output;
- build the zip from tracked package source;
- test on a copied game install.

Important current limitation:

- Full XSB generation is not solved.
- Visible bank name patching alone is not reliable.
- The working Fengbei package uses new file/path names while retaining template internal bank names.

## Steps

### 1. Create Package Source

Create a new tracked package source directory:

```text
packages/<package_name>/<release_root>/
```

For one-off tests, copy the verified package source and rename only what you are prepared to retest:

```text
packages/fengbei_v0.1_test/hiraeth_fanmade_fengbei_v0.1_test/
```

Do not edit an extracted copy under `work/` as the source of truth.

### 2. Prepare Chart XML

Normalize the chart into the known game-readable shape:

```bash
python3 scripts/normalize_chart_xml.py input.xml output.xml \
  --clamp-scale-piano \
  --shift-sub-note-track-index 1
```

Then verify:

```bash
python3 validate_song.py path/to/song_folder
python3 scripts/inspect_xml_structure.py path/to/song_folder/<basename>_02extreme.xml
```

Required chart rules:

- root is `music_score`;
- top-level blocks exist in the expected order;
- `event_data` includes BPM event `type=0`;
- `scale_piano` stays in `0..88`;
- `sub_note/track_index` does not use `0`;
- every `sub_note/track_index` exists in `track_info`.

### 3. Prepare Audio

Convert or trim WAV as needed:

```bash
python3 scripts/trim_wav.py input.wav preview.wav --duration-msec 15158
python3 scripts/resample_wav.py input.wav output.wav --sample-rate 44100
python3 scripts/wav_to_xwb.py output.wav song.xwb --bank-name M_T0168_marigoldjazzy
```

Current practical rule:

- If using a known-working template bank, avoid changing internal XSB/XWB bank names unless you can retest in game.
- A filename/path basename mismatch with internal bank names can be acceptable; the verified package depends on that behavior.

### 4. Prepare music_list Data

For experiments, `scripts/create_music_list_entry.py` can generate entries:

```bash
python3 scripts/create_music_list_entry.py reference/music_list.xml output.xml \
  --template M_T0168_marigoldjazzy \
  --basename M_T0169_filenameonly \
  --title "Fengbei Filename Test" \
  --artist "Fanmade" \
  --levels 5/9/13/15 \
  --index 701 \
  --merged
```

For public test packages, prefer the installer/package approach from `packages/fengbei_v0.1_test/`, because the verified release also patches/aligns MonkeyBusiness.

Do not assume:

- `max(index)+1` is safe;
- `.merged.xml` alone is enough;
- adding a `music_spec` count always works across versions.

### 5. Add Jacket Assets

If the chosen index is `701`, expected assets include paths similar to:

```text
jacket/jkms_l/afp_jkms0701_l.ifs
jacket/jkms_s/afp_jkms070_s_ifs/jk0701_s.png
jacket/jkms_s/afp_jkms070_s_ifs/ms0701_s.png
```

Missing jacket/select assets can show as `nowloading` or `ms####_s` / `afp_jkms####_l.ifs` errors in logs.

### 6. Build Release Zip

For the current Fengbei package:

```bash
python3 scripts/build_release_zip.py
python3 -m zipfile -t work/hiraeth_fanmade_fengbei_v0.1_test.zip
```

Future package builders should follow the same rule:

- source in `packages/`;
- output zip in `work/`;
- zip can be regenerated from tracked source.

### 7. Static Validation

Before testing on Windows:

```bash
python3 -m zipfile -t work/hiraeth_fanmade_fengbei_v0.1_test.zip
```

Extract and validate the packaged song folder:

```bash
python3 -m zipfile -e work/hiraeth_fanmade_fengbei_v0.1_test.zip /tmp/fb_pkg
python3 validate_song.py /tmp/fb_pkg/hiraeth_fanmade_fengbei_v0.1_test/assets/data_mods/fbfn/data_Op3/sound/music/M_T0169_filenameonly
```

Known warning for the current package:

```text
No internal bank string matches expected basename
```

This warning is expected for the verified Fengbei v0.1 package.

### 8. Windows Test

Tester flow:

```text
1. Extract zip to a short path.
2. Run CHECK_ENV.bat.
3. Run INSTALL_CLEAN.bat.
4. Restart MonkeyBusiness.
5. Launch with contents/start_fengbei_layeredfs.bat.
```

Never test by editing original game files directly.

If the test fails, collect:

```text
package logs/check_env_*.log
package logs/install_*.log
MonkeyBusiness-main/fengbei_fbfn_install_state.json
MonkeyBusiness backup folder for that install
MonkeyBusiness log
game log
```

## What To Improve Next

The current workflow is enough to reproduce the verified one-song package, but not enough for a clean fanmade-song platform. Next engineering work should add:

- a package manifest format;
- a generic build script for `packages/<package>/`;
- index conflict detection;
- jacket asset generation/checks;
- cross-version songlist checks;
- a single maintained chart importer;
- an explicit decision on template-bank reuse versus real XSB generation.
