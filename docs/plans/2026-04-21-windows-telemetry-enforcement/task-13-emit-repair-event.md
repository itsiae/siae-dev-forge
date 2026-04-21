# Task 13 — hooks/emit-repair-event.ps1 + Pester schema v2

**PR:** PR-2 | **SP:** 0.3 SP-Augmented | **Dipendenze:** nessuna (indipendente da PR-1) | **Stato:** [PENDING]

## File coinvolti

- `hooks/emit-repair-event.ps1` (nuovo)
- `tests/windows-runtime/EmitRepairEvent.Tests.ps1` (nuovo)

## Step 1 — Test RED

File: `tests/windows-runtime/EmitRepairEvent.Tests.ps1`

```powershell
#Requires -Version 5.1

Describe "emit-repair-event.ps1 — schema v2" {
    BeforeAll {
        $script:scriptPath = Join-Path $PSScriptRoot "..\..\hooks\emit-repair-event.ps1"
        # Sandbox isolato per non toccare $HOME reale
        $script:testHome = Join-Path $env:TEMP "devforge-emit-test-$(Get-Random)"
        New-Item -ItemType Directory -Path $script:testHome -Force | Out-Null
        $script:originalUserProfile = $env:USERPROFILE
        $env:USERPROFILE = $script:testHome
    }
    AfterAll {
        $env:USERPROFILE = $script:originalUserProfile
        Remove-Item -Path $script:testHome -Recurse -Force -ErrorAction SilentlyContinue
    }

    BeforeEach {
        $globalOutbox = Join-Path $env:USERPROFILE ".claude\devforge-state\.global-outbox"
        Remove-Item -Path $globalOutbox -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item Env:DEVFORGE_DISABLE_REPAIR_EVENT -ErrorAction SilentlyContinue
    }

    It "crea .global-outbox/ se non esiste" {
        & $script:scriptPath
        $globalOutbox = Join-Path $env:USERPROFILE ".claude\devforge-state\.global-outbox"
        Test-Path $globalOutbox | Should -Be $true
        Test-Path (Join-Path $globalOutbox "acked") | Should -Be $true
    }

    It "produce file batch-<ns>-emergency.jsonl" {
        & $script:scriptPath
        $files = Get-ChildItem (Join-Path $env:USERPROFILE ".claude\devforge-state\.global-outbox") -Filter 'batch-*-emergency.jsonl'
        $files.Count | Should -Be 1
    }

    It "JSON ha tutti i 17 campi top-level dello schema v2 canonico" {
        & $script:scriptPath
        $file = Get-ChildItem (Join-Path $env:USERPROFILE ".claude\devforge-state\.global-outbox") -Filter 'batch-*-emergency.jsonl' | Select-Object -First 1
        $json = Get-Content $file.FullName -Raw | ConvertFrom-Json
        $expectedFields = @(
            'event_id','schema_version','session_seq','hook_name','actor_canonical',
            'repo_root','project_canonical','ts','user','user_raw','user_source',
            'sid','branch','jira_id','project','event','status','meta'
        )
        foreach ($f in $expectedFields) {
            $json.PSObject.Properties.Name | Should -Contain $f
        }
    }

    It "event_id ha formato sid-seq con sid='emergency-<12hex>'" {
        & $script:scriptPath
        $file = Get-ChildItem (Join-Path $env:USERPROFILE ".claude\devforge-state\.global-outbox") -Filter 'batch-*-emergency.jsonl' | Select-Object -First 1
        $json = Get-Content $file.FullName -Raw | ConvertFrom-Json
        $json.event_id | Should -Match '^emergency-[0-9a-f]{12}-0$'
        $json.sid | Should -Match '^emergency-[0-9a-f]{12}$'
        $json.session_seq | Should -Be 0
    }

    It "ts ha formato ISO-8601 UTC YYYY-MM-DDTHH:MM:SS.000Z" {
        & $script:scriptPath
        $file = Get-ChildItem (Join-Path $env:USERPROFILE ".claude\devforge-state\.global-outbox") -Filter 'batch-*-emergency.jsonl' | Select-Object -First 1
        $json = Get-Content $file.FullName -Raw | ConvertFrom-Json
        $json.ts | Should -Match '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.000Z$'
    }

    It "event = 'repair_needed' e status = 'failure'" {
        & $script:scriptPath
        $file = Get-ChildItem (Join-Path $env:USERPROFILE ".claude\devforge-state\.global-outbox") -Filter 'batch-*-emergency.jsonl' | Select-Object -First 1
        $json = Get-Content $file.FullName -Raw | ConvertFrom-Json
        $json.event | Should -Be 'repair_needed'
        $json.status | Should -Be 'failure'
        $json.hook_name | Should -Be 'run-hook-cmd'
    }

    It "meta contiene reason/os/os_release/arch/plugin_version/hostname" {
        & $script:scriptPath
        $file = Get-ChildItem (Join-Path $env:USERPROFILE ".claude\devforge-state\.global-outbox") -Filter 'batch-*-emergency.jsonl' | Select-Object -First 1
        $json = Get-Content $file.FullName -Raw | ConvertFrom-Json
        $json.meta.reason | Should -Be 'no-bash'
        $json.meta.os | Should -Be 'windows'
        $json.meta.os_release | Should -Not -BeNullOrEmpty
        $json.meta.arch | Should -Not -BeNullOrEmpty
        $json.meta.hostname | Should -Not -BeNullOrEmpty
    }

    It "actor_canonical è user lowercased" {
        & $script:scriptPath
        $file = Get-ChildItem (Join-Path $env:USERPROFILE ".claude\devforge-state\.global-outbox") -Filter 'batch-*-emergency.jsonl' | Select-Object -First 1
        $json = Get-Content $file.FullName -Raw | ConvertFrom-Json
        $json.actor_canonical | Should -Be $json.actor_canonical.ToLower()
        $json.user | Should -Be $json.actor_canonical
    }

    It "jira_id è null (JSON null literal, non stringa vuota)" {
        & $script:scriptPath
        $file = Get-ChildItem (Join-Path $env:USERPROFILE ".claude\devforge-state\.global-outbox") -Filter 'batch-*-emergency.jsonl' | Select-Object -First 1
        $raw = Get-Content $file.FullName -Raw
        $raw | Should -Match '"jira_id":null'
    }

    It "file è UTF-8 NO BOM, LF-terminated, single JSONL line" {
        & $script:scriptPath
        $file = Get-ChildItem (Join-Path $env:USERPROFILE ".claude\devforge-state\.global-outbox") -Filter 'batch-*-emergency.jsonl' | Select-Object -First 1
        $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
        # BOM check
        ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) | Should -Be $false
        # LF-terminated
        $bytes[-1] | Should -Be 0x0A
        # Single JSONL line (no CR, no double LF)
        ($bytes -contains 0x0D) | Should -Be $false
    }

    It "DEVFORGE_DISABLE_REPAIR_EVENT=1 skip emission" {
        $env:DEVFORGE_DISABLE_REPAIR_EVENT = '1'
        try {
            & $script:scriptPath
            $globalOutbox = Join-Path $env:USERPROFILE ".claude\devforge-state\.global-outbox"
            $files = @(Get-ChildItem $globalOutbox -Filter 'batch-*.jsonl' -ErrorAction SilentlyContinue)
            $files.Count | Should -Be 0
        } finally {
            Remove-Item Env:DEVFORGE_DISABLE_REPAIR_EVENT
        }
    }
}
```

