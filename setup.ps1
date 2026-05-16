# =============================================================================
# AETHERA AI — ONE-CLICK WINDOWS SETUP
# =============================================================================
# Run: .\setup.ps1
# Skip prerequisites: .\setup.ps1 -SkipPrerequisites
# Verbose output: .\setup.ps1 -Verbose
#
# This script:
#   1. Checks prerequisites (Docker, Node.js, Python, NVIDIA GPU)
#   2. Collects API keys and configuration
#   3. Creates .env file with all settings
#   4. Creates Docker volumes for persistent data
#   5. Builds Docker images (orchestrator, UI, voice)
#   6. Starts all 8 services
#   7. Pulls local Ollama models (qwen3.5:4b, gemma4:e2b, qwen3.5:9b, nomic-embed-text)
#   8. Verifies all services are healthy
# =============================================================================
param(
    [switch]$SkipPrerequisites,
    [switch]$Verbose,
    [switch]$SkipModelPull,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$PROJECT_ROOT = $PSScriptRoot.TrimEnd('\')

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
function Write-Header {
    param([string]$Text)
    Write-Host "`n" -NoNewline
    Write-Host ("=" * 72) -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host ("=" * 72) -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Text)
    Write-Host "[OK] " -ForegroundColor Green -NoNewline
    Write-Host $Text
}

function Write-Info {
    param([string]$Text)
    Write-Host "[INFO] " -ForegroundColor Yellow -NoNewline
    Write-Host $Text
}

function Write-Warn {
    param([string]$Text)
    Write-Host "[WARN] " -ForegroundColor DarkYellow -NoNewline
    Write-Host $Text
}

function Write-Err {
    param([string]$Text)
    Write-Host "[ERROR] " -ForegroundColor Red -NoNewline
    Write-Host $Text
}

function Write-Step {
    param([string]$Text)
    Write-Host "  -> " -ForegroundColor Cyan -NoNewline
    Write-Host $Text
}

function Test-Command {
    param([string]$Name)
    try {
        $cmd = Get-Command $Name -ErrorAction SilentlyContinue
        return $null -ne $cmd
    } catch {
        return $false
    }
}

function Wait-For-Url {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 120,
        [string]$Description = "service"
    )
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        try {
            $response = Invoke-WebRequest -Uri $Url -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                return $true
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    return $false
}

# =============================================================================
# BANNER
# =============================================================================
Clear-Host
Write-Host @"

    █████╗ ██╗   ██╗██████╗ ██████╗ ███████╗███████╗
   ██╔══██╗██║   ██║██╔══██╗██╔══██╗██╔════╝██╔════╝
   ███████║██║   ██║██████╔╝██████╔╝█████╗  ███████╗
   ██╔══██║██║   ██║██╔══██╗██╔══██╗██╔══╝  ╚════██║
   ██║  ██║╚██████╔╝██████╔╝██████╔╝███████╗███████║
   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝╚══════╝

   Personal Healthcare AI Super Agent
   Setting up Aethera AI...

"@ -ForegroundColor Cyan

# =============================================================================
# 1. PREREQUISITES CHECK
# =============================================================================
if (-not $SkipPrerequisites) {
    Write-Header "Step 1: Checking Prerequisites"

    # --- Docker Desktop ---
    Write-Step "Checking Docker Desktop..."
    try {
        $dockerVersion = docker --version 2>$null
        if (-not $dockerVersion) {
            Write-Err "Docker not found. Install Docker Desktop: https://docker.com/products/docker-desktop"
            exit 1
        }
        Write-Success "Docker installed: $dockerVersion"

        # Check Docker is running
        $dockerInfo = docker info 2>&1 | Select-String "Server Version"
        if (-not $dockerInfo) {
            Write-Err "Docker is not running. Start Docker Desktop and re-run."
            Write-Info "  Look for Docker Desktop in your Start menu or system tray."
            exit 1
        }
        Write-Success "Docker daemon is running"

        # Check Docker Compose v2
        $composeVersion = docker compose version 2>$null
        if (-not $composeVersion) {
            Write-Err "Docker Compose v2 not found. Update Docker Desktop."
            exit 1
        }
        Write-Success "Docker Compose: $composeVersion"
    } catch {
        Write-Err "Docker check failed: $_"
        exit 1
    }

    # --- WSL2 Backend ---
    Write-Step "Checking WSL2 backend..."
    try {
        $wslStatus = wsl --status 2>&1
        if ($wslStatus -match "default version.*2" -or $wslStatus -match "WSL 2") {
            Write-Success "WSL2 backend is active"
        } else {
            Write-Warn "Could not confirm WSL2 backend. Docker Desktop should use WSL2 by default."
            Write-Info "  Verify: Docker Desktop > Settings > General > 'Use the WSL 2 based engine'"
        }
    } catch {
        Write-Warn "WSL status check failed. This is OK if Docker is running correctly."
    }

    # --- NVIDIA GPU ---
    Write-Step "Checking NVIDIA GPU..."
    $gpuAvailable = $false
    try {
        $nvidiaSmi = nvidia-smi 2>$null
        if ($nvidiaSmi) {
            $gpuLine = $nvidiaSmi | Select-String "MX450|GeForce"
            if ($gpuLine) {
                Write-Success "NVIDIA GPU detected: $($gpuLine.Line.Trim())"
                $gpuAvailable = $true
            } else {
                Write-Warn "NVIDIA GPU found but may not be MX450"
                Write-Info "  GPU passthrough will still be configured."
                $gpuAvailable = $true
            }
        } else {
            Write-Warn "nvidia-smi not found. GPU passthrough may not work."
            Write-Info "  Install NVIDIA drivers: https://www.nvidia.com/drivers"
            Write-Info "  Ollama will fall back to CPU-only mode."
        }
    } catch {
        Write-Warn "NVIDIA GPU check failed: $_"
        Write-Info "  Ollama will use CPU-only mode (still functional, slower inference)."
    }

    # --- Node.js ---
    Write-Step "Checking Node.js..."
    $nodeFound = $false
    $nodePaths = @(
        "C:\Program Files\nodejs\node.exe",
        "C:\Program Files (x86)\nodejs\node.exe",
        "$env:LOCALAPPDATA\Programs\nodejs\node.exe"
    )
    foreach ($p in $nodePaths) {
        if (Test-Path $p) {
            $nodeVersion = & $p --version
            Write-Success "Node.js: $nodeVersion (at $p)"
            $nodeFound = $true
            break
        }
    }
    if (-not $nodeFound) {
        # Try PATH
        $nodeInPath = Get-Command node -ErrorAction SilentlyContinue
        if ($nodeInPath) {
            $nodeVersion = node --version
            Write-Success "Node.js: $nodeVersion"
            $nodeFound = $true
        }
    }
    if (-not $nodeFound) {
        Write-Err "Node.js not found. Install Node.js 18+: https://nodejs.org"
        exit 1
    }

    # --- Python ---
    Write-Step "Checking Python..."
    $pythonFound = $false
    $pythonPaths = @(
        "C:\Python311\python.exe",
        "C:\Python310\python.exe",
        "C:\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"
    )
    foreach ($p in $pythonPaths) {
        if (Test-Path $p) {
            $pyVer = & $p --version 2>&1
            Write-Success "Python: $pyVer"
            $pythonFound = $true
            break
        }
    }
    if (-not $pythonFound) {
        try {
            $pyVer = py -3 --version 2>$null
            if ($pyVer) {
                Write-Success "Python: $pyVer (via py launcher)"
                $pythonFound = $true
            }
        } catch {}
    }
    if (-not $pythonFound) {
        Write-Err "Python not found. Install Python 3.10+: https://python.org"
        exit 1
    }

    # --- Port availability ---
    Write-Step "Checking port availability..."
    $requiredPorts = @(3000, 4000, 6379, 8000, 8001, 8500, 8888, 11434)
    $portConflicts = @()
    foreach ($port in $requiredPorts) {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
        try {
            $listener.Start()
            $listener.Stop()
        } catch {
            $portConflicts += $port
        }
    }
    if ($portConflicts.Count -gt 0) {
        Write-Warn "Ports in use: $($portConflicts -join ', ')"
        Write-Info "  Stop conflicting services or change ports in docker-compose.yml"
        $continue = Read-Host "  Continue anyway? (y/N)"
        if ($continue -ne 'y' -and $continue -ne 'Y') {
            exit 1
        }
    } else {
        Write-Success "All required ports are available"
    }
}

# =============================================================================
# 2. CONFIGURATION
# =============================================================================
Write-Header "Step 2: Configuration"
Write-Host "Enter your configuration. Press Enter for defaults where applicable.`n"

# --- Ollama Cloud API Key (REQUIRED) ---
Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host "OLLAMA CLOUD API KEY [REQUIRED]" -ForegroundColor Yellow
Write-Host "Get your key: https://ollama.com/settings/api`n"
$OLLAMA_API_KEY = Read-Host "  Enter OLLAMA_API_KEY"
while ([string]::IsNullOrWhiteSpace($OLLAMA_API_KEY)) {
    Write-Err "OLLAMA_API_KEY is required for cloud models."
    $OLLAMA_API_KEY = Read-Host "  Enter OLLAMA_API_KEY"
}

# --- HuggingFace Token (OPTIONAL) ---
Write-Host "`n----------------------------------------" -ForegroundColor Gray
Write-Host "HUGGINGFACE TOKEN [OPTIONAL]" -ForegroundColor Yellow
Write-Host "Free tier works without token. Higher limits with free account."
$HF_TOKEN = Read-Host "  Enter HF_TOKEN (or press Enter to skip)"

# --- Cloudflare (OPTIONAL) ---
Write-Host "`n----------------------------------------" -ForegroundColor Gray
Write-Host "CLOUDFLARE CONFIGURATION [OPTIONAL]" -ForegroundColor Yellow
Write-Host "For remote access via Cloudflare Tunnel.`n"
$CLOUDFLARE_API_TOKEN = Read-Host "  Enter CLOUDFLARE_API_TOKEN (or press Enter to skip)"
$CLOUDFLARE_ACCOUNT_ID = ""
$CLOUDFLARE_DOMAIN = ""
if (-not [string]::IsNullOrWhiteSpace($CLOUDFLARE_API_TOKEN)) {
    $CLOUDFLARE_ACCOUNT_ID = Read-Host "  Enter CLOUDFLARE_ACCOUNT_ID"
    $CLOUDFLARE_DOMAIN = Read-Host "  Enter CLOUDFLARE_DOMAIN (e.g., aethera.yourdomain.com)"
}

# --- GitHub (OPTIONAL) ---
Write-Host "`n----------------------------------------" -ForegroundColor Gray
Write-Host "GITHUB TOKEN [OPTIONAL]" -ForegroundColor Yellow
$GITHUB_TOKEN = Read-Host "  Enter GITHUB_TOKEN (or press Enter to skip)"

# --- User Preferences ---
Write-Host "`n----------------------------------------" -ForegroundColor Gray
Write-Host "USER PREFERENCES" -ForegroundColor Yellow
$USER_TIMEZONE = Read-Host "  Enter USER_TIMEZONE (default: America/New_York)"
if ([string]::IsNullOrWhiteSpace($USER_TIMEZONE)) { $USER_TIMEZONE = "America/New_York" }

$USER_LOCATION = Read-Host "  Enter USER_LOCATION for weather (city or lat,lon)"
$DEFAULT_SPECIALIST = Read-Host "  Enter DEFAULT_SPECIALIST (default: general)"

# --- Generate encryption key ---
Write-Step "Generating encryption key..."
$ENCRYPTION_KEY = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})
Write-Success "Encryption key generated"

