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
    if ($script:DevForgeDryRun) {
        Write-InstallLog "[DRY-RUN] would download Git-$($script:DevForgeGitDirectVersion) from $($script:DevForgeGitDirectUrl) + verify SHA256 + Inno silent install" -Level Info
        return 'C:\Program Files\Git\bin\bash.exe'
    }
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
    if ($script:DevForgeDryRun) {
        Write-InstallLog "[DRY-RUN] would download PortableGit SFX from $($script:DevForgePortableGitUrl) + SHA256 verify + extract to LOCALAPPDATA\DevForge\PortableGit" -Level Info
        return (Join-Path $env:LOCALAPPDATA 'DevForge\PortableGit\bin\bash.exe')
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
    if ($script:DevForgeDryRun) {
        Write-InstallLog "[DRY-RUN] would download Python-Standalone from $($script:DevForgePythonUrl) + SHA256 verify + tar extract to LOCALAPPDATA\DevForge\python" -Level Info
        return (Join-Path $env:LOCALAPPDATA 'DevForge\python\python.exe')
    }
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
    if ($script:DevForgeDryRun) {
        Write-InstallLog "[DRY-RUN] would download jq from $($script:DevForgeJqUrl) + SHA256 verify + copy to LOCALAPPDATA\DevForge\bin + PortableGit\usr\bin if present" -Level Info
        return (Join-Path $env:LOCALAPPDATA 'DevForge\bin\jq.exe')
    }
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
function Install-ClaudePlugin {
    <#
    .SYNOPSIS
        Installa il plugin DevForge via claude CLI.
    .DESCRIPTION
        Verifica presenza claude CLI in PATH; se assente fallisce early con hint
        al link ufficiale. Altrimenti invoca `claude plugin install siae-devforge@siae-devforge`
        via Invoke-DevForgeCommand splat (signature hardened post iter-2).
    .OUTPUTS
        Boolean -- $true se claude CLI presente + install invocato, $false altrimenti.
    #>
    [CmdletBinding()]
    param()

    $claude = Get-Command -Name 'claude' -ErrorAction SilentlyContinue
    if (-not $claude) {
        Write-InstallLog "claude CLI non trovato -- installa Claude Code da https://docs.anthropic.com/en/docs/build-with-claude/claude-code" -Level Error
        return $false
    }

    Write-InstallLog "Install plugin DevForge via claude CLI..." -Level Info
    $out = Invoke-DevForgeCommand -Executable 'claude' -Arguments @('plugin','install','siae-devforge@siae-devforge')
    Write-InstallLog "Plugin install output: $out" -Level Info
    return $true
}

function Invoke-HealthCheck {
    <#
    .SYNOPSIS
        Dry-run health-check end-to-end della pipeline telemetria.
    .DESCRIPTION
        Localizza session-start hook in ~/.claude/plugins/cache/siae-devforge/<ver>/hooks/,
        lo esegue via bash con env DEVFORGE_HEALTH_CHECK=1, poi polla
        ~/.claude/devforge-activity.jsonl per 5s per rilevare event emission
        (baseline size delta). Ritorna $false su: hook mancante, exec fallita,
        zero event emessi entro deadline.
    .PARAMETER BashPath
        Path assoluto a bash.exe (da Find-Bash / install chain).
    .PARAMETER PythonPath
        Path assoluto a python3 (da Find-Python3 / install chain).
    .OUTPUTS
        Boolean -- $true se health-check passa, $false su qualsiasi failure.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$BashPath,
        [Parameter(Mandatory=$true)][string]$PythonPath
    )
    if ($script:DevForgeDryRun) {
        Write-InstallLog "[DRY-RUN] would execute session-start hook via $BashPath + poll activity.jsonl 5s for event emission" -Level Info
        return $true
    }
    Write-InstallLog "Health-check: dry-run session-start hook..." -Level Info

    $activityLog = Join-Path $env:USERPROFILE '.claude\devforge-activity.jsonl'
    $initialSize = 0
    if (Test-Path -LiteralPath $activityLog) {
        $initialSize = (Get-Item -LiteralPath $activityLog).Length
    }

    $pluginDir = (Get-ChildItem "$env:USERPROFILE\.claude\plugins\cache\siae-devforge" -Directory -ErrorAction SilentlyContinue |
                  Select-Object -First 1)
    $hookPath = $null
    if ($pluginDir) {
        $hookPath = Join-Path $pluginDir.FullName 'hooks\session-start'
    }
    if (-not $hookPath -or -not (Test-Path -LiteralPath $hookPath)) {
        Write-InstallLog "Hook session-start non trovato in plugin cache" -Level Error
        return $false
    }

    $env:DEVFORGE_HEALTH_CHECK = '1'
    try {
        $proc = Start-Process -FilePath $BashPath -ArgumentList @($hookPath) -Wait -PassThru -NoNewWindow
        if ($proc.ExitCode -ne 0) {
            Write-InstallLog "session-start exit code $($proc.ExitCode)" -Level Warning
        }
    } catch {
        Write-InstallLog "Health-check exec fallita: $_" -Level Error
        return $false
    } finally {
        Remove-Item Env:DEVFORGE_HEALTH_CHECK -ErrorAction SilentlyContinue
    }

    $deadline = (Get-Date).AddSeconds(5)
    while ((Get-Date) -lt $deadline) {
        if (Test-Path -LiteralPath $activityLog) {
            $currentSize = (Get-Item -LiteralPath $activityLog).Length
            if ($currentSize -gt $initialSize) {
                Write-InstallLog "Health-check OK: event emesso in activity.jsonl (+$($currentSize - $initialSize) bytes)" -Level Info
                return $true
            }
        }
        Start-Sleep -Milliseconds 200
    }
    Write-InstallLog "Health-check FAILED: nessun event emesso entro 5s" -Level Error
    return $false
}
function New-InstallSnapshot {
    <#
    .SYNOPSIS
        Crea uno snapshot in-memory degli elementi introdotti dall'installer.
    .DESCRIPTION
        Tracking transazionale per rollback su health-check failure. Espone
        AddFile/AddDir/AddRegistry/AddTask come ScriptMethod (PS 5.1 compatible).
        Snapshot NON persiste su disco (memoria per install lifecycle).
    .OUTPUTS
        PSCustomObject con Timestamp + 4 collezioni + 4 ScriptMethod add.
    #>
    [CmdletBinding()]
    param()

    $snap = [pscustomobject]@{
        Timestamp       = (Get-Date).ToUniversalTime().ToString('o')
        TrackedFiles    = [System.Collections.Generic.List[string]]::new()
        TrackedDirs     = [System.Collections.Generic.List[string]]::new()
        TrackedRegistry = [System.Collections.Generic.List[pscustomobject]]::new()
        TrackedTasks    = [System.Collections.Generic.List[string]]::new()
    }
    $snap | Add-Member -MemberType ScriptMethod -Name AddFile -Value {
        param($Path) $this.TrackedFiles.Add($Path) | Out-Null
    }
    $snap | Add-Member -MemberType ScriptMethod -Name AddDir -Value {
        param($Path) $this.TrackedDirs.Add($Path) | Out-Null
    }
    $snap | Add-Member -MemberType ScriptMethod -Name AddRegistry -Value {
        param($Key, $Name)
        $this.TrackedRegistry.Add([pscustomobject]@{ Key = $Key; Name = $Name }) | Out-Null
    }
    $snap | Add-Member -MemberType ScriptMethod -Name AddTask -Value {
        param($TaskName) $this.TrackedTasks.Add($TaskName) | Out-Null
    }
    return $snap
}

