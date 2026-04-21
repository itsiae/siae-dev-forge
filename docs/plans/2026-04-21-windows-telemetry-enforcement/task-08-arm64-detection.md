# Task 08 — ARM64 detection + messaggio rinvio x64

**PR:** PR-1 | **SP:** 0.1 SP-Augmented | **Dipendenze:** T01 | **Stato:** [PENDING]

## File coinvolti

- `install.ps1` (modifica: nuova funzione `Test-IsArm64` + wire nel main flow)
- `tests/install-ps1/Arm64Detection.Tests.ps1` (nuovo)

## Implementation hint (da reviewer iter-2)

Usare `PROCESSOR_ARCHITEW6432` prima di `PROCESSOR_ARCHITECTURE` — più affidabile su PS 32-bit emulato in un processo a 64-bit. Se `PROCESSOR_ARCHITEW6432` è settato → processo a 32-bit su OS 64-bit, usarlo. Altrimenti fallback su `PROCESSOR_ARCHITECTURE`.

## Step 1 — Test RED

File: `tests/install-ps1/Arm64Detection.Tests.ps1`

```powershell
#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

Describe "Test-IsArm64" {
    It "ritorna true se PROCESSOR_ARCHITEW6432=ARM64" {
        $env:PROCESSOR_ARCHITEW6432 = 'ARM64'
        try { Test-IsArm64 | Should -Be $true }
        finally { Remove-Item Env:PROCESSOR_ARCHITEW6432 -ErrorAction SilentlyContinue }
    }
    It "ritorna true se PROCESSOR_ARCHITECTURE=ARM64 e AREW6432 non settato" {
        Remove-Item Env:PROCESSOR_ARCHITEW6432 -ErrorAction SilentlyContinue
        $env:PROCESSOR_ARCHITECTURE = 'ARM64'
        try { Test-IsArm64 | Should -Be $true }
        finally { $env:PROCESSOR_ARCHITECTURE = 'AMD64' }
    }
    It "ritorna false su AMD64" {
        Remove-Item Env:PROCESSOR_ARCHITEW6432 -ErrorAction SilentlyContinue
        $env:PROCESSOR_ARCHITECTURE = 'AMD64'
        Test-IsArm64 | Should -Be $false
    }
    It "ritorna false su x86 (PROCESSOR_ARCHITEW6432 AMD64 indica emulazione su x64)" {
        $env:PROCESSOR_ARCHITEW6432 = 'AMD64'
        $env:PROCESSOR_ARCHITECTURE = 'x86'
        try { Test-IsArm64 | Should -Be $false }
        finally { Remove-Item Env:PROCESSOR_ARCHITEW6432 -ErrorAction SilentlyContinue }
    }
}
```

## Step 2 — Run (RED)

```powershell
Invoke-Pester tests/install-ps1/Arm64Detection.Tests.ps1
# Atteso: 4 Failed (function Test-IsArm64 non esiste)
```

## Step 3 — Impl

Aggiungi in `install.ps1`:

```powershell
function Test-IsArm64 {
    <#
    .SYNOPSIS
        Rileva se l'OS è ARM64 (anche se PowerShell gira in x86 emulato).
    .DESCRIPTION
        Reviewer hint T08: PROCESSOR_ARCHITEW6432 è più affidabile di
        PROCESSOR_ARCHITECTURE quando PS 32-bit gira su OS 64-bit.
        Se AREW6432 settato → indica arch reale del SO; altrimenti fallback.
    #>
    [CmdletBinding()]
    param()

    $archReal = $env:PROCESSOR_ARCHITEW6432
    if ($archReal) { return ($archReal -eq 'ARM64') }

    return ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64')
}
```

E aggiungi anche l'early exit nel main flow (commentato, sarà wired in T11):

```powershell
# Early ARM64 gate — asset sono x64-only (design §1.4 non-goal)
# Wire completo in T11 main flow
function Invoke-Arm64Gate {
    if (Test-IsArm64) {
        Write-Host "[DevForge] Architettura ARM64 rilevata." -ForegroundColor Yellow
        Write-Host "[DevForge] Install ARM64 nativo NON supportato in questa release." -ForegroundColor Yellow
        Write-Host "[DevForge] Eseguire in emulazione x64:" -ForegroundColor Yellow
        Write-Host "  Start-Process powershell -ArgumentList '-NoProfile', '-ExecutionPolicy Bypass'" -ForegroundColor Cyan
        Write-Host "[DevForge] Open issue: https://github.com/itsiae/siae-dev-forge/issues/new?title=ARM64%20native%20support" -ForegroundColor Cyan
        return $true  # gate triggered → main deve terminare
    }
    return $false
}
```

## Step 4 — Run (GREEN)

```powershell
Invoke-Pester tests/install-ps1/Arm64Detection.Tests.ps1
# Atteso: 4/4 Passed
```

## Step 5 — Commit

```bash
git add install.ps1 tests/install-ps1/Arm64Detection.Tests.ps1
git commit -m "feat(windows): ARM64 detection with PROCESSOR_ARCHITEW6432 preference [AC-15]"
```