# =============================================================================
# 3. WRITE .ENV FILE
# =============================================================================
Write-Header "Step 3: Creating .env File"

$envContent = @"
# Aethera AI Environment Configuration
# Generated by setup.ps1 on $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

# === REQUIRED ===
ENCRYPTION_KEY=$ENCRYPTION_KEY
OLLAMA_API_KEY=$OLLAMA_API_KEY

# === OPTIONAL ===
HF_TOKEN=$HF_TOKEN
CLOUDFLARE_API_TOKEN=$CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID=$CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_DOMAIN=$CLOUDFLARE_DOMAIN
GITHUB_TOKEN=$GITHUB_TOKEN

# === PREFERENCES ===
USER_TIMEZONE=$USER_TIMEZONE
USER_LOCATION=$USER_LOCATION
DEFAULT_SPECIALIST=$DEFAULT_SPECIALIST

# === INTERNAL (do not change) ===
DATABASE_URL=sqlite+aiosqlite:///data/aethera.db
REDIS_URL=redis://redis:6379
CHROMADB_URL=http://chromadb:8000
LITELLM_URL=http://litellm:4000
OLLAMA_URL=http://ollama:11434
SEARXNG_URL=http://searxng:8080
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
"@

Set-Content -Path "$PROJECT_ROOT\.env" -Value $envContent -Encoding UTF8
Write-Success ".env file created at $PROJECT_ROOT\.env"