function Invoke-Rollback {
    <#
    .SYNOPSIS
        Rollback transazionale degli elementi tracciati in uno snapshot.
    .DESCRIPTION
        Ordine rollback: tasks -> registry -> files (reverse) -> dirs (reverse,
        solo se vuote). Ogni step logga via Write-InstallLog, non throw:
        errori per singolo item sono best-effort, non bloccano rollback complessivo.
    .PARAMETER Snapshot
        PSCustomObject prodotto da New-InstallSnapshot.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [pscustomobject]$Snapshot
    )
    Write-InstallLog "Rollback avviato su snapshot $($Snapshot.Timestamp)" -Level Warning

    foreach ($task in $Snapshot.TrackedTasks) {
        try {
            if (Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue) {
                Unregister-ScheduledTask -TaskName $task -Confirm:$false -ErrorAction Stop
                Write-InstallLog "Rollback: unregister task $task" -Level Info
            }
        } catch {
            Write-InstallLog "Rollback task $task fallito: $_" -Level Error
        }
    }

    foreach ($reg in $Snapshot.TrackedRegistry) {
        try {
            Remove-ItemProperty -Path $reg.Key -Name $reg.Name -ErrorAction Stop
            Write-InstallLog "Rollback: remove registry $($reg.Key):$($reg.Name)" -Level Info
        } catch {
            Write-InstallLog "Rollback registry $($reg.Key) fallito: $_" -Level Error
        }
    }

    $files = @($Snapshot.TrackedFiles) ; [array]::Reverse($files)
    foreach ($f in $files) {
        try {
            if (Test-Path -LiteralPath $f) {
                Remove-Item -LiteralPath $f -Force -ErrorAction Stop
                Write-InstallLog "Rollback: remove file $f" -Level Info
            }
        } catch {
            Write-InstallLog "Rollback file $f fallito: $_" -Level Error
        }
    }

    $dirs = @($Snapshot.TrackedDirs) ; [array]::Reverse($dirs)
    foreach ($d in $dirs) {
        try {
            if (Test-Path -LiteralPath $d) {
                $children = Get-ChildItem -LiteralPath $d -Force -ErrorAction SilentlyContinue
                if (-not $children) {
                    Remove-Item -LiteralPath $d -Force -ErrorAction Stop
                    Write-InstallLog "Rollback: remove empty dir $d" -Level Info
                } else {
                    Write-InstallLog "Rollback: dir $d non vuota, skip" -Level Warning
                }
            }
        } catch {
            Write-InstallLog "Rollback dir $d fallito: $_" -Level Error
        }
    }

    Write-InstallLog "Rollback completato." -Level Info
}

