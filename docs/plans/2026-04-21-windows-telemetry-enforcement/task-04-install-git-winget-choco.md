# Task 04 — Install-GitViaWinget + Install-GitViaChoco

**PR:** PR-1 | **SP:** 0.3 SP-Augmented | **Dipendenze:** T01, T02 | **Stato:** [PENDING]

## File coinvolti

- `install.ps1` (modifica: `Install-GitViaWinget`, `Install-GitViaChoco`)
- `tests/install-ps1/InstallGitWingetChoco.Tests.ps1` (nuovo)

## Step 1 — Test RED

File: `tests/install-ps1/InstallGitWingetChoco.Tests.ps1`

```powershell
#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

Describe "Install-GitViaWinget" {
    It "ritorna $null se winget non è disponibile" {
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'winget' }
        Install-GitViaWinget | Should -Be $null
    }
    It "invoca winget install Git.Git con scope user e flags silent" {
        Mock Get-Command { [pscustomobject]@{ Source = 'winget.exe' } } -ParameterFilter { $Name -eq 'winget' }
        Mock Invoke-Expression { '' } -Verifiable
        Mock Find-Bash { 'C:\Program Files\Git\bin\bash.exe' }
        $result = Install-GitViaWinget
        Should -Invoke Invoke-Expression -ParameterFilter {
            $Command -match 'winget install' -and
            $Command -match 'Git\.Git' -and
            $Command -match '--scope user' -and
            $Command -match '--silent' -and
            $Command -match '--accept-source-agreements' -and
            $Command -match '--accept-package-agreements'
        }
        $result | Should -Be 'C:\Program Files\Git\bin\bash.exe'
    }
    It "tratta exit code 1978335224 (already installed) come success" {
        Mock Get-Command { [pscustomobject]@{ Source = 'winget.exe' } } -ParameterFilter { $Name -eq 'winget' }
        Mock Invoke-Expression { $global:LASTEXITCODE = 1978335224; '' }
        Mock Find-Bash { 'C:\Program Files\Git\bin\bash.exe' }
        Install-GitViaWinget | Should -Be 'C:\Program Files\Git\bin\bash.exe'
    }
    It "ritorna $null su exit code non-zero non-noto + bash ancora assente" {
        Mock Get-Command { [pscustomobject]@{ Source = 'winget.exe' } } -ParameterFilter { $Name -eq 'winget' }
        Mock Invoke-Expression { $global:LASTEXITCODE = 1; '' }
        Mock Find-Bash { $null }
        Install-GitViaWinget | Should -Be $null
    }
}

Describe "Install-GitViaChoco" {
    It "ritorna $null se choco non disponibile" {
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'choco' }
        Install-GitViaChoco | Should -Be $null
    }
    It "invoca choco install git -y --no-progress" {
        Mock Get-Command { [pscustomobject]@{ Source = 'choco.exe' } } -ParameterFilter { $Name -eq 'choco' }
        Mock Invoke-Expression { $global:LASTEXITCODE = 0; '' } -Verifiable
        Mock Find-Bash { 'C:\Program Files\Git\bin\bash.exe' }
        Install-GitViaChoco | Should -Be 'C:\Program Files\Git\bin\bash.exe'
        Should -Invoke Invoke-Expression -ParameterFilter {
            $Command -match 'choco install git' -and $Command -match '-y' -and $Command -match '--no-progress'
        }
    }
}
```

## Step 2 — Run (RED)

```powershell
Invoke-Pester tests/install-ps1/InstallGitWingetChoco.Tests.ps1
# Atteso: 6 Failed
```

## Step 3 — Impl

```powershell
function Install-GitViaWinget {
    [CmdletBinding()]
    param()
    $winget = Get-Command -Name 'winget' -ErrorAction SilentlyContinue
    if (-not $winget) { return $null }

    Write-InstallLog "Tentativo install Git via winget..." -Level Info
    $cmd = 'winget install --id Git.Git -e --silent --scope user --accept-source-agreements --accept-package-agreements'
    $global:LASTEXITCODE = 0
    Invoke-Expression $cmd 2>&1 | Out-Null

    # 1978335224 = WINGET_INSTALLER_RETRY_ALREADY_INSTALLED
    # 2316632107 = APPINSTALLER_CLI_ERROR_UPDATE_NOT_APPLICABLE
    $acceptedCodes = @(0, 1978335224, 2316632107)
    if ($acceptedCodes -notcontains $LASTEXITCODE) {
        Write-InstallLog "winget fallito con exit code $LASTEXITCODE" -Level Warning
    }

    # Refresh PATH (winget install user-scope aggiorna PATH del processo corrente)
    $env:PATH = [Environment]::GetEnvironmentVariable('PATH', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('PATH', 'User')

    $bash = Find-Bash
    if ($bash) { Write-InstallLog "Git installato via winget: $bash" -Level Info }
    return $bash
}

function Install-GitViaChoco {
    [CmdletBinding()]
    param()
    $choco = Get-Command -Name 'choco' -ErrorAction SilentlyContinue
    if (-not $choco) { return $null }

    Write-InstallLog "Tentativo install Git via choco..." -Level Info
    $cmd = 'choco install git -y --no-progress'
    $global:LASTEXITCODE = 0
    Invoke-Expression $cmd 2>&1 | Out-Null

    $env:PATH = [Environment]::GetEnvironmentVariable('PATH', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('PATH', 'User')

    $bash = Find-Bash
    if ($bash) { Write-InstallLog "Git installato via choco: $bash" -Level Info }
    return $bash
}
```

**Nota:** le mock di `Write-InstallLog` in test sono silenziose — `Write-InstallLog` viene implementato in T09. Fino ad allora i test stubbano con `function Write-InstallLog { param($Message, $Level) }` nel `BeforeAll` se necessario; alternativamente T09 precede T04 nella schedule di esecuzione (v. dipendenze in overview).

## Step 4 — Run (GREEN)

```powershell
Invoke-Pester tests/install-ps1/InstallGitWingetChoco.Tests.ps1
# Atteso: 6/6 Passed
```

## Step 5 — Commit

```bash
git add install.ps1 tests/install-ps1/InstallGitWingetChoco.Tests.ps1
git commit -m "feat(windows): install-git via winget + choco cascade [AC-2]"
```
