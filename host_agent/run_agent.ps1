# Aethera AI — Host Agent Launcher
# Run from project root: powershell -ExecutionPolicy Bypass -File host_agent/run_agent.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Aethera AI — Host Agent" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $version = & $cmd --version 2>&1
        if ($version -match "3\.(\d+)" -and [int]$matches[1] -ge 10) {
            $pythonCmd = $cmd
            Write-Host "Using Python: $version" -ForegroundColor Green
            break
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Host "ERROR: Python 3.10+ not found. Install from https://python.org" -ForegroundColor Red
    exit 1
}

# Check dependencies
Write-Host "Checking dependencies..." -ForegroundColor Yellow
$missing = @()
foreach ($pkg in @("websockets", "psutil", "pydantic", "aiofiles")) {
    $result = & $pythonCmd -c "import $pkg; print('ok')" 2>&1
    if ($result -ne "ok") {
        $missing += $pkg
    }
}

if ($missing.Count -gt 0) {
    Write-Host "Installing missing dependencies: $($missing -join ', ')" -ForegroundColor Yellow
    & $pythonCmd -m pip install -r "$PSScriptRoot\requirements.txt" --quiet
}

# Check optional dependencies
foreach ($pkg in @("pyautogui", "GPUtil", "pytesseract", "pyperclip", "playwright")) {
    $result = & $pythonCmd -c "import $pkg" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Optional: $pkg not installed (some features may be unavailable)" -ForegroundColor DarkGray
    }
}

# Set environment variables from .env if it exists
$envFile = Join-Path $PSScriptRoot ".." ".env"
if (Test-Path $envFile) {
    Write-Host "Loading environment from .env" -ForegroundColor Green
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^([^#][^=]+)=(.*)$") {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
}

# Start the host agent
Write-Host ""
Write-Host "Starting Host Agent..." -ForegroundColor Green
Write-Host "  Orchestrator URL: $env:AETHERA_ORCHESTRATOR_URL" -ForegroundColor Gray
Write-Host "  Agent ID: $env:AETHERA_AGENT_ID" -ForegroundColor Gray
Write-Host ""

& $pythonCmd -m host_agent.agent