function Test-IsArm64 {
    <#
    .SYNOPSIS
        Rileva se l'OS e' ARM64 (anche se PowerShell gira in x86 emulato).
    .DESCRIPTION
        Reviewer hint T08: PROCESSOR_ARCHITEW6432 e' piu' affidabile di
        PROCESSOR_ARCHITECTURE quando PS 32-bit gira su OS 64-bit.
        Se AREW6432 settato -> indica arch reale del SO; altrimenti fallback
        su PROCESSOR_ARCHITECTURE (valore del processo corrente).
    .OUTPUTS
        Boolean -- $true se OS e' ARM64, altrimenti $false.
    #>
    [CmdletBinding()]
    param()

    $archReal = $env:PROCESSOR_ARCHITEW6432
    if ($archReal) { return ($archReal -eq 'ARM64') }

    return ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64')
}

function Invoke-Arm64Gate {
    <#
    .SYNOPSIS
        Early exit gate per ARM64: asset sono x64-only (design non-goal).
    .DESCRIPTION
        Wire completo nel main flow in T11. Ritorna $true se il gate e' stato
        triggered (ARM64 rilevato, messaggi stampati) e il caller deve terminare
        lo script con exit code non-fatal (info, non errore).
    .OUTPUTS
        Boolean -- $true se gate triggered (ARM64), $false se OS x64 e si procede.
    #>
    [CmdletBinding()]
    param()

    if (Test-IsArm64) {
        Write-Host "[DevForge] Architettura ARM64 rilevata." -ForegroundColor Yellow
        Write-Host "[DevForge] Install ARM64 nativo NON supportato in questa release." -ForegroundColor Yellow
        Write-Host "[DevForge] Eseguire in emulazione x64:" -ForegroundColor Yellow
        Write-Host "  Start-Process powershell -ArgumentList '-NoProfile', '-ExecutionPolicy Bypass'" -ForegroundColor Cyan
        Write-Host "[DevForge] Open issue: https://github.com/itsiae/siae-dev-forge/issues/new?title=ARM64%20native%20support" -ForegroundColor Cyan
        return $true
    }
    return $false
}

