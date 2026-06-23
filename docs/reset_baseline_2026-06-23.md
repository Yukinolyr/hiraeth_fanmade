# Restart Baseline / Cleanup Audit

Last updated: 2026-06-23

This document is the technical handoff before restarting the project with a cleaner workflow. It records what has been verified, what should be kept, and which generated outputs can be removed or archived.

## Current State

The repository is split into three kinds of data:

- Versioned project knowledge: `README.md`, `docs/`, `scripts/`, `validate_song.py`, and `packages/`.
- Local reference material: `reference/`, ignored by Git.
- Generated experiments and package outputs: `work/`, ignored by Git except the current release zip.

Current disk usage observed during cleanup:

```text
project total: about 4.4G
reference/:   about 805M
work/:        about 3.5G
packages/:    about 18M
scripts/:     about 596K
docs/:        about 132K
```

There is no meaningful tracked `output/` directory at the time of this audit. The clutter is concentrated in `work/`.

## Verified Baseline

The only fully verified end-to-end result is the Fengbei v0.1 single-song test package.

Keep these as the restart baseline:

```text
packages/fengbei_v0.1_test/hiraeth_fanmade_fengbei_v0.1_test/
work/hiraeth_fanmade_fengbei_v0.1_test.zip
scripts/build_release_zip.py
docs/release_fengbei_v0.1_test.md
docs/mac_codex_handoff.md
```

Package facts:

```text
song index: 701
basename:   M_T0169_filenameonly
title:      Fengbei Filename Test
mod name:   fbfn
target:     NOSTALGIA op.3 PAN
songlist:   revision=22621M, release_code=2024123100
launch:     spice64.exe -k ifs_hook.dll
```

The working package intentionally keeps `.xsb/.xwb` internal bank names from `M_T0168_marigoldjazzy`. Static validation reports that mismatch as warnings, but game testing confirmed this setup works. Do not "fix" internal bank names unless there is a Windows retest plan.

## Confirmed Technical Conclusions

### LayeredFS / Game Loading

- `contents/data_mods/<mod_name>/...` works only when the game is launched with `spice64.exe -k ifs_hook.dll`.
- Direct `spice64.exe` launch does not load the new song.
- For the verified package, MonkeyBusiness songlist alignment is required.
- The installer writes both MonkeyBusiness-side and game-side songlist data because `.merged.xml` alone was not reliable in all tests.
- `data_Op3/sound/music/<UppercaseBasename>/...` is the path shape observed in game logs for Op3 song resource loading.

### music_list

- `music_list.xml` uses `Shift_JIS`.
- `music_spec index` must be treated as environment-specific; `701` is verified only for the current package.
- Adding a brand-new `music_spec` by simple merged/raw insertion exposed multiple failure modes before the final installer path was found.
- Duplicating an existing basename does not produce a reliable new selectable song.
- Missing jacket resources can produce `nowloading` / missing `ms####_s` and `afp_jkms####_l.ifs` messages.

### Chart XML

Keep `docs/chart_xml_requirements.md` as the chart import reference.

Verified high-risk rules:

- root must be `music_score`.
- top-level blocks should be `header`, `note_data`, `event_data`, `beat_data`, `track_info`, `velocity_zone_data`.
- `scale_piano` and `sub_note/scale_piano` should stay in `0..88`.
- `sub_note/track_index=0` is unsafe and caused game entry failure.
- `sub_note/track_index` must refer to an existing `track_info/index`.
- `event_data` must contain at least BPM event `type=0`.

### XSB / XWB

- XSB/XWB inspection and basic conversion scripts are useful and should be kept.
- Full XSB generation is not solved.
- `patch_bank_names.py` only patches visible strings; it does not rebuild unknown XSB tables.
- Tests showed that new file path basename can work while internal bank name remains from the template. This is the current practical workaround.
- ADPCM XWB generation remains incomplete/experimental.

## Recommended Restart Workflow

The new workflow should start from the verified release package shape, not from the old `work/` experiments.

1. Choose a clean package source directory under `packages/<package_name>/`.
2. Choose a songlist strategy first:
   - for a public test, use the installer approach from `packages/fengbei_v0.1_test`;
   - do not assume `.merged.xml` alone is enough.
3. Prepare chart XML:
   - normalize top-level structure;
   - clamp `scale_piano` to `0..88`;
   - shift `sub_note/track_index` away from `0`;
   - validate with `python3 validate_song.py`.
4. Prepare audio/banks:
   - prefer the known-working template-bank strategy until full XSB generation is solved;
   - avoid casual visible-string bank renaming for new basenames.
5. Add jacket/select assets for the chosen index before user testing.
6. Build the release zip from tracked package source:

```bash
python3 scripts/build_release_zip.py
python3 -m zipfile -t work/hiraeth_fanmade_fengbei_v0.1_test.zip
```

7. Test only on a game copy, never on original game files.
8. Ask testers for installer logs, MonkeyBusiness logs, game logs, and install state JSON when something fails.

## Keep

Keep in Git:

