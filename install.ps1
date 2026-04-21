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
function Find-Python3 {
    <#
    .SYNOPSIS
        Detection di Python 3.x su Windows.
    .DESCRIPTION
        Cerca in ordine: py.exe launcher (Windows default), python3.exe, python.exe
        (solo se reporta versione 3.x via --version), cache locale DevForge.
        Usa Invoke-DevForgeCommand per il version check (no Invoke-Expression,
        splat API mockabile e sicura contro command injection).
    .OUTPUTS
        String -- path assoluto a interprete Python 3, oppure $null se non trovato.
    #>
    [CmdletBinding()]
    param()

    $cmd = Get-Command -Name 'py' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd -and $cmd.Source) { return $cmd.Source }

    $cmd = Get-Command -Name 'python3' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd -and $cmd.Source) { return $cmd.Source }

    $cmd = Get-Command -Name 'python' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd -and $cmd.Source) {
        $version = Invoke-DevForgeCommand -Executable $cmd.Source -Arguments @('--version')
        if ($version -match 'Python 3\.') { return $cmd.Source }
    }

    $cachePath = Join-Path $env:LOCALAPPDATA 'DevForge\python\python.exe'
    if (Test-Path -LiteralPath $cachePath) { return $cachePath }

    return $null
}

function Find-Jq {
    <#
    .SYNOPSIS
        Detection di jq su Windows.
    .DESCRIPTION
        Cerca jq in PATH, poi in PortableGit embedded (LOCALAPPDATA\DevForge\PortableGit\usr\bin),
        infine cache locale DevForge bin.
    .OUTPUTS
        String -- path assoluto a jq.exe, oppure $null se non trovato.
    #>
    [CmdletBinding()]
    param()

    $cmd = Get-Command -Name 'jq' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd -and $cmd.Source) { return $cmd.Source }

    $portablePath = Join-Path $env:LOCALAPPDATA 'DevForge\PortableGit\usr\bin\jq.exe'
    if (Test-Path -LiteralPath $portablePath) { return $portablePath }

    $cachePath = Join-Path $env:LOCALAPPDATA 'DevForge\bin\jq.exe'
    if (Test-Path -LiteralPath $cachePath) { return $cachePath }

    return $null
}
function Install-GitViaWinget {
    <#
    .SYNOPSIS
        Install Git-for-Windows via winget con scope user.
    .DESCRIPTION
        Invoca winget install Git.Git con flags silent e accept-agreements. Tratta
        exit code 1978335224 (WINGET_INSTALLER_RETRY_ALREADY_INSTALLED) e
        2316632107 (UPDATE_NOT_APPLICABLE) come success. Refresh PATH post-install
        da Machine+User env per rendere bash.exe visibile nella session corrente.
    .OUTPUTS
        String -- path a bash.exe post-install via Find-Bash, oppure $null su failure.
    #>
    [CmdletBinding()]
    param()
    $winget = Get-Command -Name 'winget' -ErrorAction SilentlyContinue
    if (-not $winget) { return $null }

    Write-InstallLog "Tentativo install Git via winget..." -Level Info
    $global:LASTEXITCODE = 0
    Invoke-DevForgeCommand -Executable 'winget' -Arguments @(
        'install','--id','Git.Git','-e','--silent',
        '--scope','user',
        '--accept-source-agreements','--accept-package-agreements'
    ) | Out-Null

    $acceptedCodes = @(0, 1978335224, 2316632107)
    if ($acceptedCodes -notcontains $LASTEXITCODE) {
        Write-InstallLog "winget fallito con exit code $LASTEXITCODE" -Level Warning
    }

    $env:PATH = [Environment]::GetEnvironmentVariable('PATH', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('PATH', 'User')

    $bash = Find-Bash
    if ($bash) { Write-InstallLog "Git installato via winget: $bash" -Level Info }
    return $bash
}

function Install-GitViaChoco {
    <#
    .SYNOPSIS
        Install Git-for-Windows via chocolatey.
    .DESCRIPTION
        Invoca choco install git -y --no-progress. Refresh PATH post-install.
    .OUTPUTS
        String -- path a bash.exe post-install via Find-Bash, oppure $null su failure.
    #>
    [CmdletBinding()]
    param()
    $choco = Get-Command -Name 'choco' -ErrorAction SilentlyContinue
    if (-not $choco) { return $null }

    Write-InstallLog "Tentativo install Git via choco..." -Level Info
    $global:LASTEXITCODE = 0
    Invoke-DevForgeCommand -Executable 'choco' -Arguments @('install','git','-y','--no-progress') | Out-Null

    $env:PATH = [Environment]::GetEnvironmentVariable('PATH', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('PATH', 'User')

    $bash = Find-Bash
    if ($bash) { Write-InstallLog "Git installato via choco: $bash" -Level Info }
    return $bash
}
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
