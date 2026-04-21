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
    <#
    .SYNOPSIS
        Logga un messaggio su file persistente + console con color-coding.
    .DESCRIPTION
        Scrive una riga timestamped ISO-8601Z in $script:DevForgeLogFile + Write-Host
        colorato (Red=Error, Yellow=Warning, White=Info). Crea la directory log se
        mancante. Single-process use — nessun lock su file (documentato, non usare
        da installer concorrenti).
    .PARAMETER Message
        Testo del log.
    .PARAMETER Level
        Severity level: Info (default) / Warning / Error.
    #>
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
        Wrapper che rispetta DryRun mode — esegue executable con argomenti splattati.
    .DESCRIPTION
        Sostituisce Invoke-Expression per evitare command injection. Accetta solo
        executable path + array argomenti, mai stringhe shell-concatenate.
    .PARAMETER Executable
        Path o nome executable (es. 'winget', 'choco', 'C:\full\path\to.exe').
    .PARAMETER Arguments
        Array di argomenti passati splattati a & operator.
    .OUTPUTS
        String — output combinato stdout/stderr del comando, oppure $null in DryRun.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true, Position=0)]
        [string]$Executable,
        [Parameter(Position=1)]
        [string[]]$Arguments = @()
    )
    if ($script:DevForgeDryRun) {
        $argStr = ($Arguments -join ' ')
        Write-InstallLog "[DRY-RUN] would execute: $Executable $argStr" -Level Info
        return $null
    }
    & $Executable @Arguments 2>&1
}

function Find-Bash {
    <#
    .SYNOPSIS
        Detection chain 8-path per bash.exe su Windows.
    .DESCRIPTION
        Cerca bash.exe in 6 path ben noti (Git for Windows machine-wide, user-scope,
        scoop, MSYS2, Cygwin) piu' PATH lookup fallback via Get-Command.
    .OUTPUTS
        String -- path assoluto a bash.exe, oppure $null se non trovato.
    #>
    [CmdletBinding()]
    param()

    $candidates = @(
        'C:\Program Files\Git\bin\bash.exe',
        'C:\Program Files (x86)\Git\bin\bash.exe',
        (Join-Path $env:LOCALAPPDATA 'Programs\Git\bin\bash.exe'),
        (Join-Path $env:USERPROFILE 'scoop\apps\git\current\bin\bash.exe'),
        'C:\msys64\usr\bin\bash.exe',
        'C:\cygwin64\bin\bash.exe'
    )

    foreach ($path in $candidates) {
        if (Test-Path -LiteralPath $path) {
            return $path
        }
    }

    $cmd = Get-Command -Name 'bash' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd -and $cmd.Source) {
        return $cmd.Source
    }

    return $null
}
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