# --- MAIN FLOW ------------------------------------------------------------
if ($MyInvocation.InvocationName -ne '.') {
    $script:DevForgeDryRun = $DryRun.IsPresent

    if (Invoke-Arm64Gate) { exit 0 }

    Write-InstallLog "DevForge Windows installer avviato (DryRun=$($script:DevForgeDryRun), Force=$($Force.IsPresent))" -Level Info

    $snapshot = New-InstallSnapshot
    try {
        $bash = Find-Bash
        if (-not $bash -or $Force) {
            Write-InstallLog "Bash non trovato -- inizio install chain..." -Level Info
            $bash = Install-GitViaWinget
            if (-not $bash) { $bash = Install-GitViaChoco }
            if (-not $bash) { $bash = Install-GitViaScoop }
            if (-not $bash) { $bash = Install-GitViaDirectDownload }
            if (-not $bash) { $bash = Install-GitViaPortableEmbedded -NoPortableFallback:$NoPortableFallback }
            if (-not $bash) {
                throw "Impossibile installare bash: tutti i metodi falliti. Vedi log: $script:DevForgeLogFile"
            }
            $snapshot.AddDir((Join-Path $env:LOCALAPPDATA 'DevForge\PortableGit'))
        }
        Write-InstallLog "Bash disponibile: $bash" -Level Info

        $python = Find-Python3
        if (-not $python -or $Force) {
            Write-InstallLog "Python3 non trovato -- inizio install..." -Level Info
            $python = Install-PythonViaStandaloneEmbedded
            if (-not $python) {
                throw "Impossibile installare python3."
            }
            $snapshot.AddDir((Join-Path $env:LOCALAPPDATA 'DevForge\python'))
        }
        Write-InstallLog "Python3 disponibile: $python" -Level Info

        $jq = Find-Jq
        if (-not $jq -or $Force) {
            $jq = Install-JqFromAsset
            if (-not $jq) { throw "Impossibile installare jq." }
            $snapshot.AddFile($jq)
        }
        Write-InstallLog "jq disponibile: $jq" -Level Info

        if (-not (Install-ClaudePlugin)) {
            throw "Plugin install fallito."
        }

        if (-not (Invoke-HealthCheck -BashPath $bash -PythonPath $python)) {
            throw "Health-check fallito -- telemetria non raggiunge activity.jsonl."
        }

        $repairFlag = Join-Path $env:APPDATA 'Claude\devforge-needs-repair'
        if (Test-Path -LiteralPath $repairFlag) {
            Remove-Item -LiteralPath $repairFlag -Force -ErrorAction SilentlyContinue
            Write-InstallLog "Repair flag rimosso." -Level Info
        }

        Write-InstallLog "Install completato con successo." -Level Info
        Write-Host "`n[OK] DevForge installato e funzionante su Windows. Riavvia Claude Code per attivare gli hook.`n" -ForegroundColor Green
        exit 0

    } catch {
        Write-InstallLog "Install fallito: $_" -Level Error
        Invoke-Rollback -Snapshot $snapshot
        Write-Host "`n[FAIL] DevForge install fallito. Vedi log: $script:DevForgeLogFile`n" -ForegroundColor Red
        exit 1
    }
}
