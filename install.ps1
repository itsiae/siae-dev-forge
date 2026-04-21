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

function Write-InstallLog { param($Message, $Level = 'Info') throw 'not implemented' }
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
    Write-Host "[DevForge] install.ps1 scaffold — funzioni non ancora implementate. Vedi task T02-T11." -ForegroundColor Yellow
    exit 0
}
