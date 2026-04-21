#Requires -Version 5.1
<#
.SYNOPSIS
    DevForge Windows Telemetry Enforcement Installer.
.DESCRIPTION
    Garantisce bash + python3 + jq + plugin Claude Code DevForge su Windows.
    Feature parity 100% con la pipeline telemetria Mac/Linux.
.PARAMETER DryRun
    Logga tutte le azioni senza eseguirle (usato in CI e test).
.PARAMETER NoPortableFallback
    Disabilita il fallback a PortableGit/Python-Standalone embedded.
.PARAMETER Force
    Forza reinstallazione anche se dipendenze già presenti.
#>
[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$NoPortableFallback,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$script:DevForgeLogFile = Join-Path $env:LOCALAPPDATA 'DevForge\install.log'
$script:DevForgeDryRun = $false

function Write-InstallLog {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true, Position=0)]
        [string]$Message,
        [ValidateSet('Info','Warning','Error')]
        [string]$Level = 'Info'
    )
    $logDir = Split-Path $script:DevForgeLogFile -Parent
    if (-not (Test-Path -LiteralPath $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    $ts = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    $line = "[$ts] [$($Level.ToUpper())] $Message"
    Add-Content -Path $script:DevForgeLogFile -Value $line -Encoding UTF8

    $color = switch ($Level) {
        'Error'   { 'Red' }
        'Warning' { 'Yellow' }
        default   { 'White' }
    }
    Write-Host $line -ForegroundColor $color
}

function Invoke-DevForgeCommand {
    <#
    .SYNOPSIS
        Wrapper per Invoke-Expression che rispetta DryRun mode.
    .PARAMETER Command
        Comando shell da eseguire.
    .OUTPUTS
        Output del comando, oppure $null in DryRun.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [string]$Command
    )
    if ($script:DevForgeDryRun) {
        Write-InstallLog "[DRY-RUN] would execute: $Command" -Level Info
        return $null
    }
    return (Invoke-Expression $Command)
}

function Find-Bash { throw 'not implemented' }
function Find-Python3 { throw 'not implemented' }
function Find-Jq { throw 'not implemented' }
function Install-GitViaWinget { throw 'not implemented' }
function Install-GitViaChoco { throw 'not implemented' }
function Install-GitViaScoop { throw 'not implemented' }
function Install-GitViaDirectDownload { throw 'not implemented' }
function Install-GitViaPortableEmbedded { throw 'not implemented' }
function Install-PythonViaStandaloneEmbedded { throw 'not implemented' }
function Install-JqFromAsset { throw 'not implemented' }
function Install-ClaudePlugin { throw 'not implemented' }
function Invoke-HealthCheck { throw 'not implemented' }
function New-InstallSnapshot { throw 'not implemented' }
function Invoke-Rollback { param($Snapshot) throw 'not implemented' }

# Main flow — riempito in task successivi (T02-T11)
if ($MyInvocation.InvocationName -ne '.') {
    $script:DevForgeDryRun = $DryRun.IsPresent
    Write-Host "[DevForge] install.ps1 scaffold — funzioni non ancora implementate. Vedi task T02-T11." -ForegroundColor Yellow
    exit 0
}
