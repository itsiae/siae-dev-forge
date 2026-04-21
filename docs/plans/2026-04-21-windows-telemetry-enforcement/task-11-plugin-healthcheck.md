# Task 11 — Install-ClaudePlugin + Invoke-HealthCheck + Main flow

**PR:** PR-1 | **SP:** 0.4 SP-Augmented | **Dipendenze:** T02-T10 | **Stato:** [PENDING]

## File coinvolti

- `install.ps1` (modifica: `Install-ClaudePlugin`, `Invoke-HealthCheck`, main flow completo)
- `tests/install-ps1/HealthCheck.Tests.ps1` (nuovo)

## Step 1 — Test RED

File: `tests/install-ps1/HealthCheck.Tests.ps1`

```powershell
#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

Describe "Install-ClaudePlugin" {
    It "ritorna $true se claude CLI presente + plugin install riesce" {
        Mock Get-Command { [pscustomobject]@{ Source = 'claude.exe' } } -ParameterFilter { $Name -eq 'claude' }
        Mock Invoke-DevForgeCommand { "installed" } -Verifiable
        Install-ClaudePlugin | Should -Be $true
        Should -Invoke Invoke-DevForgeCommand -ParameterFilter {
            $Command -match 'claude plugin install' -and $Command -match 'siae-devforge'
        }
    }
    It "ritorna $false se claude CLI non presente" {
        Mock Get-Command { $null } -ParameterFilter { $Name -eq 'claude' }
        Install-ClaudePlugin | Should -Be $false
    }
}

Describe "Invoke-HealthCheck" {
    BeforeEach {
        $script:testStateDir = Join-Path $env:TEMP "devforge-hc-$(Get-Random)"
        New-Item -ItemType Directory -Path (Join-Path $script:testStateDir 'devforge-state') -Force | Out-Null
        $script:testActivityLog = Join-Path $script:testStateDir 'devforge-activity.jsonl'
    }
    AfterEach {
        Remove-Item -Path $script:testStateDir -Recurse -Force -ErrorAction SilentlyContinue
    }

    It "esegue session-start dry-run con DEVFORGE_HEALTH_CHECK=1 e verifica event emesso" {
        Mock Start-Process {
            # Simula session-start che emette un event
            Set-Content -Path $script:testActivityLog -Value '{"event":"session_start","schema_version":2}'
            [pscustomobject]@{ ExitCode = 0 }
        } -Verifiable
        Mock Join-Path { $script:testActivityLog } -ParameterFilter { $ChildPath -eq '.claude\devforge-activity.jsonl' }

        $result = Invoke-HealthCheck -BashPath 'C:\Program Files\Git\bin\bash.exe' -PythonPath 'C:\Python\python.exe'
        $result | Should -Be $true
    }
    It "ritorna $false se session-start non emette event entro 5s" {
        Mock Start-Process { [pscustomobject]@{ ExitCode = 0 } }
        Mock Test-Path { $false }  # activity.jsonl non viene mai creato
        Invoke-HealthCheck -BashPath 'bash.exe' -PythonPath 'python.exe' | Should -Be $false
    }
}
```

## Step 2 — Run (RED)

```powershell
Invoke-Pester tests/install-ps1/HealthCheck.Tests.ps1
# Atteso: 4 Failed
```

## Step 3 — Impl

Sostituisci in `install.ps1`:

```powershell
function Install-ClaudePlugin {
    [CmdletBinding()]
    param()

    $claude = Get-Command -Name 'claude' -ErrorAction SilentlyContinue
    if (-not $claude) {
        Write-InstallLog "claude CLI non trovato — installa Claude Code da https://docs.anthropic.com/en/docs/build-with-claude/claude-code" -Level Error
        return $false
    }

    Write-InstallLog "Install plugin DevForge via claude CLI..." -Level Info
    $cmd = 'claude plugin install siae-devforge@siae-devforge'
    $out = Invoke-DevForgeCommand -Command $cmd
    Write-InstallLog "Plugin install output: $out" -Level Info
    return $true
}

function Invoke-HealthCheck {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$BashPath,
        [Parameter(Mandatory=$true)][string]$PythonPath
    )
    Write-InstallLog "Health-check: dry-run session-start hook..." -Level Info

    $activityLog = Join-Path $env:USERPROFILE '.claude\devforge-activity.jsonl'
    # Baseline: note initial size (se esiste)
    $initialSize = 0
    if (Test-Path -LiteralPath $activityLog) {
        $initialSize = (Get-Item -LiteralPath $activityLog).Length
    }

    # Locate session-start hook dal plugin install
    $hookPath = (Get-ChildItem "$env:USERPROFILE\.claude\plugins\cache\siae-devforge" -Directory -ErrorAction SilentlyContinue |
                 Select-Object -First 1 | ForEach-Object {
                     Join-Path $_.FullName 'hooks\session-start'
                 })
    if (-not $hookPath -or -not (Test-Path -LiteralPath $hookPath)) {
        Write-InstallLog "Hook session-start non trovato in plugin cache" -Level Error
        return $false
    }

    # Esegui bash hookPath con env DEVFORGE_HEALTH_CHECK=1
    $env:DEVFORGE_HEALTH_CHECK = '1'
    try {
        $proc = Start-Process -FilePath $BashPath -ArgumentList @($hookPath) -Wait -PassThru -NoNewWindow -RedirectStandardInput 'NUL'
        if ($proc.ExitCode -ne 0) {
            Write-InstallLog "session-start exit code $($proc.ExitCode)" -Level Warning
        }
    } catch {
        Write-InstallLog "Health-check exec fallita: $_" -Level Error
        return $false
    } finally {
        Remove-Item Env:DEVFORGE_HEALTH_CHECK -ErrorAction SilentlyContinue
    }

    # Poll activity.jsonl per 5s per nuovo evento
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
```

E il **main flow completo** in fondo a `install.ps1` (sostituisce il placeholder):

```powershell
# --- MAIN FLOW ------------------------------------------------------------
if ($MyInvocation.InvocationName -ne '.') {
    $script:DevForgeDryRun = $DryRun.IsPresent

    # ARM64 early gate
    if (Invoke-Arm64Gate) { exit 0 }

    Write-InstallLog "DevForge Windows installer avviato (DryRun=$($script:DevForgeDryRun), Force=$($Force.IsPresent))" -Level Info

    $snapshot = New-InstallSnapshot
    try {
        # BASH
        $bash = Find-Bash
        if (-not $bash -or $Force) {
            Write-InstallLog "Bash non trovato — inizio install chain..." -Level Info
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

        # PYTHON3
        $python = Find-Python3
        if (-not $python -or $Force) {
            Write-InstallLog "Python3 non trovato — inizio install..." -Level Info
            $python = Install-PythonViaStandaloneEmbedded
            if (-not $python) {
                throw "Impossibile installare python3."
            }
            $snapshot.AddDir((Join-Path $env:LOCALAPPDATA 'DevForge\python'))
        }
        Write-InstallLog "Python3 disponibile: $python" -Level Info

        # JQ
        $jq = Find-Jq
        if (-not $jq -or $Force) {
            $jq = Install-JqFromAsset
            if (-not $jq) { throw "Impossibile installare jq." }
            $snapshot.AddFile($jq)
        }
        Write-InstallLog "jq disponibile: $jq" -Level Info

        # PLUGIN
        if (-not (Install-ClaudePlugin)) {
            throw "Plugin install fallito."
        }

        # HEALTH-CHECK
        if (-not (Invoke-HealthCheck -BashPath $bash -PythonPath $python)) {
            throw "Health-check fallito — telemetria non raggiunge activity.jsonl."
        }

        # Clear repair flag se presente (self-healing)
        $repairFlag = Join-Path $env:APPDATA 'Claude\devforge-needs-repair'
        if (Test-Path -LiteralPath $repairFlag) {
            Remove-Item -LiteralPath $repairFlag -Force -ErrorAction SilentlyContinue
            Write-InstallLog "Repair flag rimosso." -Level Info
        }

        Write-InstallLog "Install completato con successo." -Level Info
        Write-Host "`n✅ DevForge installato e funzionante su Windows. Riavvia Claude Code per attivare gli hook.`n" -ForegroundColor Green
        exit 0

    } catch {
        Write-InstallLog "Install fallito: $_" -Level Error
        Invoke-Rollback -Snapshot $snapshot
        Write-Host "`n❌ DevForge install fallito. Vedi log: $script:DevForgeLogFile`n" -ForegroundColor Red
        exit 1
    }
}
```

## Step 4 — Run (GREEN)

```powershell
Invoke-Pester tests/install-ps1/HealthCheck.Tests.ps1
Invoke-Pester tests/install-ps1  # full suite
# Atteso: tutti i test verdi (integrazione end-to-end)
```

## Step 5 — Commit

```bash
git add install.ps1 tests/install-ps1/HealthCheck.Tests.ps1
git commit -m "feat(windows): plugin install + health-check + main flow integration [AC-4]"
```
