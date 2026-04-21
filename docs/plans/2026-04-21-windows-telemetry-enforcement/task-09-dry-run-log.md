# Task 09 — Dry-Run mode + Write-InstallLog

**PR:** PR-1 | **SP:** 0.2 SP-Augmented | **Dipendenze:** T01 | **Stato:** [PENDING]

## File coinvolti

- `install.ps1` (modifica: `Write-InstallLog` funzionale + supporto DryRun globale)
- `tests/install-ps1/WriteInstallLog.Tests.ps1` (nuovo)

## Step 1 — Test RED

File: `tests/install-ps1/WriteInstallLog.Tests.ps1`

```powershell
#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

Describe "Write-InstallLog" {
    BeforeEach {
        $script:testLogFile = Join-Path $env:TEMP "devforge-test-log-$(Get-Random).log"
        $script:DevForgeLogFile = $script:testLogFile
    }
    AfterEach {
        Remove-Item -Path $script:testLogFile -ErrorAction SilentlyContinue
    }

    It "crea directory log se non esiste" {
        $dir = Split-Path $script:testLogFile -Parent
        Write-InstallLog -Message "test" -Level Info
        Test-Path $dir | Should -Be $true
    }
    It "scrive riga timestamped con level in file log" {
        Write-InstallLog -Message "primo messaggio" -Level Info
        $content = Get-Content $script:testLogFile
        $content | Should -Match '\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\]'
        $content | Should -Match '\[INFO\]'
        $content | Should -Match 'primo messaggio'
    }
    It "accetta level Warning e Error" {
        Write-InstallLog -Message "warn msg" -Level Warning
        Write-InstallLog -Message "err msg" -Level Error
        $content = Get-Content $script:testLogFile -Raw
        $content | Should -Match '\[WARNING\].*warn msg'
        $content | Should -Match '\[ERROR\].*err msg'
    }
    It "default level è Info" {
        Write-InstallLog -Message "default"
        Get-Content $script:testLogFile -Raw | Should -Match '\[INFO\].*default'
    }
    It "scrive anche a Console (Write-Host) con colore per Error" {
        Mock Write-Host { } -Verifiable
        Write-InstallLog -Message "test" -Level Error
        Should -Invoke Write-Host -ParameterFilter { $ForegroundColor -eq 'Red' }
    }
}

Describe "DryRun mode" {
    It "quando `$script:DevForgeDryRun è true, Invoke-Expression NON viene eseguito" {
        $script:DevForgeDryRun = $true
        Mock Invoke-Expression { throw "should not run in dry-run" }
        try {
            { Invoke-DevForgeCommand -Command 'fake-cmd' } | Should -Not -Throw
        } finally {
            $script:DevForgeDryRun = $false
        }
    }
    It "quando DryRun false, esegue normalmente" {
        $script:DevForgeDryRun = $false
        Mock Invoke-Expression { 'ok' } -Verifiable
        Invoke-DevForgeCommand -Command 'fake-cmd' | Out-Null
        Should -Invoke Invoke-Expression
    }
}
```

## Step 2 — Run (RED)

```powershell
Invoke-Pester tests/install-ps1/WriteInstallLog.Tests.ps1
# Atteso: 7 Failed
```

## Step 3 — Impl

Sostituisci placeholder in `install.ps1`:

```powershell
# Stato globale DryRun — settato da param block nel main flow
$script:DevForgeDryRun = $false
$script:DevForgeLogFile = Join-Path $env:LOCALAPPDATA 'DevForge\install.log'

function Write-InstallLog {
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
        Wrapper per Invoke-Expression che rispetta DryRun mode.
    .PARAMETER Command
        Comando shell da eseguire.
    .OUTPUTS
        Output del comando, oppure $null in DryRun.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [string]$Command
    )
    if ($script:DevForgeDryRun) {
        Write-InstallLog "[DRY-RUN] would execute: $Command" -Level Info
        return $null
    }
    return (Invoke-Expression $Command)
}
```

Aggiungi anche (se non c'è già) wiring DryRun nel main flow scaffold:

```powershell
# Dopo param block — settaggio globale dry-run
$script:DevForgeDryRun = $DryRun.IsPresent
```

## Step 4 — Run (GREEN)

```powershell
Invoke-Pester tests/install-ps1/WriteInstallLog.Tests.ps1
# Atteso: 7/7 Passed
```

## Step 5 — Commit

```bash
git add install.ps1 tests/install-ps1/WriteInstallLog.Tests.ps1
git commit -m "feat(windows): Write-InstallLog + DryRun mode [AC-9]"
```