```text
README.md
README.en.md
README.zh-CN.md
AGENTS.md
LICENSE
docs/
validate_song.py
scripts/inspect_folder.py
scripts/inspect_banks.py
scripts/inspect_music_list.py
scripts/inspect_xml_structure.py
scripts/normalize_chart_xml.py
scripts/create_music_list_entry.py
scripts/create_music_list_entry_raw.py
scripts/assemble_layeredfs_song_mod.py
scripts/assemble_custom_song.py
scripts/create_work_copy.py
scripts/create_renamed_song_copy.py
scripts/patch_bank_names.py
scripts/resample_wav.py
scripts/trim_wav.py
scripts/wav_to_xwb.py
scripts/xwb_to_wav.py
scripts/build_release_zip.py
packages/fengbei_v0.1_test/
work/hiraeth_fanmade_fengbei_v0.1_test.zip
```

Keep locally if disk space allows:

```text
reference/music_list.xml
reference/m_t0168_marigoldjazzy/
reference/fengbei/
reference/ifs_sample/
reference/NOSTALGIAomni For 2024102200/
```

These are the most useful references for restarting from the verified Fengbei package and LayeredFS behavior.

## Archive Before Deleting

These are useful for forensic comparison but not needed for a clean restart:

```text
reference/closeup/
reference/fanmade/
reference/himawari/
reference/official_pack/
reference/m_c0047_chopin_etude10_4/
reference/m_c0064_hungary06/
reference/log.txt
otherswork/
```

If these cannot be restored from another source, archive them outside the repo before deleting.

Untracked helper scripts worth reviewing before deletion:

```text
scripts/add_basic_event_data.py
scripts/add_basic_track_info.py
scripts/add_himawari_style_velocity_zones.py
scripts/finalize_chart_copies.py
scripts/fix_scale_piano_offset.py
scripts/render_xml_preview_wav.py
scripts/set_first_bpm.py
scripts/set_track_index_by_hand.py
scripts/wav_to_xwb_adpcm.py
```

These may contain reusable transformations, but they should be merged into fewer maintained scripts or archived. Do not leave them as undocumented top-level tools.

## Safe To Delete After Confirmation

The following `work/` content is generated output. It is not needed once this document and the existing docs are kept.

Keep only:

```text
work/.gitkeep
work/hiraeth_fanmade_fengbei_v0.1_test.zip
```

The extracted package can be deleted because the source now exists in `packages/`:

```text
work/hiraeth_fanmade_fengbei_v0.1_test/
```

Generated experiment groups safe to delete or archive:

```text
work/audio_replace_*
work/decoded_*
work/custom_song_*
work/wav_pack_test*
work/closeup_charts_final/
work/lf_closeup_*
work/m_c0105_closeup_*
work/layeredfs_himawari_*
work/himawari_*
work/elise_himawari_song/
work/layeredfs_replace_elise_*
work/layeredfs_replace_himawari_*
work/layeredfs_marigold_himawari_replace/
work/music_list_himawari_*
work/music_list_closeup_*
work/music_list_test*
work/music_list_merged_test/
work/music_list_modify_existing/
work/layeredfs_music_list_*
work/install_package_marigoldjazzy_*
work/lf_fb_mj*
work/omni_fengbei_mj*
work/lf_fengbei_add*
work/omni_fengbei_add*
work/fengbei_added_song_*
work/fengbei_on_marigoldjazzy_*
work/fengbei_mb_oneclick_test/
work/music_list_fengbei_*
work/omni_fengbei_*
work/jacket_fix_probe/
work/lf_mj/
work/m_c0047_decode_check/
work/marigold_original_decoded_check/
```

Reason: these directories were intermediate A/B packages, decoded audio, temporary copied songs, or superseded package attempts. Their conclusions are now documented in `docs/ifs_layeredfs_notes.md`, `docs/audio_bank_notes.md`, `docs/music_list_notes.md`, `docs/chart_xml_requirements.md`, and this file.

Untracked `create_closeup_*` scripts can be deleted or moved to an archive folder if no longer doing Closeup variable-isolation research:

```text
scripts/create_closeup_*.py
```

They are one-off experiment generators and should not be part of the restarted core workflow.

## Suggested Cleanup Commands

Review first:

```bash
du -sh work/* 2>/dev/null | sort -h
git status --short --ignored
```

After confirming no local-only result is needed, remove generated work output while keeping the release zip:

```bash
find work -mindepth 1 \
  ! -name '.gitkeep' \
  ! -name 'hiraeth_fanmade_fengbei_v0.1_test.zip' \
  -exec rm -rf {} +
```

Do not run the cleanup command before committing or otherwise saving:

- `packages/fengbei_v0.1_test/`
- `scripts/build_release_zip.py`
- this document
- the updated README/handoff docs

## Open Problems For The Restart

- Build a clean general installer model instead of single-song hardcoding.
- Define a manifest format for song metadata, index, jacket assets, and source files.
- Add index conflict detection.
- Add cross-version `music_list.xml` compatibility checks.
- Decide whether the project should support full XSB generation or explicitly standardize on template-bank reuse.
- Reduce chart tools into one maintained importer/normalizer instead of many one-off scripts.
- Add a reproducible package build script for future songs, not only Fengbei v0.1.