## Step 2 — Run (RED)

```powershell
Invoke-Pester tests/windows-runtime/EmitRepairEvent.Tests.ps1
# Atteso: 11 Failed (script non esiste)
```

## Step 3 — Impl

File: `hooks/emit-repair-event.ps1`

```powershell
# hooks/emit-repair-event.ps1 — Emergency signal path (NO bash needed)
# Emette 1 event `repair_needed` con schema v2 canonico nel pattern
# .global-outbox/batch-<ns>-emergency.jsonl (consumato dal loop
# devforge_upload_backlog esistente — lib/telemetry-upload.sh:132-160,
# nessuna modifica agli uploader).
#
# Panic button: DEVFORGE_DISABLE_REPAIR_EVENT=1 → skip emission.
$ErrorActionPreference = 'SilentlyContinue'
if ($env:DEVFORGE_DISABLE_REPAIR_EVENT -eq '1') { exit 0 }

# .global-outbox è il path canonico per eventi stranded (telemetry-upload.sh:105)
$globalOutbox = Join-Path $env:USERPROFILE '.claude\devforge-state\.global-outbox'
New-Item -ItemType Directory -Path (Join-Path $globalOutbox 'acked') -Force | Out-Null

# Schema v2 canonico — 17 top-level fields + meta object
# Ground-truth: lib/logger.sh:440 (funzione devforge_log)
$sid     = 'emergency-' + [guid]::NewGuid().ToString('N').Substring(0, 12)
$seq     = 0
$eventId = "$sid-$seq"
$tsIso   = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.000Z')
$user    = if ($env:USERNAME) { $env:USERNAME } else { 'unknown' }

# Plugin version lookup fail-safe con "unknown" fallback
$pluginVer = 'unknown'
$pluginDir = Get-ChildItem "$env:USERPROFILE\.claude\plugins\cache\siae-devforge" -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pluginDir) {
    $pluginJson = Join-Path $pluginDir.FullName '.claude-plugin\plugin.json'
    if (Test-Path -LiteralPath $pluginJson) {
        try {
            $pluginVer = (Get-Content $pluginJson -Raw -ErrorAction Stop | ConvertFrom-Json).version
        } catch { $pluginVer = 'unknown' }
    }
}

$meta = [ordered]@{
    reason         = 'no-bash'
    os             = 'windows'
    os_release     = [Environment]::OSVersion.VersionString
    arch           = $env:PROCESSOR_ARCHITECTURE
    plugin_version = $pluginVer
    hostname       = $env:COMPUTERNAME
}

$event = [ordered]@{
    event_id          = $eventId
    schema_version    = 2
    session_seq       = $seq
    hook_name         = 'run-hook-cmd'
    actor_canonical   = $user.ToLower()
    repo_root         = ''
    project_canonical = ''
    ts                = $tsIso
    user              = $user.ToLower()
    user_raw          = $user
    user_source       = 'windows-emergency'
    sid               = $sid
    branch            = ''
    jira_id           = $null
    project           = ''
    event             = 'repair_needed'
    status            = 'failure'
    meta              = $meta
}

# Compact JSONL single-line
$jsonLine = ($event | ConvertTo-Json -Compress -Depth 5)

# Batch-pattern compatible con telemetry-upload.sh (filename matcha batch-*.jsonl glob)
$epochNs   = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() * 1000000
$batchFile = Join-Path $globalOutbox "batch-$epochNs-emergency.jsonl"

# UTF-8 no BOM, LF-terminated (matcha atomic_write.py output)
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($batchFile, $jsonLine + "`n", $utf8NoBom)
```

## Step 4 — Run (GREEN)

```powershell
Invoke-Pester tests/windows-runtime/EmitRepairEvent.Tests.ps1
# Atteso: 11/11 Passed
```

## Step 5 — Commit

```bash
git add hooks/emit-repair-event.ps1 tests/windows-runtime/EmitRepairEvent.Tests.ps1
git commit -m "feat(windows-runtime): emit-repair-event.ps1 schema v2 canonico in .global-outbox [AC-5, AC-6]"
```
