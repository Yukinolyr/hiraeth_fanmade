# Fengbei v0.1 Test Release

Package file:

```text
work/hiraeth_fanmade_fengbei_v0.1_test.zip
```

## Purpose

This is the first cleaned-up public test package for the Fengbei `fbfn` import workflow.

It is intended to verify that a MonkeyBusiness user can add one new test song through:

- `contents/data_mods`
- `ifs_hook.dll`
- `spice64.exe -k ifs_hook.dll`
- MonkeyBusiness `modules/nostalgia/music_list.xml`
- MonkeyBusiness `modules/nostalgia/op3_common.py`

## Target Environment

Verified target:

```text
NOSTALGIA op.3 PAN
music_list revision: 22621M
music_list release_code: 2024123100
MonkeyBusiness modules/nostalgia
```

## Included Song

```text
index: 701
basename: M_T0169_filenameonly
title: Fengbei Filename Test
data_mods package: fbfn
```

## User Entry Points

Recommended clean install:

```text
INSTALL_CLEAN.bat
```

Recommended extraction path:

```text
C:\hiraeth_fengbei_v01
```

Keeping the extraction path short reduces the chance of Windows path-length copy failures.

Normal install:

```text
INSTALL.bat
```

Rollback:

```text
ROLLBACK.bat
```

Generated game launch file:

```text
contents/start_fengbei_layeredfs.bat
```

The generated launch file starts the game as:

```text
spice64.exe -k ifs_hook.dll
```

Directly launching `spice64.exe` will not load the `data_mods` song.

The installer accepts pasted paths with or without surrounding English quotes.

## Installer Behavior

The clean installer:

- Backs up and clears the target `contents/data_mods`.
- Installs `contents/data_mods/fbfn`.
- Backs up and replaces `contents/ifs_hook.dll`.
- Attempts to unblock `ifs_hook.dll` if Windows marks it as downloaded from the internet.
- Generates `contents/start_fengbei_layeredfs.bat`.
- Initializes or merges MonkeyBusiness `modules/nostalgia/music_list.xml`.
- Merges Fengbei index `701` into the game-side overlay music list.
- Patches MonkeyBusiness `op3_common.py` revision and release code.
- Adds default handling for known missing songlist fields.
- Writes rollback state to `MonkeyBusiness-main/fengbei_fbfn_install_state.json`.

The normal installer keeps existing `contents/data_mods` and attempts to merge known root-style `music_list.xml` files if present.

## Verified Result

In the current test environment:

- The new song appears in the song list.
- Preview audio plays.
- Gameplay starts without freezing.
- Gameplay audio and chart work.
- Title image is shown.
- Jacket display works after songlist alignment.

## Known Limits

- This is a single-song test package.
- `index=701` is a test assignment, not a final global allocation policy.
- The package targets the verified PAN op.3 songlist version and MB module layout.
- The installer expects `spice64.exe` under the selected PAN `contents` folder.
- The installer expects MonkeyBusiness PAN files under `modules/nostalgia`.
- Multi-song support still needs manifest handling, index allocation, conflict checks, and version adaptation.
