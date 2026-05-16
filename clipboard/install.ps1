<#
.SYNOPSIS
    Install Aethera Clipboard Agent as a Windows startup application.

.DESCRIPTION
    Creates a scheduled task that launches the clipboard agent at login,
    and adds a shortcut to the Windows startup folder.
    The agent runs in the system tray monitoring for healthcare codes.

.NOTES
    Requires: Python 3.10+, pip, the clipboard\requirements.txt packages
    Run as: powershell -ExecutionPolicy Bypass -File install.ps1
#>

param(
    [string]$InstallDir = "$env:LOCALAPPDATA\AetheraAI\ClipboardAgent",
    [switch]$Uninstall,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$TaskName = "AetheraClipboardAgent"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

function Write-Status($msg) {
    if (-not $Quiet) { Write-Host "[Aethera] $msg" -ForegroundColor Cyan }
}

function Write-Success($msg) {
    if (-not $Quiet) { Write-Host "[Aethera] $msg" -ForegroundColor Green }
}

function Write-Warn($msg) {
    if (-not $Quiet) { Write-Host "[Aethera] WARNING: $msg" -ForegroundColor Yellow }
}

function Write-Err($msg) {
    if (-not $Quiet) { Write-Host "[Aethera] ERROR: $msg" -ForegroundColor Red }
}

# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------

if ($Uninstall) {
    Write-Status "Uninstalling Aethera Clipboard Agent..."

    # Remove scheduled task
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Success "Removed scheduled task: $TaskName"
    }

    # Remove startup shortcut
    $startupFolder = [System.IO.Path]::Combine(
        $env:APPDATA, "Microsoft\Windows\Start Menu\Programs\Startup"
    )
    $shortcutPath = Join-Path $startupFolder "Aethera Clipboard Agent.lnk"
    if (Test-Path $shortcutPath) {
        Remove-Item $shortcutPath -Force
        Write-Success "Removed startup shortcut"
    }

    # Optionally remove install directory
    if (Test-Path $InstallDir) {
        $answer = if ($Quiet) { "N" } else {
            Read-Host "Remove install directory $InstallDir? (Y/N)"
        }
        if ($answer -eq "Y" -or $answer -eq "y") {
            Remove-Item $InstallDir -Recurse -Force
            Write-Success "Removed install directory"
        }
    }

    Write-Success "Uninstall complete."
    exit 0
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

Write-Status "Aethera Clipboard Agent Installer"
Write-Status "================================"

# Check Python
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $version = & $cmd --version 2>&1
        if ($version -match "3\.(\d+)") {
            $minorVersion = [int]$matches[1]
            if ($minorVersion -ge 10) {
                $pythonCmd = $cmd
                Write-Success "Found Python: $version (using '$cmd')"
                break
            }
        }
    }
    catch { }
}

if (-not $pythonCmd) {
    Write-Err "Python 3.10+ not found. Install from https://python.org"
    exit 1
}

# Check pip
try {
    & $pythonCmd -m pip --version | Out-Null
    Write-Success "pip is available"
}
catch {
    Write-Err "pip not found. Install pip first."
    exit 1
}

# ---------------------------------------------------------------------------
# Install directory setup
# ---------------------------------------------------------------------------

Write-Status "Setting up install directory: $InstallDir"

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    Write-Success "Created install directory"
}

# Copy clipboard agent files
$sourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$filesToCopy = @(
    "clipboard_agent.py",
    "patterns.py",
    "requirements.txt"
)

foreach ($file in $filesToCopy) {
    $src = Join-Path $sourceDir $file
    $dst = Join-Path $InstallDir $file
    if (Test-Path $src) {
        Copy-Item $src $dst -Force
        Write-Success "Copied $file"
    }
    else {
        Write-Warn "Source file not found: $src"
    }
}

# ---------------------------------------------------------------------------
# Install Python dependencies
# ---------------------------------------------------------------------------

Write-Status "Installing Python dependencies..."

$requirementsPath = Join-Path $InstallDir "requirements.txt"
if (Test-Path $requirementsPath) {
    & $pythonCmd -m pip install -r $requirementsPath --quiet --disable-pip-version-check
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Dependencies installed"
    }
    else {
        Write-Warn "Some dependencies may not have installed correctly"
    }
}
else {
    Write-Warn "requirements.txt not found at $requirementsPath"
    Write-Status "Installing dependencies individually..."
    & $pythonCmd -m pip install pyperclip pystray Pillow requests --quiet --disable-pip-version-check
}

