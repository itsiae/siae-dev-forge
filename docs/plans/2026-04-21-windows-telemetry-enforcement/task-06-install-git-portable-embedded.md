# Task 06 — Install-GitViaPortableEmbedded (release asset x64)

**PR:** PR-1 | **SP:** 0.3 SP-Augmented | **Dipendenze:** T01, T02 | **Stato:** [PENDING]

## File coinvolti

- `install.ps1` (modifica: `Install-GitViaPortableEmbedded`)
- `tests/install-ps1/InstallGitPortableEmbedded.Tests.ps1` (nuovo)

## Fonte asset

Il file `PortableGit-2.46.0-64-bit.7z.exe` è self-extracting SFX distribuito ufficialmente da git-for-windows. URL download dal release asset del plugin (non committato in repo):

`https://github.com/itsiae/siae-dev-forge/releases/download/v<PLUGIN_VER>/PortableGit-x64.7z.exe`

Hash SHA256 pinnato nello script (aggiornato da T12 CI).

## Step 1 — Test RED

File: `tests/install-ps1/InstallGitPortableEmbedded.Tests.ps1`

```powershell
#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

Describe "Install-GitViaPortableEmbedded" {
    BeforeEach { $script:DevForgePortableGitSha256 = 'EXPECTED_HASH' }

    It "scarica asset dal release plugin, verifica SHA256, estrae in LOCALAPPDATA" {
        Mock Invoke-WebRequest { } -Verifiable
        Mock Get-FileHash { [pscustomobject]@{ Hash = 'EXPECTED_HASH' } }
        Mock Start-Process { [pscustomobject]@{ ExitCode = 0 } } -Verifiable
        $portableBash = Join-Path $env:LOCALAPPDATA 'DevForge\PortableGit\bin\bash.exe'
        Mock Test-Path { $true } -ParameterFilter { $Path -eq $portableBash }

        $result = Install-GitViaPortableEmbedded
        $result | Should -Be $portableBash
        Should -Invoke Invoke-WebRequest -ParameterFilter {
            $Uri -match 'itsiae/siae-dev-forge/releases' -and
            $Uri -match 'PortableGit-x64\.7z\.exe'
        }
        Should -Invoke Start-Process -ParameterFilter {
            $ArgumentList -match '-o' -and # output dir flag 7z SFX
            $ArgumentList -match '-y'
        }
    }
    It "abort su SHA256 mismatch" {
        Mock Invoke-WebRequest { }
        Mock Get-FileHash { [pscustomobject]@{ Hash = 'WRONG' } }
        Mock Start-Process { throw "should not run" }
        Install-GitViaPortableEmbedded | Should -Be $null
    }
    It "skip se NoPortableFallback switch attivo" {
        Mock Invoke-WebRequest { throw "should not be invoked" }
        $global:NoPortableFallbackOverride = $true
        try {
            Install-GitViaPortableEmbedded -NoPortableFallback | Should -Be $null
        } finally {
            $global:NoPortableFallbackOverride = $null
        }
    }
}
```

## Step 2 — Run (RED)

```powershell
Invoke-Pester tests/install-ps1/InstallGitPortableEmbedded.Tests.ps1
# Atteso: 3 Failed
```

## Step 3 — Impl

```powershell
$script:DevForgePortableGitUrl    = 'https://github.com/itsiae/siae-dev-forge/releases/latest/download/PortableGit-x64.7z.exe'
$script:DevForgePortableGitSha256 = '0000000000000000000000000000000000000000000000000000000000000000'  # pinned in T12 CI

function Install-GitViaPortableEmbedded {
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
        Write-InstallLog "SHA256 PortableGit mismatch: expected $expectedHash, got $actualHash — ABORT" -Level Error
        Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
        return $null
    }
    Write-InstallLog "SHA256 PortableGit verificato" -Level Info

    # Clean destination if exists (idempotent)
    if (Test-Path -LiteralPath $destDir) {
        Remove-Item -LiteralPath $destDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null

    # 7-zip SFX auto-extract silent flags
    $args = @('-o' + $destDir, '-y')
    $proc = Start-Process -FilePath $sfxPath -ArgumentList $args -Wait -PassThru
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
```

## Step 4 — Run (GREEN)

```powershell
Invoke-Pester tests/install-ps1/InstallGitPortableEmbedded.Tests.ps1
# Atteso: 3/3 Passed
```

## Step 5 — Commit

```bash
git add install.ps1 tests/install-ps1/InstallGitPortableEmbedded.Tests.ps1
git commit -m "feat(windows): install-git via PortableGit embedded release asset [AC-3, AC-11]"
```
