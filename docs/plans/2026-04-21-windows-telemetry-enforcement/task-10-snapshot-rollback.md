# Task 10 — Snapshot + Rollback transazionale

**PR:** PR-1 | **SP:** 0.4 SP-Augmented | **Dipendenze:** T09 | **Stato:** [PENDING]

## File coinvolti

- `install.ps1` (modifica: `New-InstallSnapshot`, `Invoke-Rollback`)
- `tests/install-ps1/SnapshotRollback.Tests.ps1` (nuovo)

## Design (da §5.1 + ADR-06)

Snapshot pre-install registra in memory (non persiste): file che verranno creati, registry key modificate, scheduled task creati. Se health-check post-install fallisce, rollback rimuove ogni elemento registrato nell'ordine inverso.

## Step 1 — Test RED

File: `tests/install-ps1/SnapshotRollback.Tests.ps1`

```powershell
#Requires -Version 5.1
BeforeAll { . (Join-Path $PSScriptRoot "..\..\install.ps1") }

Describe "New-InstallSnapshot" {
    It "ritorna oggetto con collezioni vuote TrackedFiles/TrackedDirs/TrackedRegistry/TrackedTasks" {
        $s = New-InstallSnapshot
        $s.TrackedFiles | Should -BeNullOrEmpty
        $s.TrackedDirs | Should -BeNullOrEmpty
        $s.TrackedRegistry | Should -BeNullOrEmpty
        $s.TrackedTasks | Should -BeNullOrEmpty
        $s.Timestamp | Should -Not -BeNullOrEmpty
    }
    It "espone i membri AddFile AddDir AddRegistry AddTask" {
        $s = New-InstallSnapshot
        $s.AddFile('C:\foo\bar.txt')
        $s.AddDir('C:\foo')
        $s.AddRegistry('HKCU:\Software\DevForge', 'InstallDate')
        $s.AddTask('DevForgeCanary')
        $s.TrackedFiles.Count | Should -Be 1
        $s.TrackedDirs.Count | Should -Be 1
        $s.TrackedRegistry.Count | Should -Be 1
        $s.TrackedTasks.Count | Should -Be 1
    }
}

Describe "Invoke-Rollback" {
    It "rimuove file tracciati in ordine inverso" {
        $tmp = Join-Path $env:TEMP "devforge-rb-$(Get-Random)"
        New-Item -ItemType Directory -Path $tmp -Force | Out-Null
        $f1 = Join-Path $tmp 'file1.txt'; $f2 = Join-Path $tmp 'file2.txt'
        Set-Content -Path $f1 -Value 'a'; Set-Content -Path $f2 -Value 'b'

        $s = New-InstallSnapshot
        $s.AddFile($f1); $s.AddFile($f2)

        Invoke-Rollback -Snapshot $s

        Test-Path $f1 | Should -Be $false
        Test-Path $f2 | Should -Be $false
        Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
    It "rimuove directory tracciate solo se vuote" {
        $tmp = Join-Path $env:TEMP "devforge-rb-$(Get-Random)"
        New-Item -ItemType Directory -Path $tmp -Force | Out-Null
        $emptyDir = Join-Path $tmp 'empty'; New-Item -ItemType Directory -Path $emptyDir | Out-Null

        $s = New-InstallSnapshot
        $s.AddDir($emptyDir)
        Invoke-Rollback -Snapshot $s

        Test-Path $emptyDir | Should -Be $false
        Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
    It "rimuove scheduled task via Unregister-ScheduledTask" {
        Mock Unregister-ScheduledTask { } -Verifiable
        Mock Get-ScheduledTask { [pscustomobject]@{ TaskName = 'DevForgeCanary' } }
        $s = New-InstallSnapshot
        $s.AddTask('DevForgeCanary')
        Invoke-Rollback -Snapshot $s
        Should -Invoke Unregister-ScheduledTask
    }
    It "logga ogni step di rollback via Write-InstallLog" {
        Mock Write-InstallLog { } -Verifiable
        $s = New-InstallSnapshot
        Invoke-Rollback -Snapshot $s
        Should -Invoke Write-InstallLog -ParameterFilter { $Message -match 'Rollback' }
    }
}
```

## Step 2 — Run (RED)

```powershell
Invoke-Pester tests/install-ps1/SnapshotRollback.Tests.ps1
# Atteso: 6 Failed
```

## Step 3 — Impl

Sostituisci placeholder in `install.ps1`:

```powershell
function New-InstallSnapshot {
    [CmdletBinding()]
    param()

    # Uso PSCustomObject con Add-Member ScriptMethod per portabilità PS 5.1
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
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [pscustomobject]$Snapshot
    )
    Write-InstallLog "Rollback avviato su snapshot $($Snapshot.Timestamp)" -Level Warning

    # 1. Unregister scheduled tasks
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

    # 2. Remove registry keys
    foreach ($reg in $Snapshot.TrackedRegistry) {
        try {
            Remove-ItemProperty -Path $reg.Key -Name $reg.Name -ErrorAction Stop
            Write-InstallLog "Rollback: remove registry $($reg.Key):$($reg.Name)" -Level Info
        } catch {
            Write-InstallLog "Rollback registry $($reg.Key) fallito: $_" -Level Error
        }
    }

    # 3. Remove files (reverse order)
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

    # 4. Remove directories (reverse order, solo se vuote)
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
```

## Step 4 — Run (GREEN)

```powershell
Invoke-Pester tests/install-ps1/SnapshotRollback.Tests.ps1
# Atteso: 6/6 Passed
```

## Step 5 — Commit

```bash
git add install.ps1 tests/install-ps1/SnapshotRollback.Tests.ps1
git commit -m "feat(windows): snapshot + rollback transazionale [AC-10]"
```
