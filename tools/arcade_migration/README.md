# Arcade Migration Tools

This folder contains tools for moving the verified `E:\hiraeth` build to a Windows arcade PC.

## Collect Cabinet Information

Copy these two files to a USB drive:

```text
collect_arcade_info.bat
collect_arcade_info.ps1
```

On the cabinet, run:

```text
collect_arcade_info.bat
```

It creates an `arcade_info_<computer>_<timestamp>` folder and, if PowerShell supports it, a zip next to that folder.

The report includes:

- Windows version and architecture
- CPU, RAM, GPU, sound devices
- display resolution and refresh data when available
- drives and free space
- network configuration
- running processes and services
- DirectX diagnostic output

## Package Runtime

On the development PC/WSL side:

```bash
python3 tools/arcade_migration/package_hiraeth_runtime.py
```

The output is written under:

```text
work/arcade_migration/
```

The package excludes logs, caches, historical backups, and personal MonkeyBusiness database state.
