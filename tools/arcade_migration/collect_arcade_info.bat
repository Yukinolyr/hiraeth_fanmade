@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "STAMP=%DATE:/=-%_%TIME::=-%"
set "STAMP=%STAMP: =0%"
set "OUT_DIR=%SCRIPT_DIR%arcade_info_%COMPUTERNAME%_%STAMP%"
mkdir "%OUT_DIR%" >nul 2>nul

echo Collecting arcade PC information...
echo Output: "%OUT_DIR%"

ver > "%OUT_DIR%\windows_ver.txt" 2>&1
systeminfo > "%OUT_DIR%\systeminfo.txt" 2>&1
hostname > "%OUT_DIR%\hostname.txt" 2>&1
whoami /all > "%OUT_DIR%\whoami_all.txt" 2>&1
set > "%OUT_DIR%\environment.txt" 2>&1
ipconfig /all > "%OUT_DIR%\ipconfig_all.txt" 2>&1
route print > "%OUT_DIR%\route_print.txt" 2>&1
netstat -ano > "%OUT_DIR%\netstat_ano.txt" 2>&1
tasklist /v > "%OUT_DIR%\tasklist_v.txt" 2>&1
driverquery /v > "%OUT_DIR%\driverquery_v.txt" 2>&1
wmic os get Caption,Version,BuildNumber,OSArchitecture,InstallDate /format:list > "%OUT_DIR%\wmic_os.txt" 2>&1
wmic computersystem get Manufacturer,Model,SystemType,TotalPhysicalMemory /format:list > "%OUT_DIR%\wmic_computersystem.txt" 2>&1
wmic cpu get Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed /format:list > "%OUT_DIR%\wmic_cpu.txt" 2>&1
wmic path win32_VideoController get Name,DriverVersion,AdapterRAM,CurrentHorizontalResolution,CurrentVerticalResolution,CurrentRefreshRate /format:list > "%OUT_DIR%\wmic_video.txt" 2>&1
wmic sounddev get Name,Manufacturer,Status /format:list > "%OUT_DIR%\wmic_sound.txt" 2>&1
wmic logicaldisk get Caption,Description,FileSystem,FreeSpace,Size,VolumeName /format:list > "%OUT_DIR%\wmic_disks.txt" 2>&1
wmic path win32_PnPEntity get Name,PNPClass,Status,DeviceID /format:list > "%OUT_DIR%\wmic_pnp.txt" 2>&1

if exist "%SystemRoot%\System32\dxdiag.exe" (
  "%SystemRoot%\System32\dxdiag.exe" /t "%OUT_DIR%\dxdiag.txt" >nul 2>nul
  timeout /t 8 /nobreak >nul 2>nul
)

if exist "%SCRIPT_DIR%collect_arcade_info.ps1" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%collect_arcade_info.ps1" -OutputDir "%OUT_DIR%" > "%OUT_DIR%\powershell_collect_stdout.txt" 2>&1
) else (
  echo collect_arcade_info.ps1 not found > "%OUT_DIR%\powershell_collect_stdout.txt"
)

if exist C:\ (
  dir C:\ /a > "%OUT_DIR%\dir_C_root.txt" 2>&1
)
if exist D:\ (
  dir D:\ /a > "%OUT_DIR%\dir_D_root.txt" 2>&1
)
if exist E:\ (
  dir E:\ /a > "%OUT_DIR%\dir_E_root.txt" 2>&1
)

echo.
echo Done.
echo Please copy this folder back for analysis:
echo "%OUT_DIR%"
pause
