# Mac Codex Handoff

Last updated: 2026-05-01

This document is the handoff entry point for continuing development from a Mac laptop while Windows/game testing happens on other machines.

## Current Goal

The project is no longer only a song replacement experiment. The current working direction is:

- add a fanmade song through `contents/data_mods`
- load it with IFS LayeredFS via `ifs_hook.dll`
- keep MonkeyBusiness `modules/nostalgia/music_list.xml` aligned with the game music list
- ship a double-clickable test package for normal MB users

Chart format research is temporarily paused because other team members are studying the exact chart format and building a chart editor.

## Current Verified Release

Current package:

```text
work/hiraeth_fanmade_fengbei_v0.1_test.zip
```

Current test song:

```text
index: 701
basename: M_T0169_filenameonly
title: Fengbei Filename Test
data_mods package: fbfn
```

Expected environment:

```text
NOSTALGIA op.3 PAN
music_list revision: 22621M
music_list release_code: 2024123100
MonkeyBusiness module path: modules/nostalgia
```

Verified locally on the Windows test machine:

```text
contents: E:\Nostalgia_test\nostalgia\Nostalgia\PAN\contents
MB:       E:\Nostalgia_test\nostalgia\MonkeyBusiness-main
```

The package was installed successfully there with `INSTALL_CLEAN` on 2026-04-29. The installer created:

```text
E:\Nostalgia_test\nostalgia\Nostalgia\PAN\contents\data_mods\fbfn
E:\Nostalgia_test\nostalgia\Nostalgia\PAN\contents\start_fengbei_layeredfs.bat
E:\Nostalgia_test\nostalgia\MonkeyBusiness-main\fengbei_fbfn_backup\20260429_055149
```

## What Is Confirmed

These are confirmed by actual game testing, not just static inspection:

- The new song can appear in game when launched through `spice64.exe -k ifs_hook.dll`.
- Direct `spice64.exe` launch does not load the new song.
- Preview audio works.
- Gameplay starts without freezing.
- Gameplay audio works.
- The current Fengbei chart files are accepted by the game.
- Title image works.
- Jacket display works after MB songlist and game-side songlist are aligned.
- Installing into the local `nostalgia_test` environment succeeds.

Static checks also pass:

- `python3 -m zipfile -t work/hiraeth_fanmade_fengbei_v0.1_test.zip`
- `python3 validate_song.py` on the packaged song folder after extraction

Known static warning:

- The XSB/XWB internal bank names still contain `M_T0168_marigoldjazzy`.
- This is part of the currently tested working setup, not a newly discovered packaging error.
- Do not "fix" this casually without retesting in game.

## Release Package Behavior

Inside the zip, user entry points are:

```text
CHECK_ENV.bat
INSTALL_CLEAN.bat
INSTALL.bat
ROLLBACK.bat
```

Recommended tester flow:

```text
1. Extract to a short path, for example C:\hiraeth_fengbei_v01
2. Run CHECK_ENV.bat
3. If there are no [FAIL] lines, run INSTALL_CLEAN.bat
4. Restart MonkeyBusiness
5. Start the game with contents\start_fengbei_layeredfs.bat
```

`CHECK_ENV.bat` is read-only. It should not modify game files or MB files.

`INSTALL_CLEAN.bat`:

- backs up and clears `contents/data_mods`
- installs `contents/data_mods/fbfn`
- backs up and replaces `contents/ifs_hook.dll`
- tries to unblock `ifs_hook.dll` if Windows marked it as downloaded
- generates `contents/start_fengbei_layeredfs.bat`
- merges index `701` into MB `modules/nostalgia/music_list.xml`
- builds a full game-side overlay `fbfn/data_Op3/sound/music_list.xml`
- patches MB `op3_common.py` revision/release code and missing field defaults
- writes rollback state to `MonkeyBusiness-main/fengbei_fbfn_install_state.json`

`ROLLBACK.bat` restores from the latest install state.

Diagnostic logs are written inside the extracted package:

```text
logs/check_env_*.log
logs/install_*.log
logs/rollback_*.log
```

If a tester reports failure, ask for:

```text
logs/check_env_*.log
logs/install_*.log
MonkeyBusiness-main/fengbei_fbfn_install_state.json
MonkeyBusiness-main/fengbei_fbfn_backup/<timestamp>
MonkeyBusiness log
game log
```

## Repository Reality For Mac Development

Important: `work/` is ignored by Git except for selected forced files.

The tracked release artifact is:

```text
work/hiraeth_fanmade_fengbei_v0.1_test.zip
```

The unpacked package source directory under:

```text
work/hiraeth_fanmade_fengbei_v0.1_test/
```

is local working output and may not exist after a fresh Mac clone.

On Mac, if Codex needs to inspect the package internals, extract it first:

```bash
python3 -m zipfile -e work/hiraeth_fanmade_fengbei_v0.1_test.zip /tmp/hiraeth_pkg
```

Recommended first structural cleanup after development resumes:

