# install.ps1 — per-user Windows installer for CodeBase.
#
# Windows analog of install.sh. Installs the PyInstaller-built executable into
# %LOCALAPPDATA%\Programs\CodeBase and creates Start Menu (and optional Desktop)
# shortcuts. No administrator rights required.
#
# Usage (from the repo root, after running `python build_windows.py`):
#   powershell -ExecutionPolicy Bypass -File install.ps1
#   powershell -ExecutionPolicy Bypass -File install.ps1 -Desktop      # also add a Desktop shortcut
#   powershell -ExecutionPolicy Bypass -File install.ps1 -Uninstall    # remove the install

[CmdletBinding()]
param(
    [switch]$Desktop,
    [switch]$Uninstall
)

$ErrorActionPreference = 'Stop'

$AppName    = 'CodeBase'
$SourceDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ExeSource  = Join-Path $SourceDir "dist\$AppName.exe"
$IconSource = Join-Path $SourceDir "assets\icon.ico"
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\$AppName"
$ExeTarget  = Join-Path $InstallDir "$AppName.exe"
$IconTarget = Join-Path $InstallDir 'icon.ico'

$StartMenuDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
$StartShortcut = Join-Path $StartMenuDir "$AppName.lnk"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) "$AppName.lnk"

function New-Shortcut {
    param([string]$LinkPath, [string]$TargetPath, [string]$IconPath)
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($LinkPath)
    $shortcut.TargetPath = $TargetPath
    $shortcut.WorkingDirectory = Split-Path -Parent $TargetPath
    if (Test-Path $IconPath) { $shortcut.IconLocation = $IconPath }
    $shortcut.Description = 'CodeBase Repository Manager'
    $shortcut.Save()
}

if ($Uninstall) {
    Write-Host "Uninstalling $AppName..."
    foreach ($lnk in @($StartShortcut, $DesktopShortcut)) {
        if (Test-Path $lnk) { Remove-Item $lnk -Force; Write-Host "  Removed $lnk" }
    }
    if (Test-Path $InstallDir) { Remove-Item $InstallDir -Recurse -Force; Write-Host "  Removed $InstallDir" }
    Write-Host "Done."
    return
}

if (-not (Test-Path $ExeSource)) {
    Write-Error "Executable not found at $ExeSource. Run 'python build_windows.py' first."
    exit 1
}

Write-Host "Installing $AppName to $InstallDir..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item $ExeSource $ExeTarget -Force
if (Test-Path $IconSource) { Copy-Item $IconSource $IconTarget -Force }

Write-Host "Creating Start Menu shortcut..."
New-Shortcut -LinkPath $StartShortcut -TargetPath $ExeTarget -IconPath $IconTarget

if ($Desktop) {
    Write-Host "Creating Desktop shortcut..."
    New-Shortcut -LinkPath $DesktopShortcut -TargetPath $ExeTarget -IconPath $IconTarget
}

Write-Host "`nSUCCESS! $AppName installed."
Write-Host "  Executable: $ExeTarget"
Write-Host "  Start Menu: $StartShortcut"
if ($Desktop) { Write-Host "  Desktop:    $DesktopShortcut" }