# =============================================================================
# 4. CREATE DOCKER VOLUMES
# =============================================================================
Write-Header "Step 4: Creating Docker Volumes"
Write-Step "Creating persistent volumes..."
$volumes = @("aethera-data", "ollama-models", "chroma-data", "redis-data", "searxng-data", "voice-models")
foreach ($vol in $volumes) {
    docker volume create $vol 2>$null | Out-Null
    Write-Success "Volume: $vol"
}

# =============================================================================
# 5. BUILD DOCKER IMAGES
# =============================================================================
if (-not $SkipBuild) {
    Write-Header "Step 5: Building Docker Images"

    Write-Step "Building orchestrator image..."
    docker compose -f "$PROJECT_ROOT\docker-compose.yml" -f "$PROJECT_ROOT\docker-compose.override.yml" build orchestrator
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to build orchestrator image."
        Write-Info "Check orchestrator/Dockerfile and requirements.txt for issues."
        exit 1
    }
    Write-Success "Orchestrator image built"

    Write-Step "Building UI image..."
    docker compose -f "$PROJECT_ROOT\docker-compose.yml" -f "$PROJECT_ROOT\docker-compose.override.yml" build ui
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Failed to build UI image."
        Write-Info "Check ui/Dockerfile and package.json for issues."
        exit 1
    }
    Write-Success "UI image built"

    Write-Step "Building voice image..."
    docker compose -f "$PROJECT_ROOT\docker-compose.yml" -f "$PROJECT_ROOT\docker-compose.override.yml" build voice
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Voice image build failed — voice features will be disabled."
        Write-Info "You can rebuild later with: docker compose build voice"
    } else {
        Write-Success "Voice image built"
    }
}