```text
packages/fengbei_v0.1_test/
scripts/build_release_zip.py
```

Move the package source out of ignored `work/` and generate the zip from tracked source. Until that happens, avoid editing only the extracted `work/` package and forgetting to rebuild/force-add the zip.

## Important Documents

Read in this order:

```text
README.md
docs/mac_codex_handoff.md
docs/release_fengbei_v0.1_test.md
docs/ifs_layeredfs_notes.md
docs/music_list_notes.md
docs/audio_bank_notes.md
docs/chart_xml_requirements.md
```

Use `docs/chart_xml_requirements.md` as reference only for now. Do not start new chart format work until the chart editor/chart format team returns results.

## Important Scripts

Inspection:

```text
scripts/inspect_folder.py
scripts/inspect_banks.py
scripts/inspect_music_list.py
scripts/inspect_xml_structure.py
validate_song.py
```

Music list generation:

```text
scripts/create_music_list_entry.py
scripts/create_music_list_entry_raw.py
```

LayeredFS assembly:

```text
scripts/assemble_layeredfs_song_mod.py
```

Chart cleanup:

```text
scripts/normalize_chart_xml.py
```

Audio helpers:

```text
scripts/xwb_to_wav.py
scripts/wav_to_xwb.py
scripts/resample_wav.py
scripts/trim_wav.py
scripts/patch_bank_names.py
```

## What Not To Change Casually

Do not casually change these without a Windows retest:

- `index=701`
- `basename=M_T0169_filenameonly`
- the internal XSB/XWB bank names that still reference `M_T0168_marigoldjazzy`
- `ifs_hook.dll` behavior
- generated launch command `spice64.exe -k ifs_hook.dll`
- `op3_common.py` patch shape
- songlist revision/release code defaults:

```text
revision=22621M
release_code=2024123100
```

Do not treat `.merged.xml` alone as sufficient in all environments. The current installer also writes a full overlay `data_Op3/sound/music_list.xml` because some tests needed stronger songlist alignment.

## Current Limits

The current package is a single-song test release, not a general-purpose installer.

Known limits:

- no global song index allocation
- no multi-song manifest handling
- no conflict resolution between fanmade packages
- no cross-version PAN adaptation
- no complete XSB rebuild
- XWB generation is still a limited PCM workflow
- Mac cannot do final game validation

For now, Mac development should focus on installer/package reliability and documentation, not chart internals.

## Recommended Next Work After Pause

Priority 1: turn the release package into tracked source.

Suggested structure:

```text
packages/fengbei_v0.1_test/
  CHECK_ENV.bat
  INSTALL.bat
  INSTALL_CLEAN.bat
  ROLLBACK.bat
  check_env.ps1
  install_fengbei.ps1
  install_fengbei_clean.ps1
  rollback_fengbei.ps1
  manifest.json
  README.md
  VERSION.txt
  assets/

scripts/build_release_zip.py
```

The build script should:

- delete old generated zip
- create `work/hiraeth_fanmade_fengbei_v0.1_test.zip`
- include the top-level folder `hiraeth_fanmade_fengbei_v0.1_test/`
- print SHA256
- run `python3 -m zipfile -t`

Priority 2: improve installer checks without changing install behavior.

Add checks for:

- whether `spice64.exe` is currently running
- whether MonkeyBusiness is currently running
- whether target paths are too long
- whether `data_mods` contains known conflicting root-style songlists
- whether MB `op3_common.py` patch markers are already present

Priority 3: prepare a tester feedback template.

The template should ask testers for:

```text
Windows version
game path
MonkeyBusiness path
CHECK_ENV result
INSTALL_CLEAN result
whether MB starts after install
whether the generated start bat starts the game
whether the song appears
preview/title/jacket/gameplay result
logs/check_env_*.log
logs/install_*.log
game log
MB log
```

## Suggested Prompt For Mac Codex

When continuing from a fresh Mac clone, start with:

```text
Read docs/mac_codex_handoff.md and README.md first. Do not modify chart logic. Help me move the Fengbei v0.1 test package source out of ignored work/ into tracked packages/fengbei_v0.1_test, add scripts/build_release_zip.py, rebuild the zip, and keep the output path work/hiraeth_fanmade_fengbei_v0.1_test.zip.
```

If investigating a tester failure:

```text
Read docs/mac_codex_handoff.md and docs/release_fengbei_v0.1_test.md. Analyze these logs and identify whether the failure is environment check, install write, MonkeyBusiness songlist, ifs_hook launch, or in-game asset loading. Do not change chart XML unless the logs specifically point to chart loading.
```

## Safety Rules

- Do not commit original game files.
- Do not commit tester logs if they contain personal paths unless sanitized.
- Do not commit raw copyrighted music or extracted game assets beyond the already tracked test release artifact policy.
- Keep `master` for tested or clearly documented changes.
- Use feature branches for risky installer refactors.
- Every release zip change must include a new SHA256 in the final report.

