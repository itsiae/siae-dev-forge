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
$script:DevForgeGitDirectVersion = '2.46.0'
$script:DevForgeGitDirectUrl     = "https://github.com/git-for-windows/git/releases/download/v$($script:DevForgeGitDirectVersion).windows.1/Git-$($script:DevForgeGitDirectVersion)-64-bit.exe"
# Pinned by T12 CI release packaging — placeholder until release asset is cut
$script:DevForgeGitDirectSha256  = '0000000000000000000000000000000000000000000000000000000000000000'

function Install-GitViaScoop {
    <#
    .SYNOPSIS
        Install Git-for-Windows via scoop package manager.
    .DESCRIPTION
        Invoca scoop install git via Invoke-DevForgeCommand splat. Refresh PATH
        post-install per rendere bash.exe visibile nella session corrente.
    .OUTPUTS
        String -- path a bash.exe via Find-Bash, oppure $null se scoop mancante.
    #>
    [CmdletBinding()]
    param()
    $scoop = Get-Command -Name 'scoop' -ErrorAction SilentlyContinue
    if (-not $scoop) { return $null }

    Write-InstallLog "Tentativo install Git via scoop..." -Level Info
    $global:LASTEXITCODE = 0
    Invoke-DevForgeCommand -Executable 'scoop' -Arguments @('install','git') | Out-Null

    $env:PATH = [Environment]::GetEnvironmentVariable('PATH', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('PATH', 'User')

    $bash = Find-Bash
    if ($bash) { Write-InstallLog "Git installato via scoop: $bash" -Level Info }
    return $bash
}

function Install-GitViaDirectDownload {
    <#
    .SYNOPSIS
        Install Git-for-Windows via direct download con SHA256 pin.
    .DESCRIPTION
        Scarica installer pinnato (versione + URL + SHA256 in $script: vars),
        verifica hash SHA256, avvia installer silent con Inno Setup flags
        /VERYSILENT /NORESTART /COMPONENTS= minimal. Abort se hash mismatch.
    .OUTPUTS
        String -- path a bash.exe via Find-Bash, oppure $null su download/hash/install failure.
    #>
    [CmdletBinding()]
    param()
    Write-InstallLog "Tentativo direct download Git-for-Windows v$($script:DevForgeGitDirectVersion)..." -Level Info

    $tmpDir = Join-Path $env:TEMP "devforge-git-install-$(Get-Random)"
    New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
    $installerPath = Join-Path $tmpDir "Git-installer.exe"

    try {
        Invoke-WebRequest -Uri $script:DevForgeGitDirectUrl -OutFile $installerPath -UseBasicParsing -TimeoutSec 300
    } catch {
        Write-InstallLog "Download fallito: $_" -Level Error
        Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
        return $null
    }

    $actualHash = (Get-FileHash -Path $installerPath -Algorithm SHA256).Hash.ToUpper()
    $expectedHash = $script:DevForgeGitDirectSha256.ToUpper()
    if ($actualHash -ne $expectedHash) {
        Write-InstallLog "SHA256 mismatch: expected $expectedHash, got $actualHash -- ABORT" -Level Error
        Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
        return $null
    }
    Write-InstallLog "SHA256 verificato: $actualHash" -Level Info

    $innoArgs = @('/VERYSILENT', '/NORESTART', '/COMPONENTS="gitlfs,assoc,assoc_sh"', '/NOICONS')
    $proc = Start-Process -FilePath $installerPath -ArgumentList $innoArgs -Wait -PassThru
    Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue

    if ($proc.ExitCode -ne 0) {
        Write-InstallLog "Installer exit code $($proc.ExitCode)" -Level Warning
    }

    $env:PATH = [Environment]::GetEnvironmentVariable('PATH', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('PATH', 'User')

    $bash = Find-Bash
    if ($bash) { Write-InstallLog "Git installato via direct download: $bash" -Level Info }
    return $bash
}
$script:DevForgePortableGitUrl    = 'https://github.com/itsiae/siae-dev-forge/releases/latest/download/PortableGit-x64.7z.exe'
# Pinned by T12 CI release packaging -- placeholder until release asset is cut
$script:DevForgePortableGitSha256 = '0000000000000000000000000000000000000000000000000000000000000000'

function Install-GitViaPortableEmbedded {
    <#
    .SYNOPSIS
        Install PortableGit embedded da asset del release plugin (SFX 7z).
    .DESCRIPTION
        Ultima risorsa della cascade install: scarica PortableGit SFX dal release
        asset del plugin DevForge, verifica SHA256, estrae in
        LOCALAPPDATA\DevForge\PortableGit (idempotent: pulisce destdir preesistente).
        Si bypassa con switch -NoPortableFallback (air-gapped / policy restrittiva).
    .PARAMETER NoPortableFallback
        Se presente, disabilita il fallback e ritorna subito $null.
    .OUTPUTS
        String -- path a bash.exe estratto, oppure $null su skip/download/hash/extract failure.
    #>
    [CmdletBinding()]
    param(
        [switch]$NoPortableFallback
    )
    if ($NoPortableFallback) {
        Write-InstallLog "Fallback PortableGit disabilitato (-NoPortableFallback)" -Level Info
        return $null
    }

    Write-InstallLog "Tentativo install Git via PortableGit asset embedded..." -Level Info

    $tmpDir = Join-Path $env:TEMP "devforge-portable-git-$(Get-Random)"
    New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
    $sfxPath = Join-Path $tmpDir "PortableGit.7z.exe"
    $destDir = Join-Path $env:LOCALAPPDATA 'DevForge\PortableGit'

    try {
        Invoke-WebRequest -Uri $script:DevForgePortableGitUrl -OutFile $sfxPath -UseBasicParsing -TimeoutSec 600
    } catch {
        Write-InstallLog "Download PortableGit fallito: $_" -Level Error
        Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
        return $null
    }

    $actualHash = (Get-FileHash -Path $sfxPath -Algorithm SHA256).Hash.ToUpper()
    $expectedHash = $script:DevForgePortableGitSha256.ToUpper()
    if ($actualHash -ne $expectedHash) {
        Write-InstallLog "SHA256 PortableGit mismatch: expected $expectedHash, got $actualHash -- ABORT" -Level Error
        Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
        return $null
    }
    Write-InstallLog "SHA256 PortableGit verificato" -Level Info

    if (Test-Path -LiteralPath $destDir) {
        Remove-Item -LiteralPath $destDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null

    $sfxArgs = @('-o' + $destDir, '-y')
    $proc = Start-Process -FilePath $sfxPath -ArgumentList $sfxArgs -Wait -PassThru
    Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue

    if ($proc.ExitCode -ne 0) {
        Write-InstallLog "PortableGit SFX exit code $($proc.ExitCode)" -Level Warning
    }

    $bashPath = Join-Path $destDir 'bin\bash.exe'
    if (Test-Path -LiteralPath $bashPath) {
        Write-InstallLog "PortableGit estratto: $bashPath" -Level Info
        return $bashPath
    }
    Write-InstallLog "PortableGit estratto ma bash.exe non trovato in $bashPath" -Level Error
    return $null
}
$script:DevForgePythonUrl    = 'https://github.com/itsiae/siae-dev-forge/releases/latest/download/python-standalone-x64.tar.gz'
# Pinned by T12 CI release packaging -- placeholder until release asset is cut
$script:DevForgePythonSha256 = '0000000000000000000000000000000000000000000000000000000000000000'

$script:DevForgeJqUrl    = 'https://github.com/itsiae/siae-dev-forge/releases/latest/download/jq-win64.exe'
# Pinned by T12 CI release packaging -- placeholder until release asset is cut
$script:DevForgeJqSha256 = '0000000000000000000000000000000000000000000000000000000000000000'

function Install-PythonViaStandaloneEmbedded {
    <#
    .SYNOPSIS
        Install Python-Standalone (indygreg) embedded da release asset DevForge.
    .DESCRIPTION
        Scarica tar.gz mirror (python-build-standalone 3.12.x x64), verifica SHA256,
        estrae via tar.exe nativo (Win10 1803+). Abort su hash mismatch. Idempotent:
        pulisce LOCALAPPDATA\DevForge\python pre-extract.
    .OUTPUTS
        String -- path a python.exe estratto, oppure $null su failure.
    #>
    [CmdletBinding()]
    param()
    Write-InstallLog "Install Python-Standalone embedded..." -Level Info

    $tmpDir = Join-Path $env:TEMP "devforge-python-$(Get-Random)"
    New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
    $tgzPath = Join-Path $tmpDir "python.tar.gz"
    $destDir = Join-Path $env:LOCALAPPDATA 'DevForge\python'

    try {
        Invoke-WebRequest -Uri $script:DevForgePythonUrl -OutFile $tgzPath -UseBasicParsing -TimeoutSec 300
    } catch {
        Write-InstallLog "Download Python-Standalone fallito: $_" -Level Error
        Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
        return $null
    }

    $actualHash = (Get-FileHash -Path $tgzPath -Algorithm SHA256).Hash.ToUpper()
    if ($actualHash -ne $script:DevForgePythonSha256.ToUpper()) {
        Write-InstallLog "SHA256 Python mismatch -- ABORT" -Level Error
        Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
        return $null
    }

    if (Test-Path -LiteralPath $destDir) {
        Remove-Item -LiteralPath $destDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null

    $proc = Start-Process -FilePath 'tar.exe' -ArgumentList @('-xzf', $tgzPath, '-C', $destDir, '--strip-components=1') -Wait -PassThru -NoNewWindow
    Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue

    if ($proc.ExitCode -ne 0) {
        Write-InstallLog "tar extract exit code $($proc.ExitCode)" -Level Warning
    }

    $pythonExe = Join-Path $destDir 'python.exe'
    if (Test-Path -LiteralPath $pythonExe) {
        Write-InstallLog "Python-Standalone estratto: $pythonExe" -Level Info
        return $pythonExe
    }
    return $null
}

function Install-JqFromAsset {
    <#
    .SYNOPSIS
        Install jq da release asset DevForge (mirror jqlang/jq).
    .DESCRIPTION
        Scarica jq.exe in LOCALAPPDATA\DevForge\bin, verifica SHA256, abort su
        mismatch. Copia anche in PortableGit\usr\bin se presente (discoverability
        uniforme con bash toolchain).
    .OUTPUTS
        String -- path a jq.exe, oppure $null su download/hash failure.
    #>
    [CmdletBinding()]
    param()
    Write-InstallLog "Install jq da release asset..." -Level Info

    $destDir = Join-Path $env:LOCALAPPDATA 'DevForge\bin'
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    $jqPath = Join-Path $destDir 'jq.exe'

    try {
        Invoke-WebRequest -Uri $script:DevForgeJqUrl -OutFile $jqPath -UseBasicParsing -TimeoutSec 120
    } catch {
        Write-InstallLog "Download jq fallito: $_" -Level Error
        return $null
    }

    $actualHash = (Get-FileHash -Path $jqPath -Algorithm SHA256).Hash.ToUpper()
    if ($actualHash -ne $script:DevForgeJqSha256.ToUpper()) {
        Write-InstallLog "SHA256 jq mismatch -- ABORT" -Level Error
        Remove-Item $jqPath -Force -ErrorAction SilentlyContinue
        return $null
    }

    $portableUsrBin = Join-Path $env:LOCALAPPDATA 'DevForge\PortableGit\usr\bin'
    if (Test-Path -LiteralPath $portableUsrBin) {
        Copy-Item -Path $jqPath -Destination $portableUsrBin -Force -ErrorAction SilentlyContinue
        Write-InstallLog "jq copiato in $portableUsrBin" -Level Info
    }

    Write-InstallLog "jq installato: $jqPath" -Level Info
    return $jqPath
}
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
