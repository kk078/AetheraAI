<#
.SYNOPSIS
    Cloudflare Access (Zero Trust) setup for Aethera AI.

.DESCRIPTION
    Creates a Cloudflare Access application, configures email OTP
    authentication policy, and binds it to the tunnel hostname.
    This ensures only authenticated users can access Aethera remotely.

.NOTES
    Requires: Cloudflare Zero Trust enabled, API token with Access edit permissions
    Run as: powershell -ExecutionPolicy Bypass -File access_setup.ps1
#>

param(
    [string]$Domain = $env:CLOUDFLARE_DOMAIN,
    [string]$ApiToken = $env:CLOUDFLARE_API_TOKEN,
    [string]$AccountId = $env:CLOUDFLARE_ACCOUNT_ID,
    [string]$AppName = "Aethera AI",
    [string]$Hostname = "",
    [string]$ApiHostname = "",
    [string[]]$AllowedEmails = @(),
    [string[]]$AllowedEmailDomains = @(),
    [string]$PolicyName = "Email OTP Authentication",
    [int]$SessionDurationHours = 24,
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "`n[CLOUDFLARE ACCESS] $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red }
function Write-Info($msg) { Write-Host "  [INFO] $msg" -ForegroundColor Gray }

$BaseApiUrl = "https://api.cloudflare.com/client/v4/accounts/$AccountId"

# ---------------------------------------------------------------------------
# Validate parameters
# ---------------------------------------------------------------------------

if (-not $Domain) { Write-Fail "CLOUDFLARE_DOMAIN required"; exit 1 }
if (-not $ApiToken) { Write-Fail "CLOUDFLARE_API_TOKEN required"; exit 1 }
if (-not $AccountId) { Write-Fail "CLOUDFLARE_ACCOUNT_ID required"; exit 1 }

if (-not $Hostname) { $Hostname = "aethera.$Domain" }
if (-not $ApiHostname) { $ApiHostname = "api.$Domain" }

$Headers = @{
    "Authorization" = "Bearer $ApiToken"
    "Content-Type"  = "application/json"
}

# ---------------------------------------------------------------------------
# Remove access application and policies
# ---------------------------------------------------------------------------

if ($Remove) {
    Write-Step "Removing Cloudflare Access configuration..."

    # Find existing applications
    try {
        $apps = Invoke-RestMethod -Uri "$BaseApiUrl/access/apps" -Headers $Headers
        $aetheraApps = $apps.result | Where-Object { $_.name -like "*Aethera*" }

        foreach ($app in $aetheraApps) {
            # Delete policies first
            try {
                $policies = Invoke-RestMethod -Uri "$BaseApiUrl/access/apps/$($app.id)/policies" -Headers $Headers
                foreach ($policy in $policies.result) {
                    Invoke-RestMethod -Uri "$BaseApiUrl/access/apps/$($app.id)/policies/$($policy.id)" -Method Delete -Headers $Headers | Out-Null
                    Write-Ok "Deleted policy: $($policy.name)"
                }
            }
            catch { Write-Info "No policies found for app $($app.id)" }

            # Delete application
            Invoke-RestMethod -Uri "$BaseApiUrl/access/apps/$($app.id)" -Method Delete -Headers $Headers | Out-Null
            Write-Ok "Deleted application: $($app.name)"
        }
    }
    catch { Write-Info "Error during removal: $_" }

    Write-Ok "Access configuration removed"
    exit 0
}

# ---------------------------------------------------------------------------
# Step 1: Verify account and get zone info
# ---------------------------------------------------------------------------

Write-Step "Step 1: Verifying account and zone..."

$zonesResp = Invoke-RestMethod -Uri "https://api.cloudflare.com/client/v4/zones?name=$Domain" -Headers $Headers
if ($zonesResp.result.Count -eq 0) {
    Write-Fail "Zone not found for domain: $Domain"
    exit 1
}
$ZoneId = $zonesResp.result[0].id
Write-Ok "Zone ID: $ZoneId"

# Check if Zero Trust is enabled
try {
    $accountResp = Invoke-RestMethod -Uri "$BaseApiUrl/access/apps" -Headers $Headers
    Write-Ok "Zero Trust / Access is enabled on this account"
}
catch {
    Write-Fail "Cloudflare Access may not be enabled. Enable Zero Trust in the Cloudflare dashboard."
    exit 1
}

# ---------------------------------------------------------------------------
# Step 2: Create Access Application for UI
# ---------------------------------------------------------------------------

Write-Step "Step 2: Creating Access application for UI ($Hostname)..."

# Check if app already exists
$existingApps = Invoke-RestMethod -Uri "$BaseApiUrl/access/apps" -Headers $Headers
$uiApp = $existingApps.result | Where-Object { $_.domain -eq $Hostname }

if ($uiApp) {
    Write-Ok "Application already exists: $($uiApp.id) for $Hostname"
}
else {
    $uiAppBody = @{
        name              = "$AppName - UI"
        domain            = $Hostname
        type              = "self_hosted"
        session_duration  = "${SessionDurationHours}h"
        auto_redirect_to_identity = $true
        options = @{
            self_hosted = @{
                domain = $Hostname
            }
        }
    } | ConvertTo-Json -Depth 10

    $createResp = Invoke-RestMethod -Uri "$BaseApiUrl/access/apps" -Method Post -Headers $Headers -Body $uiAppBody
    $uiApp = $createResp.result
    Write-Ok "Created application: $($uiApp.id)"
}

# ---------------------------------------------------------------------------
# Step 3: Create Access Application for API
# ---------------------------------------------------------------------------

Write-Step "Step 3: Creating Access application for API ($ApiHostname)..."

$apiApp = $existingApps.result | Where-Object { $_.domain -eq $ApiHostname }

if ($apiApp) {
    Write-Ok "Application already exists: $($apiApp.id) for $ApiHostname"
}
else {
    $apiAppBody = @{
        name              = "$AppName - API"
        domain            = $ApiHostname
        type              = "self_hosted"
        session_duration  = "${SessionDurationHours}h"
        auto_redirect_to_identity = $true
        options = @{
            self_hosted = @{
                domain = $ApiHostname
            }
        }
    } | ConvertTo-Json -Depth 10

    $createResp = Invoke-RestMethod -Uri "$BaseApiUrl/access/apps" -Method Post -Headers $Headers -Body $apiAppBody
    $apiApp = $createResp.result
    Write-Ok "Created application: $($apiApp.id)"
}

# ---------------------------------------------------------------------------
# Step 4: Create email OTP access policy
# ---------------------------------------------------------------------------

Write-Step "Step 4: Creating email OTP access policy..."

function New-AccessPolicy($AppId, $AppName, $Policies) {
    $existingPolicies = Invoke-RestMethod -Uri "$BaseApiUrl/access/apps/$AppId/policies" -Headers $Headers

    if ($existingPolicies.result.Count -gt 0) {
        Write-Ok "Policy already exists for $AppName"
        return $existingPolicies.result[0]
    }

    # Build include rules
    $includeRules = @()

    if ($AllowedEmails.Count -gt 0) {
        foreach ($email in $AllowedEmails) {
            $includeRules += @{
                type  = "email"
                value = $email
            }
        }
    }

    if ($AllowedEmailDomains.Count -gt 0) {
        foreach ($emailDomain in $AllowedEmailDomains) {
            $includeRules += @{
                type  = "email_domain"
                value = $emailDomain
            }
        }
    }

    # If no specific emails/domains, allow the domain itself
    if ($includeRules.Count -eq 0) {
        $includeRules += @{
            type  = "email_domain"
            value = $Domain
        }
        Write-Info "No specific emails configured, allowing @$Domain domain"
    }

    $policyBody = @{
        name          = "$AppName - $PolicyName"
        decision      = "allow"
        precedence    = 1
        session_duration = "${SessionDurationHours}h"
        include       = $includeRules
        require       = @()
        exclude       = @()
    } | ConvertTo-Json -Depth 10

    $policyResp = Invoke-RestMethod -Uri "$BaseApiUrl/access/apps/$AppId/policies" -Method Post -Headers $Headers -Body $policyBody
    Write-Ok "Created policy: $($policyResp.result.name)"
    return $policyResp.result
}

$uiPolicy = New-AccessPolicy -AppId $uiApp.id -AppName "$AppName - UI" -Policies $AllowedEmails
$apiPolicy = New-AccessPolicy -AppId $apiApp.id -AppName "$AppName - API" -Policies $AllowedEmails

# ---------------------------------------------------------------------------
# Step 5: Verify Access configuration
# ---------------------------------------------------------------------------

Write-Step "Step 5: Verifying Access configuration..."

# Test that the application is accessible (should redirect to login)
$accessVerified = $false
try {
    $response = Invoke-WebRequest -Uri "https://$Hostname" -MaximumRedirection 0 -UseBasicParsing -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 301 -or $response.StatusCode -eq 302) {
        $location = $response.Headers["Location"]
        if ($location -match "cloudflareaccess") {
            $accessVerified = $true
            Write-Ok "Access redirect detected - authentication is active"
        }
    }
}
catch {
    # A redirect exception is expected
    if ($_.Exception.Response.StatusCode -in @(301, 302, 303, 307)) {
        $location = $_.Exception.Response.Headers["Location"]
        if ($location -match "cloudflareaccess") {
            $accessVerified = $true
            Write-Ok "Access redirect detected - authentication is active"
        }
    }
}

if (-not $accessVerified) {
    Write-Info "Could not verify access redirect. DNS may still be propagating."
    Write-Info "Visit https://$Hostname in a browser to confirm the login page appears."
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Step "Access Setup Complete!"
Write-Host ""
Write-Ok "UI Application:  $($uiApp.id) ($Hostname)"
Write-Ok "API Application:  $($apiApp.id) ($ApiHostname)"
Write-Ok "Authentication:   Email OTP"
Write-Ok "Session Duration: ${SessionDurationHours}h"
if ($AllowedEmails.Count -gt 0) {
    Write-Ok "Allowed Emails:   $($AllowedEmails -join ', ')"
}
if ($AllowedEmailDomains.Count -gt 0) {
    Write-Ok "Allowed Domains:  $($AllowedEmailDomains -join ', ')"
}
else {
    Write-Ok "Allowed Domains:  @$Domain (default)"
}
Write-Host ""
Write-Info "Users will be prompted for email OTP when accessing Aethera remotely."
Write-Info "To manage access, visit: https://one.dash.cloudflare.com/"
Write-Info "To remove: .\access_setup.ps1 -Remove"