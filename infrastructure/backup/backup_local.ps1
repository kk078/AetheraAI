<#
.SYNOPSIS
    Local backup of Aethera AI to external drive.

.DESCRIPTION
    Creates a timestamped backup of Docker data volumes, database files,
    and configuration. Verifies backup integrity after creation.

.NOTES
    Run as: powershell -ExecutionPolicy Bypass -File backup_local.ps1
#>

param(
    [string]$BackupRoot = "",
    [string]$DockerComposeDir = "$PWD",
    [int]$KeepDays = 30,
    [switch]$Compress,
    [switch]$VerifyOnly,
    [string]$VerifyBackup = "",
    [switch]$DryRun,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    if (-not $Quiet) { Write-Host "`n[BACKUP] $msg" -ForegroundColor Cyan }
}
function Write-Ok($msg) {
    if (-not $Quiet) { Write-Host "  [OK] $msg" -ForegroundColor Green }
}
function Write-Warn($msg) {
    if (-not $Quiet) { Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
}
function Write-Err($msg) {
    if (-not $Quiet) { Write-Host "  [FAIL] $msg" -ForegroundColor Red }
}

# ---------------------------------------------------------------------------
# Determine backup destination
# ---------------------------------------------------------------------------

if (-not $BackupRoot) {
    # Auto-detect: look for external drives
    $drives = Get-Volume | Where-Object {
        $_.DriveType -eq "Removable" -or
        ($_.DriveLetter -and $_.DriveLetter -ne "C" -and $_.Size -gt 10GB)
    } | Sort-Object -Property Size -Descending

    if ($drives.Count -gt 0) {
        $BackupRoot = "$($drives[0].DriveLetter):\AetheraBackups"
        Write-Step "Auto-detected backup drive: $($drives[0].DriveLetter):"
    }
    else {
        $BackupRoot = "$env:USERPROFILE\AetheraBackups"
        Write-Step "No external drive detected, using: $BackupRoot"
    }
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = Join-Path $BackupRoot "aethera_$timestamp"

# ---------------------------------------------------------------------------
# Verify-only mode
# ---------------------------------------------------------------------------

if ($VerifyOnly -and $VerifyBackup) {
    Write-Step "Verifying backup: $VerifyBackup"

    if (-not (Test-Path $VerifyBackup)) {
        Write-Err "Backup path not found: $VerifyBackup"
        exit 1
    }

    $manifestPath = Join-Path $VerifyBackup "manifest.json"
    if (-not (Test-Path $manifestPath)) {
        Write-Err "Manifest not found: $manifestPath"
        exit 1
    }

    $manifest = Get-Content $manifestPath | ConvertFrom-Json
    $allValid = $true

    foreach ($item in $manifest.items) {
        $itemPath = Join-Path $VerifyBackup $item.relative_path
        if (Test-Path $itemPath) {
            $actualSize = (Get-Item $itemPath).Length
            if ($actualSize -eq $item.size) {
                Write-Ok "$($item.name): size verified ($($item.size) bytes)"
            }
            else {
                Write-Err "$($item.name): size mismatch (expected $($item.size), got $actualSize)"
                $allValid = $false
            }
        }
        else {
            Write-Err "$($item.name): file missing at $itemPath"
            $allValid = $false
        }
    }

    if ($allValid) {
        Write-Ok "Backup verification PASSED"
    }
    else {
        Write-Err "Backup verification FAILED"
        exit 1
    }
    exit 0
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

Write-Step "Aethera AI Local Backup"
Write-Step "======================="
Write-Step "Backup destination: $backupDir"

# Check Docker
$dockerAvailable = $false
try {
    $dockerVersion = & docker --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $dockerAvailable = $true
        Write-Ok "Docker: $dockerVersion"
    }
}
catch { Write-Warn "Docker not available" }

# Check disk space
$backupDrive = $BackupRoot.Substring(0, 1)
$driveInfo = Get-PSDrive -Name $backupDrive -ErrorAction SilentlyContinue
if ($driveInfo) {
    $freeGB = [math]::Round($driveInfo.Free / 1GB, 2)
    Write-Ok "Free space on ${backupDrive}:: $freeGB GB"
    if ($freeGB -lt 5) {
        Write-Err "Less than 5GB free on backup drive. Aborting."
        exit 1
    }
}

# Create backup directory
if (-not $DryRun) {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    Write-Ok "Created backup directory"
}

# ---------------------------------------------------------------------------
# Backup Docker volumes
# ---------------------------------------------------------------------------

Write-Step "Backing up Docker volumes..."

$volumeNames = @(
    "aethera_aethera-data",
    "aethera_ollama-models",
    "aethera_chroma-data",
    "aethera_redis-data",
    "aethera_searxng-data",
    "aethera_voice-models"
)

# Also try with underscore-prefixed names (older docker-compose)
$allVolumeNames = $volumeNames + ($volumeNames | ForEach-Object { $_ -replace "aethera_", "aetherai_" })

$manifest = @()
$backupItems = @()

if ($dockerAvailable) {
    $existingVolumes = & docker volume ls --format "{{.Name}}" 2>&1

    foreach ($volName in $allVolumeNames) {
        if ($existingVolumes -match $volName) {
            $volBackupDir = Join-Path $backupDir "volumes\$volName"
            Write-Step "  Volume: $volName"

            if (-not $DryRun) {
                New-Item -ItemType Directory -Path $volBackupDir -Force | Out-Null

                # Use docker cp from a temporary container
                $containerId = & docker create --name "backup-temp-$timestamp" -v "${volName}:/backup_data:ro" alpine 2>&1
                if ($LASTEXITCODE -eq 0) {
                    & docker cp "${containerId}:/backup_data/." $volBackupDir 2>&1 | Out-Null
                    & docker rm "backup-temp-$timestamp" 2>&1 | Out-Null

                    $volSize = (Get-ChildItem $volBackupDir -Recurse | Measure-Object -Property Length -Sum).Sum
                    Write-Ok "  Backed up: $volName ($([math]::Round($volSize / 1MB, 2)) MB)"

                    $backupItems += @{
                        name        = "volume_$volName"
                        type        = "docker_volume"
                        relative_path = "volumes\$volName"
                        size        = $volSize
                    }
                }
                else {
                    Write-Warn "  Could not create temp container for $volName"
                    # Clean up
                    & docker rm "backup-temp-$timestamp" 2>$null
                }
            }
            else {
                Write-Ok "  [DRY RUN] Would backup: $volName"
            }
        }
        else {
            Write-Warn "  Volume not found: $volName"
        }
    }
}
else {
    Write-Warn "Docker not available, skipping volume backup"
}

# ---------------------------------------------------------------------------
# Backup database files
# ---------------------------------------------------------------------------

Write-Step "Backing up database files..."

$dbPaths = @(
    ".\data\aethera.db",
    ".\data\conversations.db",
    ".\data\aethera_usage.db",
    ".\data\aethera_uptime.db"
)

foreach ($dbPath in $dbPaths) {
    $resolvedPath = if (Test-Path $dbPath) { $dbPath } elseif (Test-Path (Join-Path $DockerComposeDir $dbPath)) { Join-Path $DockerComposeDir $dbPath } else { $null }

    if ($resolvedPath -and (Test-Path $resolvedPath)) {
        $dbName = Split-Path $resolvedPath -Leaf
        $destPath = Join-Path $backupDir "databases\$dbName"

        if (-not $DryRun) {
            New-Item -ItemType Directory -Path (Split-Path $destPath) -Force | Out-Null

            # Copy with retry for locked files
            $copied = $false
            for ($attempt = 1; $attempt -le 3; $attempt++) {
                try {
                    Copy-Item $resolvedPath $destPath -Force
                    $copied = $true
                    break
                }
                catch {
                    if ($attempt -lt 3) {
                        Start-Sleep -Seconds 2
                    }
                }
            }

            if ($copied) {
                $fileSize = (Get-Item $destPath).Length
                Write-Ok "Backed up: $dbName ($([math]::Round($fileSize / 1KB, 2)) KB)"

                $backupItems += @{
                    name          = "database_$dbName"
                    type          = "database"
                    relative_path = "databases\$dbName"
                    size          = $fileSize
                }
            }
            else {
                Write-Warn "Could not copy locked file: $dbName"
            }
        }
        else {
            Write-Ok "[DRY RUN] Would backup: $dbName"
        }
    }
}

# ---------------------------------------------------------------------------
# Backup configuration files
# ---------------------------------------------------------------------------

Write-Step "Backing up configuration files..."

$configFiles = @(
    ".\docker-compose.yml",
    ".\docker-compose.override.yml",
    ".\litellm_config.yaml",
    ".\searxng-settings.yml",
    ".\orchestrator\config.yaml",
    ".\env.example",
    ".\.env"
)

foreach ($cfgPath in $configFiles) {
    $resolvedPath = if (Test-Path $cfgPath) { $cfgPath } elseif (Test-Path (Join-Path $DockerComposeDir $cfgPath)) { Join-Path $DockerComposeDir $cfgPath } else { $null }

    if ($resolvedPath -and (Test-Path $resolvedPath)) {
        $cfgName = $resolvedPath.Replace("$DockerComposeDir\", "").Replace("\", "_").Replace("/", "_")
        $destPath = Join-Path $backupDir "config\$cfgName"

        if (-not $DryRun) {
            New-Item -ItemType Directory -Path (Split-Path $destPath) -Force | Out-Null
            Copy-Item $resolvedPath $destPath -Force
            $fileSize = (Get-Item $destPath).Length
            Write-Ok "Backed up: $cfgName"

            $backupItems += @{
                name          = "config_$cfgName"
                type          = "config"
                relative_path = "config\$cfgName"
                size          = $fileSize
            }
        }
        else {
            Write-Ok "[DRY RUN] Would backup: $cfgName"
        }
    }
}

# ---------------------------------------------------------------------------
# Compress backup (optional)
# ---------------------------------------------------------------------------

if ($Compress) {
    Write-Step "Compressing backup..."

    if (-not $DryRun) {
        $archivePath = "$backupDir.zip"
        Compress-Archive -Path $backupDir -DestinationPath $archivePath -Force
        $archiveSize = (Get-Item $archivePath).Length
        Write-Ok "Archive created: $archivePath ($([math]::Round($archiveSize / 1MB, 2)) MB)"

        # Remove uncompressed directory
        Remove-Item $backupDir -Recurse -Force
        $backupDir = $archivePath
    }
    else {
        Write-Ok "[DRY RUN] Would compress backup"
    }
}

# ---------------------------------------------------------------------------
# Write manifest
# ---------------------------------------------------------------------------

if (-not $DryRun) {
    Write-Step "Writing backup manifest..."

    $totalSize = ($backupItems | Measure-Object -Property size -Sum).Sum

    $manifestObj = @{
        timestamp    = $timestamp
        created_at   = (Get-Date).Iso8601Format()
        source_dir   = $DockerComposeDir
        backup_dir   = $backupDir
        total_items  = $backupItems.Count
        total_size   = $totalSize
        total_size_mb = [math]::Round($totalSize / 1MB, 2)
        compressed   = $Compress.IsPresent
        items        = $backupItems
        environment  = @{
            hostname = $env:COMPUTERNAME
            user     = $env:USERNAME
            os       = (Get-CimInstance Win32_OperatingSystem).Caption
        }
    }

    $manifestPath = if ($Compress) {
        # For compressed, write manifest alongside
        Join-Path $BackupRoot "manifest_$timestamp.json"
    }
    else {
        Join-Path $backupDir "manifest.json"
    }

    $manifestObj | ConvertTo-Json -Depth 10 | Set-Content $manifestPath -Encoding UTF8
    Write-Ok "Manifest written: $manifestPath"
}

# ---------------------------------------------------------------------------
# Verify backup integrity
# ---------------------------------------------------------------------------

if (-not $DryRun -and -not $Compress) {
    Write-Step "Verifying backup integrity..."

    $manifestData = Get-Content (Join-Path $backupDir "manifest.json") | ConvertFrom-Json
    $verifyOk = $true

    foreach ($item in $manifestData.items) {
        $itemPath = Join-Path $backupDir $item.relative_path
        if (Test-Path $itemPath) {
            $actualSize = (Get-Item $itemPath -ErrorAction SilentlyContinue).Length
            if ($actualSize -and $actualSize -eq $item.size) {
                Write-Ok "$($item.name): verified"
            }
            else {
                Write-Warn "$($item.name): size mismatch (expected $($item.size), actual $actualSize)"
                $verifyOk = $false
            }
        }
        else {
            Write-Err "$($item.name): missing at $itemPath"
            $verifyOk = $false
        }
    }

    if ($verifyOk) {
        Write-Ok "Backup integrity verified!"
    }
    else {
        Write-Warn "Some items failed verification. Check the backup manually."
    }
}

# ---------------------------------------------------------------------------
# Cleanup old backups
# ---------------------------------------------------------------------------

Write-Step "Cleaning up old backups (keeping last $KeepDays days)..."

$cutoff = (Get-Date).AddDays(-$KeepDays)
$oldBackups = Get-ChildItem $BackupRoot -Directory -Filter "aethera_*" -ErrorAction SilentlyContinue |
    Where-Object { $_.CreationTime -lt $cutoff }

$oldArchives = Get-ChildItem $BackupRoot -File -Filter "aethera_*.zip" -ErrorAction SilentlyContinue |
    Where-Object { $_.CreationTime -lt $cutoff }

$totalCleaned = 0

foreach ($old in ($oldBackups + $oldArchives)) {
    if (-not $DryRun) {
        Remove-Item $old.FullName -Recurse -Force
        Write-Ok "Removed old backup: $($old.Name)"
        $totalCleaned++
    }
    else {
        Write-Ok "[DRY RUN] Would remove: $($old.Name)"
    }
}

if ($totalCleaned -gt 0) {
    Write-Ok "Cleaned up $totalCleaned old backup(s)"
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Step "Backup Complete!"
Write-Host ""
Write-Ok "Location:  $backupDir"
Write-Ok "Items:     $($backupItems.Count)"
Write-Ok "Timestamp: $timestamp"
if ($Compress) { Write-Ok "Compressed: Yes" }
Write-Host ""

if ($DryRun) {
    Write-Info "This was a dry run. No files were actually backed up."
}