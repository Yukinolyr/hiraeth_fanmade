param(
  [string]$OutputDir = ".\arcade_info"
)

$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

function Write-Text {
  param([string]$Name, [object]$Value)
  $path = Join-Path $OutputDir $Name
  $Value | Out-File -FilePath $path -Encoding UTF8 -Width 4096
}

Write-Text "ps_version.txt" $PSVersionTable

try {
  Write-Text "computer_info.txt" (Get-ComputerInfo)
} catch {
  Write-Text "computer_info_error.txt" $_
}

try {
  Write-Text "os_cim.txt" (Get-CimInstance Win32_OperatingSystem | Format-List *)
} catch {
  Write-Text "os_wmi.txt" (Get-WmiObject Win32_OperatingSystem | Format-List *)
}

foreach ($name in @(
  "Win32_ComputerSystem",
  "Win32_Processor",
  "Win32_VideoController",
  "Win32_SoundDevice",
  "Win32_DesktopMonitor",
  "Win32_PnPEntity",
  "Win32_LogicalDisk",
  "Win32_DiskDrive",
  "Win32_NetworkAdapterConfiguration"
)) {
  try {
    Write-Text "$name.txt" (Get-WmiObject $name | Format-List *)
  } catch {
    Write-Text "$name.error.txt" $_
  }
}

try {
  Add-Type -AssemblyName System.Windows.Forms
  $screens = [System.Windows.Forms.Screen]::AllScreens | ForEach-Object {
    [PSCustomObject]@{
      DeviceName = $_.DeviceName
      Primary = $_.Primary
      Bounds = $_.Bounds.ToString()
      WorkingArea = $_.WorkingArea.ToString()
      BitsPerPixel = $_.BitsPerPixel
    }
  }
  Write-Text "screens_dotnet.txt" ($screens | Format-List *)
} catch {
  Write-Text "screens_dotnet_error.txt" $_
}

try {
  Write-Text "installed_programs_hklm.txt" (
    Get-ItemProperty "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*" |
      Select-Object DisplayName, DisplayVersion, Publisher, InstallDate |
      Sort-Object DisplayName |
      Format-Table -AutoSize
  )
} catch {
  Write-Text "installed_programs_hklm_error.txt" $_
}

try {
  Write-Text "services.txt" (Get-Service | Sort-Object Name | Format-Table -AutoSize)
} catch {
  Write-Text "services_error.txt" $_
}

try {
  Write-Text "processes.txt" (Get-Process | Sort-Object ProcessName | Format-Table -AutoSize)
} catch {
  Write-Text "processes_error.txt" $_
}

try {
  Write-Text "powercfg_q.txt" (powercfg /q)
} catch {
  Write-Text "powercfg_q_error.txt" $_
}

try {
  Write-Text "drive_roots.txt" (
    Get-PSDrive -PSProvider FileSystem | ForEach-Object {
      $root = $_.Root
      "===== $root ====="
      if (Test-Path $root) {
        Get-ChildItem -Force $root | Select-Object Mode, Length, LastWriteTime, Name | Format-Table -AutoSize | Out-String -Width 4096
      }
    }
  )
} catch {
  Write-Text "drive_roots_error.txt" $_
}

try {
  Compress-Archive -Force -Path (Join-Path $OutputDir "*") -DestinationPath "$OutputDir.zip"
} catch {
  Write-Text "zip_error.txt" $_
}
