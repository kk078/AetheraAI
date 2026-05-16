<#
.SYNOPSIS
    Aethera AI — Host Agent Installer
    Installs Python dependencies, downloads optional tools, and sets up
    the host agent to run as a Windows service or startup task.

.DESCRIPTION
    This script:
    1. Checks for Python 3.11+
    2. Creates a virtual environment
    3. Installs host_agent Python dependencies
    4. Optionally installs Tesseract OCR for screen capture
    5. Optionally installs Playwright Chromium for browser automation
    6. Registers the host agent as a Windows startup task

.EXAMPLE
    .\install_host_agent.ps1
    .\install_host_agent.ps1 -SkipBrowser -SkipOCR
    .\install_host_agent.ps1 -VenvPath C:\AetheraAI\host_agent\.venv
#>

param(
    [string]$VenvPath = "$PSScriptRoot\.venv",
    [switch]$SkipBrowser,
    [switch]$SkipOCR,
    [switch]$SkipStartup,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Aethera AI — Host Agent Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --- Step 1: Check Python ---
Write-Host "[1/6] Checking Python..." -ForegroundColor Yellow

$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $version = & $cmd --version 2>&1
        if ($version -match "3\.(\d+)") {
            $minor = [int]$Matches[1]
            if ($minor -ge 11) {
                $pythonCmd = $cmd
                Write-Host "  Found Python: $version" -ForegroundColor Green
                break
            }
        }
    } catch { }
}

if (-not $pythonCmd) {
    Write-Host "  ERROR: Python 3.11+ is required. Install from https://python.org" -ForegroundColor Red
    exit 1
}

# --- Step 2: Create virtual environment ---
Write-Host "[2/6] Setting up virtual environment..." -ForegroundColor Yellow

if (-not (Test-Path $VenvPath) -or $Force) {
    & $pythonCmd -m venv $VenvPath
    Write-Host "  Created venv at: $VenvPath" -ForegroundColor Green
} else {
    Write-Host "  Using existing venv at: $VenvPath" -ForegroundColor Green
}

$activateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
. $activateScript

# Upgrade pip
& python -m pip install --upgrade pip --quiet

# --- Step 3: Install Python dependencies ---
Write-Host "[3/6] Installing Python dependencies..." -ForegroundColor Yellow

$requirementsPath = Join-Path $PSScriptRoot "requirements.txt"
if (Test-Path $requirementsPath) {
    & python -m pip install -r $requirementsPath --quiet
    Write-Host "  Installed dependencies from requirements.txt" -ForegroundColor Green
} else {
    # Install individually if no requirements.txt
    $packages = @("websockets", "psutil", "GPUtil", "pydantic", "pyautogui", "Pillow", "pytesseract", "pyperclip", "playwright", "aiofiles")
    foreach ($pkg in $packages) {
        Write-Host "  Installing $pkg..." -ForegroundColor Gray
        & python -m pip install $pkg --quiet
    }
    Write-Host "  Installed all dependencies" -ForegroundColor Green
}

# --- Step 4: Install Tesseract OCR (optional) ---
if (-not $SkipOCR) {
    Write-Host "[4/6] Checking Tesseract OCR..." -ForegroundColor Yellow

    $tesseractFound = $false
    try {
        $tessVersion = & tesseract --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Tesseract OCR already installed" -ForegroundColor Green
            $tesseractFound = $true
        }
    } catch { }

    if (-not $tesseractFound) {
        Write-Host "  Tesseract OCR not found. Installing via winget..." -ForegroundColor Yellow
        try {
            & winget install --id UB-Mannheim.TesseractOCR --accept-source-agreements --accept-package-agreements
            Write-Host "  Tesseract OCR installed" -ForegroundColor Green
            Write-Host "  NOTE: You may need to restart your terminal for Tesseract to be in PATH" -ForegroundColor Yellow
        } catch {
            Write-Host "  Could not install Tesseract automatically. Install manually from:" -ForegroundColor Yellow
            Write-Host "  https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Yellow
            Write-Host "  Screen capture OCR will work without Tesseract (limited)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "[4/6] Skipping Tesseract OCR (-SkipOCR)" -ForegroundColor Gray
}

# --- Step 5: Install Playwright browser (optional) ---
if (-not $SkipBrowser) {
    Write-Host "[5/6] Installing Playwright Chromium..." -ForegroundColor Yellow
    try {
        & python -m playwright install chromium
        Write-Host "  Playwright Chromium installed" -ForegroundColor Green
    } catch {
        Write-Host "  Could not install Playwright browser. Browser automation may not work." -ForegroundColor Yellow
        Write-Host "  Run manually: python -m playwright install chromium" -ForegroundColor Yellow
    }
} else {
    Write-Host "[5/6] Skipping Playwright browser (-SkipBrowser)" -ForegroundColor Gray
}

# --- Step 6: Register startup task (optional) ---
if (-not $SkipStartup) {
    Write-Host "[6/6] Registering startup task..." -ForegroundColor Yellow

    $taskName = "AetheraHostAgent"
    $scriptPath = Join-Path $PSScriptRoot "run_agent.ps1"

    # Check if task already exists
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

    if ($existingTask -and -not $Force) {
        Write-Host "  Startup task '$taskName' already exists. Use -Force to recreate." -ForegroundColor Green
    } else {
        if ($existingTask) {
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        }

        $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
        $trigger = New-ScheduledTaskTrigger -AtLogOn
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable

        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Aethera AI Host Agent - PC Control Service" | Out-Null

        Write-Host "  Registered startup task: $taskName" -ForegroundColor Green
        Write-Host "  The host agent will start automatically when you log in." -ForegroundColor Green
    }
} else {
    Write-Host "[6/6] Skipping startup registration (-SkipStartup)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start the host agent manually:" -ForegroundColor White
Write-Host "  cd $PSScriptRoot" -ForegroundColor Cyan
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "  python -m host_agent.agent" -ForegroundColor Cyan
Write-Host ""
Write-Host "The agent will connect to the orchestrator at:" -ForegroundColor White
Write-Host "  ws://localhost:8000/api/pc/ws" -ForegroundColor Cyan
Write-Host ""
Write-Host "Set AETHERA_ORCHESTRATOR_URL env var to change the orchestrator address." -ForegroundColor Yellow