# =============================================================================
# 6. START SERVICES
# =============================================================================
Write-Header "Step 6: Starting Services"
Write-Step "Starting all services..."
docker compose -f "$PROJECT_ROOT\docker-compose.yml" -f "$PROJECT_ROOT\docker-compose.override.yml" up -d
if ($LASTEXITCODE -ne 0) {
    Write-Err "Failed to start services. Check Docker logs."
    Write-Info "Run: docker compose logs"
    exit 1
}
Write-Success "Docker Compose services started"

Write-Step "Waiting for services to initialize..."
Write-Info "This takes ~30-60 seconds on first start..."

# =============================================================================
# 7. PULL LOCAL OLLAMA MODELS
# =============================================================================
if (-not $SkipModelPull) {
    Write-Header "Step 7: Pulling Local Ollama Models"

    Write-Step "Waiting for Ollama to be ready..."
    $ollamaReady = Wait-For-Url -Url "http://localhost:11434/api/tags" -TimeoutSeconds 120 -Description "Ollama"
    if (-not $ollamaReady) {
        Write-Warn "Ollama did not become ready within 120 seconds."
        Write-Info "Models will be pulled on first use, or run: docker compose restart ollama"
    } else {
        Write-Success "Ollama is ready"

        $models = @(
            @{Name = "qwen3.5:4b"; Desc = "Primary local model (GPU)"}
            @{Name = "gemma4:e2b"; Desc = "Tool calling model (GPU)"}
            @{Name = "qwen3.5:9b"; Desc = "Smart fallback model (CPU)"}
            @{Name = "nomic-embed-text"; Desc = "Embedding model (CPU)"}
        )

        foreach ($model in $models) {
            Write-Step "Pulling $($model.Name) ($($model.Desc))..."
            try {
                $pullResult = docker exec aethera-ollama ollama pull $model.Name 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "$($model.Name) pulled"
                } else {
                    Write-Warn "Failed to pull $($model.Name). Will try on first use."
                    Write-Info "  Manual pull: docker exec aethera-ollama ollama pull $($model.Name)"
                }
            } catch {
                Write-Warn "Error pulling $($model.Name): $_"
                Write-Info "  Manual pull: docker exec aethera-ollama ollama pull $($model.Name)"
            }
        }
    }
}

