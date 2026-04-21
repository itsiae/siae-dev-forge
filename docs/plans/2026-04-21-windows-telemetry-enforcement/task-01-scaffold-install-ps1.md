# Task 01 — Scaffold install.ps1 + Pester harness + CI workflow Windows matrix

**PR:** PR-1 | **SP:** 0.5 SP-Augmented | **Dipendenze:** nessuna | **Stato:** [PENDING]

## File coinvolti

- `install.ps1` (nuovo, root repo — esiste già `install.sh` Mac/Linux)
- `tests/install-ps1/Install.Scaffold.Tests.ps1` (nuovo)
- `tests/install-ps1/README.md` (nuovo, 5 righe: come eseguire Pester)
- `.github/workflows/test-windows-enforcement.yml` (nuovo)

## Step 1 — Scrivi test RED (Pester 5)

File: `tests/install-ps1/Install.Scaffold.Tests.ps1`

```powershell
#Requires -Version 5.1
Describe "install.ps1 — scaffold" {
    BeforeAll {
        $script:InstallerPath = Join-Path $PSScriptRoot "..\..\install.ps1"
    }

    It "file installer esiste nella root repo" {
        Test-Path $script:InstallerPath | Should -Be $true
    }

    It "parsing senza errori sintattici (no -Force, no side-effect)" {
        $errors = $null
        [System.Management.Automation.Language.Parser]::ParseFile(
            $script:InstallerPath, [ref]$null, [ref]$errors
        ) | Out-Null
        $errors | Should -BeNullOrEmpty
    }

    It "dichiara [CmdletBinding()] e param block con DryRun/NoPortableFallback/Force" {
        $content = Get-Content $script:InstallerPath -Raw
        $content | Should -Match '\[CmdletBinding\(\)\]'
        $content | Should -Match '\[switch\]\$DryRun'
        $content | Should -Match '\[switch\]\$NoPortableFallback'
        $content | Should -Match '\[switch\]\$Force'
    }

    It "definisce le funzioni pubbliche previste dal design §5.1" {
        $content = Get-Content $script:InstallerPath -Raw
        $expected = @(
            'Find-Bash', 'Find-Python3', 'Find-Jq',
            'Install-GitViaWinget', 'Install-GitViaChoco', 'Install-GitViaScoop',
            'Install-GitViaDirectDownload', 'Install-GitViaPortableEmbedded',
            'Install-PythonViaStandaloneEmbedded', 'Install-JqFromAsset',
            'Install-ClaudePlugin', 'Invoke-HealthCheck',
            'New-InstallSnapshot', 'Invoke-Rollback', 'Write-InstallLog'
        )
        foreach ($fn in $expected) {
            $content | Should -Match "function\s+$fn\s*\{"
        }
    }
}
```

## Step 2 — Run (aspettato RED)

```powershell
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge"
Invoke-Pester tests/install-ps1/Install.Scaffold.Tests.ps1
# Atteso: Tests Failed (file install.ps1 non esiste)
```

## Step 3 — Impl

File: `install.ps1` (scaffold con funzioni placeholder che lanciano `throw 'not implemented'` — verranno riempite nei task successivi)

```powershell
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
```

File: `.github/workflows/test-windows-enforcement.yml`

```yaml
name: Test Windows Enforcement
on:
  pull_request:
    paths:
      - 'install.ps1'
      - 'hooks/run-hook.cmd'
      - 'hooks/emit-repair-event.ps1'
      - 'hooks/session-start'
      - 'tests/install-ps1/**'
      - 'tests/windows-runtime/**'
      - '.github/workflows/test-windows-enforcement.yml'

jobs:
  test-pester:
    strategy:
      fail-fast: false
      matrix:
        os: [windows-latest, windows-2019]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - name: Install Pester 5
        shell: pwsh
        run: |
          Install-Module -Name Pester -MinimumVersion 5.5.0 -Force -SkipPublisherCheck
          Import-Module Pester -MinimumVersion 5.5.0
          Get-Module Pester | Format-Table Name, Version
      - name: Run Pester tests
        shell: pwsh
        run: |
          $config = New-PesterConfiguration
          $config.Run.Path = 'tests/install-ps1'
          $config.Run.Exit = $true
          $config.Output.Verbosity = 'Detailed'
          Invoke-Pester -Configuration $config

  test-bash-regression:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - name: Install bats
        run: |
          if [ "$RUNNER_OS" = "macOS" ]; then brew install bats-core; else sudo apt-get install -y bats; fi
      - name: Run existing bash tests (zero-regression guard)
        run: bash tests/run-all.sh
```

File: `tests/install-ps1/README.md`

```markdown
# Pester tests per install.ps1

## Esecuzione locale (Windows)

```powershell
Install-Module Pester -MinimumVersion 5.5.0 -Force -SkipPublisherCheck
Invoke-Pester tests/install-ps1
```

## CI

I test girano automaticamente su `windows-latest` + `windows-2019` via `.github/workflows/test-windows-enforcement.yml`.
```

## Step 4 — Run (aspettato GREEN)

```powershell
Invoke-Pester tests/install-ps1/Install.Scaffold.Tests.ps1
# Atteso: Tests Passed — 4/4
```

## Step 5 — Commit

```bash
git add install.ps1 tests/install-ps1/ .github/workflows/test-windows-enforcement.yml
git commit -m "feat(windows): scaffold install.ps1 + Pester harness + CI matrix [AC-8]"
```
