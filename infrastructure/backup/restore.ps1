<#
.SYNOPSIS
    Restore Aethera AI from backup.

.DESCRIPTION
    Prompts for backup location, stops services, restores data,
    verifies integrity, and restarts services.

.NOTES
    Run as: powershell -ExecutionPolicy Bypass -File restore.ps1
#>

param(
    [string]$BackupPath = "",
    [string]$DockerComposeDir = "$PWD",
    [switch]$FromR2,
    [string]$R2Date = "",
    [switch]$SkipServiceStop,
    [switch]$SkipVerify,
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "`n[RESTORE] $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red }
function Write-Info($msg) { Write-Host "  [INFO] $msg" -ForegroundColor Gray }

# ---------------------------------------------------------------------------
# Prompt for backup location
# ---------------------------------------------------------------------------

Write-Step "Aethera AI Backup Restore"
Write-Step "========================="

if (-not $BackupPath -and -not $FromR2) {
    # List available local backups
    $localBackupRoots = @(
        "$env:USERPROFILE\AetheraBackups",
        ".\backups"
    )

    # Check for external drives
    $removableDrives = Get-Volume | Where-Object {
        $_.DriveType -eq "Removable" -and $_.DriveLetter
    }

    foreach ($drive in $removableDrives) {
        $localBackupRoots += "$($drive.DriveLetter):\AetheraBackups"
    }

    $availableBackups = @()

    foreach ($root in $localBackupRoots) {
        if (Test-Path $root) {
            $dirs = Get-ChildItem $root -Directory -Filter "aethera_*" -ErrorAction SilentlyContinue
            foreach ($d in $dirs) {
                $manifestPath = Join-Path $d.FullName "manifest.json"
                if (Test-Path $manifestPath) {
                    $availableBackups += $d
                }
            }

            $zips = Get-ChildItem $root -File -Filter "aethera_*.zip" -ErrorAction SilentlyContinue
            foreach ($z in $zips) {
                $availableBackups += $z
            }
        }
    }

    if ($availableBackups.Count -eq 0) {
        Write-Err "No backups found in common locations."
        Write-Info "Specify backup path with: -BackupPath <path>"
        Write-Info "Or restore from R2 with:  -FromR2 -R2Date <YYYY/MM/DD>"
        exit 1
    }

    Write-Step "Available backups:"
    for ($i = 0; $i -lt $availableBackups.Count; $i++) {
        $b = $availableBackups[$i]
        $size = if ($b.PSIsContainer) {
            (Get-ChildItem $b.FullName -Recurse -File | Measure-Object -Property Length -Sum).Sum
        }
        else {
            $b.Length
        }
        $sizeStr = if ($size -gt 1GB) { "{0:N2} GB" -f ($size / 1GB) } elseif ($size -gt 1MB) { "{0:N2} MB" -f ($size / 1MB) } else { "{0:N2} KB" -f ($size / 1KB) }
        $typeStr = if ($b.PSIsContainer) { "Directory" } else { "Archive" }
        Write-Host "  [$i] $($b.Name)  ($sizeStr, $typeStr, $($b.CreationTime.ToString('yyyy-MM-dd HH:mm')))"
    }

    if (-not $Force) {
        $selection = Read-Host "Select backup number (or 'q' to quit)"
        if ($selection -eq "q" -or $selection -eq "Q") { exit 0 }
        $idx = [int]$selection
    }
    else {
        $idx = 0
    }

    if ($idx -ge 0 -and $idx -lt $availableBackups.Count) {
        $BackupPath = $availableBackups[$idx].FullName
        Write-Ok "Selected: $BackupPath"
    }
    else {
        Write-Err "Invalid selection"
        exit 1
    }
}

# ---------------------------------------------------------------------------
# Handle R2 restore
# ---------------------------------------------------------------------------

if ($FromR2) {
    if (-not $R2Date) {
        Write-Err "R2 date required. Use: -R2Date 2025/01/15"
        exit 1
    }

    Write-Step "Restoring from Cloudflare R2 (date: $R2Date)..."

    if (-not $DryRun) {
        # Run the R2 backup script's restore command
        $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
        $r2Script = Join-Path $scriptDir "backup_r2.py"

        if (Test-Path $r2Script) {
            $env:RESTORE_DIR = Join-Path $DockerComposeDir "data_restored"
            & python $r2Script restore --date $R2Date --dest $env:RESTORE_DIR

            if ($LASTEXITCODE -ne 0) {
                Write-Err "R2 restore failed"
                exit 1
            }

            $BackupPath = $env:RESTORE_DIR
            Write-Ok "R2 restore complete: $BackupPath"
        }
        else {
            Write-Err "R2 backup script not found: $r2Script"
            exit 1
        }
    }
    else {
        Write-Info "[DRY RUN] Would restore from R2: $R2Date"
    }
}

# Validate backup path
if (-not $BackupPath -or -not (Test-Path $BackupPath)) {
    Write-Err "Backup path not found: $BackupPath"
    exit 1
}

# Determine if it's an archive
$isArchive = $BackupPath.EndsWith(".zip")
$isDirectory = (Get-Item $BackupPath).PSIsContainer

# Extract archive if needed
if ($isArchive) {
    Write-Step "Extracting archive..."

    $extractDir = Join-Path $env:TEMP "aethera_restore_$([datetime]::Now.ToString('yyyyMMdd_HHmmss'))"

    if (-not $DryRun) {
        Expand-Archive -Path $BackupPath -DestinationPath $extractDir -Force
        Write-Ok "Extracted to: $extractDir"
        $BackupPath = $extractDir
        $isDirectory = $true
    }
    else {
        Write-Info "[DRY RUN] Would extract to: $extractDir"
    }
}

# Load manifest
$manifestPath = Join-Path $BackupPath "manifest.json"
$manifest = $null

if (Test-Path $manifestPath) {
    $manifest = Get-Content $manifestPath | ConvertFrom-Json
    Write-Step "Backup manifest:"
    Write-Info "  Created:   $($manifest.timestamp)"
    Write-Info "  Items:     $($manifest.total_items)"
    Write-Info "  Size:      $($manifest.total_size_mb) MB"
    Write-Info "  Compressed: $($manifest.compressed)"
}

# ---------------------------------------------------------------------------
# Confirm restore
# ---------------------------------------------------------------------------

if (-not $Force -and -not $DryRun) {
    Write-Host ""
    Write-Warn "WARNING: This will replace current data with backup data!"
    Write-Warn "Current services will be stopped during restore."
    $confirm = Read-Host "Continue? (yes/no)"
    if ($confirm -ne "yes") {
        Write-Info "Restore cancelled."
        exit 0
    }
}

# ---------------------------------------------------------------------------
# Stop services
# ---------------------------------------------------------------------------

if (-not $SkipServiceStop) {
    Write-Step "Stopping Aethera services..."

    if (-not $DryRun) {
        # Check if running via Docker Compose
        $composeFile = Join-Path $DockerComposeDir "docker-compose.yml"
        if (Test-Path $composeFile) {
            Push-Location $DockerComposeDir
            try {
                & docker compose down 2>&1 | Out-Null
                Write-Ok "Docker Compose services stopped"
            }
            catch {
                Write-Warn "Could not stop via docker compose: $_"
                # Try stopping containers individually
                $containers = & docker ps --filter "name=aethera" --format "{{.Names}}" 2>&1
                foreach ($c in $containers) {
                    & docker stop $c 2>&1 | Out-Null
                    Write-Ok "Stopped container: $c"
                }
            }
            Pop-Location
        }
        else {
            # Stop individual containers
            $containers = & docker ps --filter "name=aethera" --format "{{.Names}}" 2>&1
            foreach ($c in $containers) {
                & docker stop $c 2>&1 | Out-Null
                Write-Ok "Stopped container: $c"
            }
        }
    }
    else {
        Write-Info "[DRY RUN] Would stop Aethera services"
    }
}

# ---------------------------------------------------------------------------
# Restore data
# ---------------------------------------------------------------------------

Write-Step "Restoring data..."

# Restore Docker volumes
$volumesDir = Join-Path $BackupPath "volumes"
if (Test-Path $volumesDir) {
    Write-Step "Restoring Docker volumes..."

    $volumeDirs = Get-ChildItem $volumesDir -Directory -ErrorAction SilentlyContinue

    foreach ($volDir in $volumeDirs) {
        $volName = $volDir.Name
        Write-Info "  Restoring volume: $volName"

        if (-not $DryRun) {
            # Ensure volume exists
            $existingVolumes = & docker volume ls --format "{{.Name}}" 2>&1
            if ($existingVolumes -notmatch $volName) {
                & docker volume create $volName 2>&1 | Out-Null
                Write-Ok "  Created volume: $volName"
            }

            # Copy data into volume using temp container
            $containerName = "restore-temp-$volName-$([datetime]::Now.ToString('HHmmss'))"
            $containerId = & docker create --name $containerName -v "${volName}:/restore_target" alpine 2>&1

            if ($LASTEXITCODE -eq 0) {
                & docker cp "$($volDir.FullName)/." "${containerId}:/restore_target/" 2>&1 | Out-Null
                & docker rm $containerName 2>&1 | Out-Null
                Write-Ok "  Restored: $volName"
            }
            else {
                Write-Warn "  Could not create temp container for $volName"
                & docker rm $containerName 2>$null
            }
        }
        else {
            Write-Info "  [DRY RUN] Would restore volume: $volName"
        }
    }
}

# Restore databases
$databasesDir = Join-Path $BackupPath "databases"
if (Test-Path $databasesDir) {
    Write-Step "Restoring database files..."

    $dataDir = Join-Path $DockerComposeDir "data"
    if (-not (Test-Path $dataDir)) {
        New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
    }

    $dbFiles = Get-ChildItem $databasesDir -File -ErrorAction SilentlyContinue

    foreach ($dbFile in $dbFiles) {
        $destPath = Join-Path $dataDir $dbFile.Name

        if (-not $DryRun) {
            # Backup current file if it exists
            if (Test-Path $destPath) {
                $backupCurrent = "$destPath.pre_restore_$([datetime]::Now.ToString('yyyyMMdd_HHmmss'))"
                Copy-Item $destPath $backupCurrent -Force
                Write-Info "  Current file backed up: $backupCurrent"
            }

            Copy-Item $dbFile.FullName $destPath -Force
            Write-Ok "  Restored: $($dbFile.Name)"
        }
        else {
            Write-Info "  [DRY RUN] Would restore: $($dbFile.Name)"
        }
    }
}

# Restore config
$configDir = Join-Path $BackupPath "config"
if (Test-Path $configDir) {
    Write-Step "Restoring configuration files..."

    $configFiles = Get-ChildItem $configDir -File -ErrorAction SilentlyContinue

    foreach ($cfgFile in $configFiles) {
        # Decode the flattened path name back to original
        $originalName = $cfgFile.Name
        $destPath = Join-Path $DockerComposeDir $originalName.Replace("_", "\")

        if (-not $DryRun) {
            $destDir = Split-Path $destPath -Parent
            if (-not (Test-Path $destDir)) {
                New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            }

            if (Test-Path $destPath) {
                $backupCurrent = "$destPath.pre_restore_$([datetime]::Now.ToString('yyyyMMdd_HHmmss'))"
                Copy-Item $destPath $backupCurrent -Force
            }

            Copy-Item $cfgFile.FullName $destPath -Force
            Write-Ok "  Restored: $originalName"
        }
        else {
            Write-Info "  [DRY RUN] Would restore: $originalName"
        }
    }
}

# ---------------------------------------------------------------------------
# Verify restored data
# ---------------------------------------------------------------------------

if (-not $SkipVerify -and $manifest -and -not $DryRun) {
    Write-Step "Verifying restored data..."

    $verifyOk = $true

    foreach ($item in $manifest.items) {
        $itemPath = Join-Path $BackupPath $item.relative_path

        if (Test-Path $itemPath) {
            $actualSize = (Get-Item $itemPath -ErrorAction SilentlyContinue).Length
            if ($actualSize -and $actualSize -eq $item.size) {
                Write-Ok "$($item.name): verified"
            }
            else {
                Write-Warn "$($item.name): size mismatch (expected $($item.size), actual $actualSize)"
            }
        }
        else {
            Write-Warn "$($item.name): source file missing"
        }
    }

    if ($verifyOk) {
        Write-Ok "Verification passed"
    }
}

# ---------------------------------------------------------------------------
# Restart services
# ---------------------------------------------------------------------------

if (-not $SkipServiceStop) {
    Write-Step "Restarting Aethera services..."

    if (-not $DryRun) {
        Start-Sleep -Seconds 3  # Brief pause before restart

        $composeFile = Join-Path $DockerComposeDir "docker-compose.yml"
        if (Test-Path $composeFile) {
            Push-Location $DockerComposeDir
            try {
                & docker compose up -d 2>&1 | Out-Null
                Write-Ok "Docker Compose services started"
            }
            catch {
                Write-Warn "Could not start via docker compose: $_"
            }
            Pop-Location
        }
        else {
            Write-Warn "No docker-compose.yml found. Start services manually."
        }

        # Wait for services to be ready
        Write-Info "Waiting for services to initialize..."
        Start-Sleep -Seconds 15

        # Quick health check
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Ok "Orchestrator health check: OK"
            }
        }
        catch {
            Write-Warn "Orchestrator not yet responding (may need more time to start)"
        }
    }
    else {
        Write-Info "[DRY RUN] Would restart services"
    }
}

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

if ($isArchive -and (Test-Path (Join-Path $env:TEMP "aethera_restore_"))) {
    Write-Step "Cleaning up temporary files..."
    Get-ChildItem $env:TEMP -Directory -Filter "aethera_restore_*" -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    }
    Write-Ok "Temporary files cleaned up"
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Step "Restore Complete!"
Write-Host ""
Write-Ok "Backup:     $BackupPath"
Write-Ok "Data dir:   $DockerComposeDir"
if ($manifest) {
    Write-Ok "Backup date: $($manifest.timestamp)"
    Write-Ok "Items:       $($manifest.total_items)"
}
Write-Host ""
Write-Info "If services did not start automatically, run:"
Write-Info "  cd $DockerComposeDir && docker compose up -d"