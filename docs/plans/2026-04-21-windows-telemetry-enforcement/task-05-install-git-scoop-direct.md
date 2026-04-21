# Task 05 — Install-GitViaScoop + Install-GitViaDirectDownload (SHA256 pin)

**PR:** PR-1 | **SP:** 0.3 SP-Augmented | **Dipendenze:** T01, T02 | **Stato:** [PENDING]

## File coinvolti

- `install.ps1` (modifica: `Install-GitViaScoop`, `Install-GitViaDirectDownload`)
- `tests/install-ps1/InstallGitScoopDirect.Tests.ps1` (nuovo)

## Versioni pinnate (aggiornare se cambia upstream)

- Git for Windows: `2.46.0` (SHA256 da `https://github.com/git-for-windows/git/releases/download/v2.46.0.windows.1/Git-2.46.0-64-bit.exe.sig`)
- URL: `https://github.com/git-for-windows/git/releases/download/v2.46.0.windows.1/Git-2.46.0-64-bit.exe`
- SHA256: recuperabile runtime dal file `.sha256` del release oppure pinnato come constante in install.ps1

## Step 1 — Test RED

File: `tests/install-ps1/InstallGitScoopDirect.Tests.ps1`

```powershell
#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

Describe "Install-GitViaScoop" {
    It "ritorna $null se scoop non disponibile" {
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'scoop' }
        Install-GitViaScoop | Should -Be $null
    }
    It "invoca scoop install git" {
        Mock Get-Command { [pscustomobject]@{ Source = 'scoop' } } -ParameterFilter { $Name -eq 'scoop' }
        Mock Invoke-Expression { $global:LASTEXITCODE = 0; '' } -Verifiable
        Mock Find-Bash { 'C:\Users\test\scoop\apps\git\current\bin\bash.exe' }
        $result = Install-GitViaScoop
        Should -Invoke Invoke-Expression -ParameterFilter { $Command -match 'scoop install git' }
        $result | Should -Be 'C:\Users\test\scoop\apps\git\current\bin\bash.exe'
    }
}

Describe "Install-GitViaDirectDownload" {
    BeforeEach {
        $script:tmp = Join-Path $env:TEMP "devforge-test-$(Get-Random)"
        New-Item -ItemType Directory -Path $script:tmp -Force | Out-Null
    }
    AfterEach {
        Remove-Item -Path $script:tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
    It "scarica installer, verifica SHA256, avvia install silent" {
        Mock Invoke-WebRequest { } -Verifiable
        Mock Get-FileHash { [pscustomobject]@{ Hash = 'EXPECTED_SHA256_HASH_UPPERCASE' } }
        Mock Start-Process { [pscustomobject]@{ ExitCode = 0 } } -Verifiable
        Mock Find-Bash { 'C:\Program Files\Git\bin\bash.exe' }
        # Override constant in test
        $script:DevForgeGitDirectSha256 = 'EXPECTED_SHA256_HASH_UPPERCASE'

        $result = Install-GitViaDirectDownload
        Should -Invoke Invoke-WebRequest
        Should -Invoke Start-Process -ParameterFilter {
            $ArgumentList -match '/VERYSILENT' -and
            $ArgumentList -match '/NORESTART' -and
            $ArgumentList -match '/COMPONENTS='
        }
        $result | Should -Be 'C:\Program Files\Git\bin\bash.exe'
    }
    It "abort se SHA256 mismatch" {
        Mock Invoke-WebRequest { }
        Mock Get-FileHash { [pscustomobject]@{ Hash = 'WRONG_HASH' } }
        Mock Start-Process { throw "Should not be called" }
        $script:DevForgeGitDirectSha256 = 'EXPECTED_SHA256_HASH_UPPERCASE'

        Install-GitViaDirectDownload | Should -Be $null
    }
}
```

## Step 2 — Run (RED)

```powershell
Invoke-Pester tests/install-ps1/InstallGitScoopDirect.Tests.ps1
# Atteso: 4 Failed
```

## Step 3 — Impl

```powershell
# Constanti pinned — aggiornare coerentemente a CI release packaging (T12)
$script:DevForgeGitDirectVersion = '2.46.0'
$script:DevForgeGitDirectUrl     = "https://github.com/git-for-windows/git/releases/download/v$($script:DevForgeGitDirectVersion).windows.1/Git-$($script:DevForgeGitDirectVersion)-64-bit.exe"
$script:DevForgeGitDirectSha256  = '0000000000000000000000000000000000000000000000000000000000000000'  # pinned in T12 CI

function Install-GitViaScoop {
    [CmdletBinding()]
    param()
    $scoop = Get-Command -Name 'scoop' -ErrorAction SilentlyContinue
    if (-not $scoop) { return $null }

    Write-InstallLog "Tentativo install Git via scoop..." -Level Info
    $global:LASTEXITCODE = 0
    Invoke-Expression 'scoop install git' 2>&1 | Out-Null

    $env:PATH = [Environment]::GetEnvironmentVariable('PATH', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('PATH', 'User')

    $bash = Find-Bash
    if ($bash) { Write-InstallLog "Git installato via scoop: $bash" -Level Info }
    return $bash
}

function Install-GitViaDirectDownload {
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
        Write-InstallLog "SHA256 mismatch: expected $expectedHash, got $actualHash — ABORT" -Level Error
        Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
        return $null
    }
    Write-InstallLog "SHA256 verificato: $actualHash" -Level Info

    # Silent install, components minimal
    $args = @('/VERYSILENT', '/NORESTART', '/COMPONENTS="gitlfs,assoc,assoc_sh"', '/NOICONS')
    $proc = Start-Process -FilePath $installerPath -ArgumentList $args -Wait -PassThru
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
```

## Step 4 — Run (GREEN)

```powershell
Invoke-Pester tests/install-ps1/InstallGitScoopDirect.Tests.ps1
# Atteso: 4/4 Passed
```

## Step 5 — Commit

```bash
git add install.ps1 tests/install-ps1/InstallGitScoopDirect.Tests.ps1
git commit -m "feat(windows): install-git via scoop + direct-download with SHA256 pin [AC-2, AC-11]"
```