# ---------------------------------------------------------------------------
# Create launcher script
# ---------------------------------------------------------------------------

Write-Status "Creating launcher script..."

$launcherScript = @"
@echo off
cd /d "$InstallDir"
$pythonCmd clipboard_agent.py
"@

$launcherPath = Join-Path $InstallDir "launch.bat"
Set-Content -Path $launcherPath -Value $launcherScript -Encoding ASCII
Write-Success "Created launcher: $launcherPath"

# Also create a VBS wrapper to run silently (no console window)
$vbsScript = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "$InstallDir"
WshShell.Run """$pythonCmd"" clipboard_agent.py", 0, False
"@

$vbsPath = Join-Path $InstallDir "launch_silent.vbs"
Set-Content -Path $vbsPath -Value $vbsScript -Encoding ASCII
Write-Success "Created silent launcher: $vbsPath"

# ---------------------------------------------------------------------------
# Create scheduled task (runs at logon)
# ---------------------------------------------------------------------------

Write-Status "Creating scheduled task..."

# Remove existing task if present
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Status "Removed existing scheduled task"
}

# Get full path to Python executable
$pythonExe = & $pythonCmd -c "import sys; print(sys.executable)" 2>&1
if (-not (Test-Path $pythonExe)) {
    Write-Warn "Could not determine Python executable path, using '$pythonCmd'"
    $pythonExe = $pythonCmd
}

$action = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument "clipboard_agent.py" `
    -WorkingDirectory $InstallDir

$trigger = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Aethera AI Clipboard Agent - Monitors clipboard for healthcare codes" | Out-Null

Write-Success "Created scheduled task: $TaskName (triggers at logon)"

# ---------------------------------------------------------------------------
# Add to startup folder (belt and suspenders)
# ---------------------------------------------------------------------------

Write-Status "Adding to startup folder..."

$startupFolder = [System.IO.Path]::Combine(
    $env:APPDATA, "Microsoft\Windows\Start Menu\Programs\Startup"
)
$shortcutPath = Join-Path $startupFolder "Aethera Clipboard Agent.lnk"

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $vbsPath
$shortcut.WorkingDirectory = $InstallDir
$shortcut.Description = "Aethera AI Clipboard Agent"
$shortcut.IconLocation = "shell32.dll,13"  # Clipboard icon
$shortcut.Save()

Write-Success "Created startup shortcut: $shortcutPath"

# ---------------------------------------------------------------------------
# Verify installation
# ---------------------------------------------------------------------------

Write-Status "Verifying installation..."

$issues = @()

# Verify files
foreach ($file in $filesToCopy) {
    $path = Join-Path $InstallDir $file
    if (-not (Test-Path $path)) {
        $issues += "Missing file: $file"
    }
}

# Verify scheduled task
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $task) {
    $issues += "Scheduled task not found"
}

# Verify startup shortcut
if (-not (Test-Path $shortcutPath)) {
    $issues += "Startup shortcut not found"
}

# Verify Python can import required packages
$importCheck = & $pythonCmd -c "import pyperclip, pystray, PIL, requests; print('OK')" 2>&1
if ($importCheck -notmatch "OK") {
    $issues += "Python packages not fully installed"
}

if ($issues.Count -eq 0) {
    Write-Success ""
    Write-Success "========================================="
    Write-Success " Aethera Clipboard Agent installed!       "
    Write-Success "========================================="
    Write-Success ""
    Write-Success "Install location: $InstallDir"
    Write-Success "Scheduled task:   $TaskName (runs at logon)"
    Write-Success "Startup shortcut: $shortcutPath"
    Write-Success ""
    Write-Status "The agent will start automatically at next login."
    Write-Status "To start now, run: $launcherPath"
    Write-Status "To uninstall, run:  .\install.ps1 -Uninstall"
}
else {
    Write-Warn ""
    Write-Warn "Installation completed with issues:"
    foreach ($issue in $issues) {
        Write-Err "  - $issue"
    }
    Write-Status ""
    Write-Status "The agent may not work correctly until these are resolved."
    exit 1
}