# =============================================================================
# 8. VERIFY SERVICES
# =============================================================================
Write-Header "Step 8: Verifying Services"

$services = @(
    @{Name = "Redis";       Url = "http://localhost:6379";     Check = { try { redis-cli -h localhost ping 2>$null } catch { Invoke-WebRequest -Uri "http://localhost:6379" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop } }; Port = 6379}
    @{Name = "SearXNG";     Url = "http://localhost:8888/healthz"; Port = 8888}
    @{Name = "Ollama";      Url = "http://localhost:11434/api/tags"; Port = 11434}
    @{Name = "ChromaDB";    Url = "http://localhost:8001/api/v1/heartbeat"; Port = 8001}
    @{Name = "LiteLLM";     Url = "http://localhost:4000/health"; Port = 4000}
    @{Name = "Orchestrator"; Url = "http://localhost:8000/api/health"; Port = 8000}
    @{Name = "Voice";       Url = "http://localhost:8500/health"; Port = 8500}
    @{Name = "UI";          Url = "http://localhost:3000"; Port = 3000}
)

$allHealthy = $true
foreach ($svc in $services) {
    Write-Step "Checking $($svc.Name) on port $($svc.Port)..."
    try {
        $response = Invoke-WebRequest -Uri $svc.Url -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
        Write-Success "$($svc.Name) is healthy"
    } catch {
        Write-Warn "$($svc.Name) is not ready yet (this may take a few minutes on first start)"
        $allHealthy = $false
    }
}

# Show container status
Write-Host "`n" -NoNewline
Write-Step "Container status:"
docker compose -f "$PROJECT_ROOT\docker-compose.yml" -f "$PROJECT_ROOT\docker-compose.override.yml" ps

# =============================================================================
# SUMMARY
# =============================================================================
Write-Header "Setup Complete!"

$accessInfo = @"

  Aethera AI is ready!

  LOCAL URL:   http://localhost:3000   (Web UI)
  API URL:     http://localhost:8000   (REST API)
  Ollama API:  http://localhost:11434  (Local models)
  LiteLLM:     http://localhost:4000   (Model proxy)
  SearXNG:     http://localhost:8888   (Search engine)
  Redis:       localhost:6379
  ChromaDB:    http://localhost:8001   (Vector DB)
  Voice API:   http://localhost:8500   (STT/TTS)

"@

Write-Host $accessInfo -ForegroundColor Green

if (-not [string]::IsNullOrWhiteSpace($CLOUDFLARE_DOMAIN)) {
    Write-Host "  TUNNEL URL:  https://$CLOUDFLARE_DOMAIN`n" -ForegroundColor Green
}

if (-not $allHealthy) {
    Write-Host "  NOTE: Some services are still starting. Wait 1-2 minutes and check:" -ForegroundColor Yellow
    Write-Host "    docker compose ps" -ForegroundColor Yellow
    Write-Host "    docker compose logs <service-name>`n" -ForegroundColor Yellow
}

$nextSteps = @"
  NEXT STEPS:
    1. Open http://localhost:3000 in your browser
    2. Start chatting with Aethera!
    3. If GPU passthrough didn't work, models will run on CPU (slower but functional)

  USEFUL COMMANDS:
    Stop Aethera:    docker compose down
    Restart:         docker compose restart
    View logs:       docker compose logs -f
    View one service: docker compose logs -f orchestrator
    Pull models:     docker exec aethera-ollama ollama pull <model>
    Check health:    docker compose ps
    Rebuild:         docker compose build
    Full reset:      docker compose down -v (WARNING: deletes all data)
"@

Write-Host $nextSteps

Write-Host "`nPress any key to continue..." -ForegroundColor DarkGray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")