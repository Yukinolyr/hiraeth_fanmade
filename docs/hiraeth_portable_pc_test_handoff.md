# Hiraeth Portable PC Test Handoff

Date: 2026-06-25

This document records the current Hiraeth portable runtime state for testing on another Windows PC or cabinet-like environment.

## Current Local Build

Verified local source folder:

```text
E:\hiraeth
```

Portable package generated from that source:

```text
\\wsl.localhost\Ubuntu\home\yukino\code\nostalgia_fanmade\work\arcade_migration\hiraeth_portable_runtime_20260625_022057
```

ZIP package:

```text
\\wsl.localhost\Ubuntu\home\yukino\code\nostalgia_fanmade\work\arcade_migration\hiraeth_portable_runtime_20260625_022057.zip
```

Size:

```text
unpacked: 3.7GB
zip:      2.3GB
```

The package itself is generated output and is not committed to Git.

## Runtime Strategy

MonkeyBusiness no longer depends on system Python, Anaconda, or `.venv`.

The portable package includes:

```text
runtime\python\python.exe
```

Current runtime version:

```text
Python 3.8.10 x64 embeddable
```

This was chosen instead of Python 3.12 to improve compatibility with older Windows systems.

Important dependency adjustments:

- `anyio` is pinned to `4.5.2` because later versions require newer Python.
- `websockets` is pinned to `13.1` because 14.x requires Python 3.9+.
- `kbinxml` is pure Python but needed Python 3.8 compatibility patches for modern type annotations.

## Startup Chain

Use:

```text
START_HIRAETH_PORTABLE.bat
```

It calls:

```text
contents\start.bat
```

The game start script launches MonkeyBusiness through:

```text
MonkeyBusiness-main\start_runtime.bat
```

Then it starts the game with:

```bat
spice64.exe -url http://localhost:8000/core -urlslash 1 -k ifs_hook.dll
```

This means `contents\prop\ea3-config.xml` may still contain an external service URL, but the runtime server is selected by the SpiceTools `-url` argument.

## Excluded Personal Or Machine State

The portable package intentionally excludes:

```text
contents\card0.txt
contents\dev\nvram
MonkeyBusiness-main\db.json
MonkeyBusiness-main\fengbei_fbfn_install_state.json
contents\log.txt
.venv
```

The target PC should generate or configure its own local player and machine state.

## Verified Custom Songs

The current playable Hanon songs are:

```text
m_c0035_hanon_120
m_c0036_hanon_108
m_c0037_hanon_90
m_c0038_hanon_78
```

Expected displayed levels:

```text
120 bpm: 7 / 9 / 12 / REAL 3
108 bpm: 7 / 9 / 12 / REAL 3
90 bpm:  7 / 9 / 12 / REAL 2
78 bpm:  7 / 9 / 12 / REAL 2
```

The package includes Hanon jackets and music-select text textures under:

```text
contents\data_mods\hanon_visuals
```

## Validation Already Performed

On the source PC:

- `E:\hiraeth\runtime\python\python.exe -V` returns `Python 3.8.10`.
- MB imports pass for `fastapi`, `uvicorn`, `kbinxml`, `Cryptodome`, `tinydb`, `ujson`, `lxml`, `watchfiles`, `websockets`, and `exceptiongroup`.
- MB `/config` responds through `http://localhost:8000/config`.
- Full game startup reaches `op3_common.get_music_info`.
- `eacoin`, `cardmng`, and music select flow were observed in logs before the Python 3.8 switch.
- After game exit, `spice64`, runtime Python, and port `8000` are cleaned up.

Portable package manifest checks:

- `runtime/python/python.exe` included.
- `contents/start.bat` included.
- `MonkeyBusiness-main/start_runtime.bat` included.
- `contents/card0.txt` excluded.
- `contents/dev/nvram` excluded.
- `MonkeyBusiness-main/db.json` excluded.

## Test Steps On Another PC

1. Extract the ZIP to a short ASCII path, for example:

```text
C:\hiraeth
```

2. Run:

```text
START_HIRAETH_PORTABLE.bat
```

3. Confirm that a MonkeyBusiness console opens and the game starts.

4. In game, check:

- no connection error
- can enter mode/select flow
- can reach music select
- four Hanon songs are visible
- preview audio works
- entering a Hanon chart does not hang
- song audio plays
- exiting the game also closes MB

## If It Fails

If MB does not start:

- Check whether `runtime\python\python.exe` runs.
- Check for missing DLL errors. Older Windows may need UCRT/VC runtime.
- Check whether port `8000` is already occupied.

If the game reports connection problems:

- Confirm MB is listening on port `8000`.
- Confirm `contents\start.bat` still contains `-url http://localhost:8000/core -urlslash 1`.

If the game starts but graphics/audio behave differently:

- Run `contents\spicecfg.exe` on the target PC.
- Reconfigure display, input, audio, and card options for that machine.
- Some SpiceTools screen resize settings are stored in the Windows user profile and are not part of this package.

If the target is an old cabinet OS:

- Confirm it is 64-bit Windows.
- Confirm `MF.dll`, `MFPlat.dll`, and `MFReadWrite.dll` exist. Missing Media Foundation components can affect SpiceTools/game startup.
- Use `tools\collect_arcade_info.bat` and compare the report before changing cabinet files.

## GitHub Notes

This repository stores:

- technical documentation
- packaging and migration scripts
- conversion and generation scripts
- package build logic

It does not store:

- the full `E:\hiraeth` runtime
- generated portable packages
- personal card/player database state
- large game resource files
