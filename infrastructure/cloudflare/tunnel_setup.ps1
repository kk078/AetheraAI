<#
.SYNOPSIS
    Cloudflare Tunnel automated setup for Aethera AI.

.DESCRIPTION
    Installs cloudflared, authenticates, creates a tunnel, configures
    ingress rules, starts the tunnel, and verifies connectivity.

.NOTES
    Requires: Cloudflare account with domain, Cloudflare API token
    Run as: powershell -ExecutionPolicy Bypass -File tunnel_setup.ps1
#>

param(
    [string]$TunnelName = "aethera-tunnel",
    [string]$Domain = $env:CLOUDFLARE_DOMAIN,
    [string]$ApiToken = $env:CLOUDFLARE_API_TOKEN,
    [string]$AccountId = $env:CLOUDFLARE_ACCOUNT_ID,
    [string]$ConfigDir = "$env:PROGRAMDATA\AetheraAI\cloudflare",
    [string]$Hostname = "",
    [int]$UIPort = 3000,
    [int]$APIPort = 8000,
    [switch]$SkipInstall,
    [switch]$SkipAuth,
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

function Write-Step($msg) {
    Write-Host "`n[CLOUDFLARE TUNNEL] $msg" -ForegroundColor Cyan
}

function Write-Ok($msg) {
    Write-Host "  [OK] $msg" -ForegroundColor Green
}

function Write-Fail($msg) {
    Write-Host "  [FAIL] $msg" -ForegroundColor Red
}

function Write-Info($msg) {
    Write-Host "  [INFO] $msg" -ForegroundColor Gray
}

function Test-Command($cmd) {
    try { Get-Command $cmd -ErrorAction Stop | Out-Null; return $true }
    catch { return $false }
}

# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------

if ($Uninstall) {
    Write-Step "Uninstalling Cloudflare Tunnel..."

    # Stop tunnel if running
    $svc = Get-Service -Name "Cloudflared" -ErrorAction SilentlyContinue
    if ($svc) {
        Stop-Service -Name "Cloudflared" -Force
        sc.exe delete Cloudflared
        Write-Ok "Removed Cloudflared service"
    }

    # Stop any running cloudflared processes
    Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Ok "Stopped cloudflared processes"

    # Delete tunnel
    if ($ApiToken -and $AccountId -and $TunnelName) {
        $listUrl = "https://api.cloudflare.com/client/v4/accounts/$AccountId/tunnels?is_deleted=false"
        try {
            $tunnels = Invoke-RestMethod -Uri $listUrl -Headers @{
                "Authorization" = "Bearer $ApiToken"
            } -ErrorAction Stop
            $target = $tunnels.result | Where-Object { $_.name -eq $TunnelName }
            if ($target) {
                $delUrl = "https://api.cloudflare.com/client/v4/accounts/$AccountId/tunnels/$($target.id)"
                Invoke-RestMethod -Uri $delUrl -Method Delete -Headers @{
                    "Authorization" = "Bearer $ApiToken"
                } | Out-Null
                Write-Ok "Deleted tunnel: $TunnelName"
            }
        }
        catch { Write-Info "Could not delete tunnel via API: $_" }
    }

    # Remove config directory
    if (Test-Path $ConfigDir) {
        Remove-Item $ConfigDir -Recurse -Force
        Write-Ok "Removed config directory: $ConfigDir"
    }

    Write-Ok "Uninstall complete"
    exit 0
}

# ---------------------------------------------------------------------------
# Validate parameters
# ---------------------------------------------------------------------------

Write-Step "Validating configuration..."

if (-not $Domain) {
    Write-Fail "CLOUDFLARE_DOMAIN environment variable or -Domain parameter is required"
    exit 1
}
Write-Ok "Domain: $Domain"

if (-not $ApiToken) {
    Write-Fail "CLOUDFLARE_API_TOKEN environment variable or -ApiToken parameter is required"
    exit 1
}

if (-not $AccountId) {
    # Try to auto-detect account ID
    try {
        $verifyUrl = "https://api.cloudflare.com/client/v4/user/tokens/verify"
        $verifyResp = Invoke-RestMethod -Uri $verifyUrl -Headers @{
            "Authorization" = "Bearer $ApiToken"
        }
        Write-Info "API token verified: status=$($verifyResp.result.status)"
    }
    catch {
        Write-Fail "API token verification failed: $_"
        exit 1
    }

    # List accounts to find account ID
    try {
        $accountsUrl = "https://api.cloudflare.com/client/v4/accounts"
        $accountsResp = Invoke-RestMethod -Uri $accountsUrl -Headers @{
            "Authorization" = "Bearer $ApiToken"
        }
        if ($accountsResp.result.Count -gt 0) {
            $AccountId = $accountsResp.result[0].id
            Write-Ok "Auto-detected Account ID: $AccountId"
        }
        else {
            Write-Fail "Could not auto-detect Account ID. Set CLOUDFLARE_ACCOUNT_ID."
            exit 1
        }
    }
    catch {
        Write-Fail "Could not fetch account ID: $_"
        exit 1
    }
}

if (-not $Hostname) {
    $Hostname = "aethera.$Domain"
}
Write-Ok "Hostname: $Hostname"

# ---------------------------------------------------------------------------
# Step 1: Install cloudflared
# ---------------------------------------------------------------------------

if (-not $SkipInstall) {
    Write-Step "Step 1: Installing cloudflared..."

    if (Test-Command "cloudflared") {
        $version = & cloudflared --version 2>&1
        Write-Ok "cloudflared already installed: $version"
    }
    else {
        $installPath = "$env:PROGRAMFILES\cloudflared"
        $exePath = Join-Path $installPath "cloudflared.exe"

        if (-not (Test-Path $installPath)) {
            New-Item -ItemType Directory -Path $installPath -Force | Out-Null
        }

        $downloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.msi"
        $msiPath = Join-Path $env:TEMP "cloudflared.msi"

        Write-Info "Downloading cloudflared..."
        try {
            Invoke-WebRequest -Uri $downloadUrl -OutFile $msiPath -UseBasicParsing
            Write-Info "Installing cloudflared MSI..."
            Start-Process msiexec.exe -ArgumentList "/i", $msiPath, "/quiet", "/norestart" -Wait
            Remove-Item $msiPath -Force -ErrorAction SilentlyContinue
        }
        catch {
            # Fallback: direct exe download
            Write-Info "MSI install failed, trying direct download..."
            $exeUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
            Invoke-WebRequest -Uri $exeUrl -OutFile $exePath -UseBasicParsing
        }

        # Add to PATH if not present
        $pathDirs = $env:PATH -split ";"
        if ($installPath -notin $pathDirs) {
            $env:PATH += ";$installPath"
            [System.Environment]::SetEnvironmentVariable("PATH", $env:PATH, "Machine")
        }

        if (Test-Command "cloudflared") {
            Write-Ok "cloudflared installed successfully"
        }
        else {
            Write-Fail "cloudflared installation failed"
            exit 1
        }
    }
}
else {
    Write-Step "Step 1: Skipping cloudflared installation (-SkipInstall)"
}

# ---------------------------------------------------------------------------
# Step 2: Authenticate
# ---------------------------------------------------------------------------

if (-not $SkipAuth) {
    Write-Step "Step 2: Authenticating with Cloudflare..."

    $certPath = Join-Path $ConfigDir "cert.pem"
    if (-not (Test-Path $certPath)) {
        New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null

        Write-Info "Opening browser for authentication..."
        Write-Info "Select your domain ($Domain) in the browser, then come back."

        $env:CLOUDFLARE_CONFIG = $ConfigDir
        & cloudflared tunnel login 2>&1

        if (Test-Path (Join-Path $env:USERPROFILE ".cloudflared\cert.pem")) {
            Copy-Item (Join-Path $env:USERPROFILE ".cloudflared\cert.pem") $certPath -Force
            Write-Ok "Authentication certificate saved"
        }
        elseif (Test-Path $certPath) {
            Write-Ok "Authentication certificate found"
        }
        else {
            Write-Fail "Authentication failed - no certificate found"
            exit 1
        }
    }
    else {
        Write-Ok "Authentication certificate already exists"
    }
}
else {
    Write-Step "Step 2: Skipping authentication (-SkipAuth)"
    $certPath = Join-Path $ConfigDir "cert.pem"
}

# ---------------------------------------------------------------------------
# Step 3: Create tunnel
# ---------------------------------------------------------------------------

Write-Step "Step 3: Creating tunnel '$TunnelName'..."

$env:CLOUDFLARE_CONFIG = $ConfigDir

# Check if tunnel already exists
$existingTunnelId = $null
try {
    $listOutput = & cloudflared tunnel list --output json 2>&1
    $tunnels = $listOutput | ConvertFrom-Json -ErrorAction SilentlyContinue
    if ($tunnels) {
        $existing = $tunnels | Where-Object { $_.name -eq $TunnelName -and $_.is_deleted -eq $false }
        if ($existing) {
            $existingTunnelId = $existing.id
            Write-Ok "Tunnel already exists: $existingTunnelId"
        }
    }
}
catch {
    # List command may not support json output in all versions
}

if (-not $existingTunnelId) {
    try {
        $createOutput = & cloudflared tunnel create $TunnelName 2>&1
        # Parse tunnel ID from output
        if ($createOutput -match "([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})") {
            $existingTunnelId = $matches[1]
            Write-Ok "Tunnel created: $existingTunnelId"
        }
        else {
            Write-Fail "Could not parse tunnel ID from output"
            Write-Info "Output: $createOutput"
            exit 1
        }
    }
    catch {
        Write-Fail "Tunnel creation failed: $_"
        exit 1
    }
}

$TunnelId = $existingTunnelId

# Copy credentials file to config dir
$credSource = Join-Path $env:USERPROFILE ".cloudflared\$TunnelId.json"
$credDest = Join-Path $ConfigDir "$TunnelId.json"
if (Test-Path $credSource) {
    Copy-Item $credSource $credDest -Force
}
elseif (-not (Test-Path $credDest)) {
    Write-Fail "Credentials file not found: $credSource or $credDest"
    exit 1
}

# ---------------------------------------------------------------------------
# Step 4: Configure ingress (DNS + tunnel config)
# ---------------------------------------------------------------------------

Write-Step "Step 4: Configuring DNS and ingress..."

# Create DNS CNAME record
$zoneId = $null
try {
    $zonesUrl = "https://api.cloudflare.com/client/v4/zones?name=$Domain"
    $zonesResp = Invoke-RestMethod -Uri $zonesUrl -Headers @{
        "Authorization" = "Bearer $ApiToken"
    }
    if ($zonesResp.result.Count -gt 0) {
        $zoneId = $zonesResp.result[0].id
        Write-Ok "Found zone ID: $zoneId"
    }
    else {
        Write-Fail "Zone not found for domain: $Domain"
        exit 1
    }
}
catch {
    Write-Fail "Could not find zone: $_"
    exit 1
}

# Create CNAME record pointing to tunnel
$cnameTarget = "$TunnelId.cfargotunnel.com"
try {
    $dnsRecordsUrl = "https://api.cloudflare.com/client/v4/zones/$zoneId/dns_records"
    $existingDns = Invoke-RestMethod -Uri "$dnsRecordsUrl?name=$Hostname" -Headers @{
        "Authorization" = "Bearer $ApiToken"
    }

    $existingRecord = $existingDns.result | Where-Object { $_.name -eq $Hostname }

    if ($existingRecord) {
        # Update existing CNAME
        $updateUrl = "$dnsRecordsUrl/$($existingRecord.id)"
        Invoke-RestMethod -Uri $updateUrl -Method Patch -Headers @{
            "Authorization" = "Bearer $ApiToken"
            "Content-Type" = "application/json"
        } -Body (@{
            type    = "CNAME"
            name    = $Hostname
            content = $cnameTarget
            proxied = $true
            ttl     = 1
        } | ConvertTo-Json) | Out-Null
        Write-Ok "Updated DNS CNAME: $Hostname -> $cnameTarget"
    }
    else {
        # Create new CNAME
        Invoke-RestMethod -Uri $dnsRecordsUrl -Method Post -Headers @{
            "Authorization" = "Bearer $ApiToken"
            "Content-Type" = "application/json"
        } -Body (@{
            type    = "CNAME"
            name    = $Hostname
            content = $cnameTarget
            proxied = $true
            ttl     = 1
        } | ConvertTo-Json) | Out-Null
        Write-Ok "Created DNS CNAME: $Hostname -> $cnameTarget"
    }
}
catch {
    Write-Fail "DNS record creation failed: $_"
    exit 1
}

# Create API hostname
$apiHostname = "api.$Domain"
try {
    $existingApiDns = Invoke-RestMethod -Uri "$dnsRecordsUrl?name=$apiHostname" -Headers @{
        "Authorization" = "Bearer $ApiToken"
    }
    $existingApiRecord = $existingApiDns.result | Where-Object { $_.name -eq $apiHostname }

    if ($existingApiRecord) {
        $updateUrl = "$dnsRecordsUrl/$($existingApiRecord.id)"
        Invoke-RestMethod -Uri $updateUrl -Method Patch -Headers @{
            "Authorization" = "Bearer $ApiToken"
            "Content-Type" = "application/json"
        } -Body (@{
            type    = "CNAME"
            name    = $apiHostname
            content = $cnameTarget
            proxied = $true
            ttl     = 1
        } | ConvertTo-Json) | Out-Null
        Write-Ok "Updated DNS CNAME: $apiHostname -> $cnameTarget"
    }
    else {
        Invoke-RestMethod -Uri $dnsRecordsUrl -Method Post -Headers @{
            "Authorization" = "Bearer $ApiToken"
            "Content-Type" = "application/json"
        } -Body (@{
            type    = "CNAME"
            name    = $apiHostname
            content = $cnameTarget
            proxied = $true
            ttl     = 1
        } | ConvertTo-Json) | Out-Null
        Write-Ok "Created DNS CNAME: $apiHostname -> $cnameTarget"
    }
}
catch {
    Write-Info "API DNS record setup skipped or failed: $_"
}

# Write tunnel configuration
$tunnelConfig = @"
tunnel: $TunnelId
credentials-file: $credDest

ingress:
  - hostname: $Hostname
    service: http://localhost:$UIPort
  - hostname: $apiHostname
    service: http://localhost:$APIPort
  - service: http_status:404
"@

$configPath = Join-Path $ConfigDir "tunnel.yml"
Set-Content -Path $configPath -Value $tunnelConfig -Encoding UTF8
Write-Ok "Tunnel config written: $configPath"

# ---------------------------------------------------------------------------
# Step 5: Start tunnel
# ---------------------------------------------------------------------------

Write-Step "Step 5: Starting tunnel..."

# Install as Windows service
try {
    & cloudflared service install 2>&1
    Write-Ok "Installed cloudflared as Windows service"
}
catch {
    Write-Info "Service install skipped or already installed, starting manually..."
}

# Start the service
$svc = Get-Service -Name "Cloudflared" -ErrorAction SilentlyContinue
if ($svc) {
    Start-Service -Name "Cloudflared" -ErrorAction SilentlyContinue
    Write-Ok "Started Cloudflared service"
}
else {
    # Start manually in background
    Start-Process -FilePath "cloudflared" -ArgumentList "tunnel", "--config", $configPath, "run", $TunnelId -WindowStyle Hidden
    Write-Ok "Started cloudflared tunnel process"
}

# ---------------------------------------------------------------------------
# Step 6: Verify connectivity
# ---------------------------------------------------------------------------

Write-Step "Step 6: Verifying connectivity..."

Start-Sleep -Seconds 10  # Allow tunnel to establish

$maxRetries = 6
$verified = $false

for ($i = 1; $i -le $maxRetries; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "https://$Hostname" -UseBasicParsing -TimeoutSec 10
        if ($response.StatusCode -lt 500) {
            $verified = $true
            Write-Ok "UI accessible at https://$Hostname (status $($response.StatusCode))"
            break
        }
    }
    catch {
        Write-Info "Attempt $i/$maxRetries failed: $_"
    }

    if ($i -lt $maxRetries) {
        Start-Sleep -Seconds 5
    }
}

# Verify API endpoint
try {
    $apiResponse = Invoke-WebRequest -Uri "https://$apiHostname/api/health" -UseBasicParsing -TimeoutSec 10
    Write-Ok "API accessible at https://$apiHostname (status $($apiResponse.StatusCode))"
}
catch {
    Write-Info "API health check: $_"
}

# Check tunnel status
try {
    $tunnelInfo = & cloudflared tunnel info $TunnelId 2>&1
    Write-Info "Tunnel info: $tunnelInfo"
}
catch {
    Write-Info "Could not get tunnel info"
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Step "Setup Complete!"
Write-Host ""
Write-Ok "Tunnel Name:    $TunnelName"
Write-Ok "Tunnel ID:      $TunnelId"
Write-Ok "UI URL:         https://$Hostname"
Write-Ok "API URL:        https://$apiHostname"
Write-Ok "Config Dir:     $ConfigDir"
Write-Ok "Config File:    $configPath"
Write-Host ""

if ($verified) {
    Write-Ok "Connectivity verified!"
}
else {
    Write-Info "Connectivity not yet verified. The tunnel may need a few minutes to propagate DNS."
    Write-Info "Check status with: cloudflared tunnel info $TunnelId"
}