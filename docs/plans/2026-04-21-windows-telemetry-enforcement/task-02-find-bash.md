# Task 02 — Find-Bash detection chain 8-path

**PR:** PR-1 | **SP:** 0.3 SP-Augmented | **Dipendenze:** T01 | **Stato:** [DONE]

## File coinvolti

- `install.ps1` (modifica: funzione `Find-Bash`)
- `tests/install-ps1/FindBash.Tests.ps1` (nuovo)

## Step 1 — Scrivi test RED

File: `tests/install-ps1/FindBash.Tests.ps1`

```powershell
#Requires -Version 5.1
BeforeAll {
    . (Join-Path $PSScriptRoot "..\..\install.ps1")
}

Describe "Find-Bash — 8-path detection" {
    It "restituisce path se bash in C:\Program Files\Git\bin\bash.exe" {
        Mock Test-Path { $Path -eq 'C:\Program Files\Git\bin\bash.exe' }
        Find-Bash | Should -Be 'C:\Program Files\Git\bin\bash.exe'
    }
    It "cade a (x86)\Git se Program Files assente" {
        Mock Test-Path { $Path -eq 'C:\Program Files (x86)\Git\bin\bash.exe' }
        Find-Bash | Should -Be 'C:\Program Files (x86)\Git\bin\bash.exe'
    }
    It "cade a LOCALAPPDATA user-scope install" {
        $userPath = Join-Path $env:LOCALAPPDATA 'Programs\Git\bin\bash.exe'
        Mock Test-Path { $Path -eq $userPath }
        Find-Bash | Should -Be $userPath
    }
    It "cade a scoop" {
        $scoopPath = Join-Path $env:USERPROFILE 'scoop\apps\git\current\bin\bash.exe'
        Mock Test-Path { $Path -eq $scoopPath }
        Find-Bash | Should -Be $scoopPath
    }
    It "cade a MSYS2" {
        Mock Test-Path { $Path -eq 'C:\msys64\usr\bin\bash.exe' }
        Find-Bash | Should -Be 'C:\msys64\usr\bin\bash.exe'
    }
    It "cade a Cygwin" {
        Mock Test-Path { $Path -eq 'C:\cygwin64\bin\bash.exe' }
        Find-Bash | Should -Be 'C:\cygwin64\bin\bash.exe'
    }
    It "cade a PATH lookup via Get-Command" {
        Mock Test-Path { $false }
        Mock Get-Command { [pscustomobject]@{ Source = 'D:\custom\bash.exe' } } -ParameterFilter { $Name -eq 'bash' }
        Find-Bash | Should -Be 'D:\custom\bash.exe'
    }
    It "restituisce $null se nessun path valido" {
        Mock Test-Path { $false }
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'bash' }
        Find-Bash | Should -Be $null
    }
}
```

## Step 2 — Run (aspettato RED)

```powershell
Invoke-Pester tests/install-ps1/FindBash.Tests.ps1
# Atteso: 8 Failed (Find-Bash throws 'not implemented')
```

## Step 3 — Impl

Sostituisci in `install.ps1` la funzione placeholder `Find-Bash` con:

```powershell
function Find-Bash {
    <#
    .SYNOPSIS
        Detection chain 8-path per bash.exe su Windows.
    .OUTPUTS
        String — path assoluto a bash.exe, oppure $null se non trovato.
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

    # Fallback: PATH lookup
    $cmd = Get-Command -Name 'bash' -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd -and $cmd.Source) {
        return $cmd.Source
    }

    return $null
}
```

## Step 4 — Run (aspettato GREEN)

```powershell
Invoke-Pester tests/install-ps1/FindBash.Tests.ps1
# Atteso: 8/8 Passed
```

## Step 5 — Commit

```bash
git add install.ps1 tests/install-ps1/FindBash.Tests.ps1
git commit -m "feat(windows): Find-Bash 8-path detection chain [AC-1]"
```
