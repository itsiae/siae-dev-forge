# Task 14 — Schema validator harness (byte-diff vs lib/logger.sh)

**PR:** PR-2 | **SP:** 0.3 SP-Augmented | **Dipendenze:** T13 | **Stato:** [PENDING]

## File coinvolti

- `tests/windows-runtime/schema-v2-validator.ps1` (nuovo — validator riusabile)
- `tests/windows-runtime/SchemaValidator.Tests.ps1` (nuovo — Pester test che applica validator a output reale di bash + PS)
- `tests/windows-runtime/fixtures/bash-sample-event.jsonl` (nuovo — fixture event prodotto da `lib/logger.sh` catturato a runtime)

## Perché serve

Il reviewer iter-2 ha segnalato (hint #2): "AC-6b validator schema — verificare se esiste validator bash riusabile o va sviluppato ex-novo". Verifica effettuata: **nessun validator esistente nel repo**. Va sviluppato in questo task.

Il validator serve come:
- Gate CI per AC-6b (byte-structure diff contro ground truth bash)
- Regression guard: se qualcuno modifica `lib/logger.sh` schema, il validator cattura il drift

## Step 1 — Test RED

File: `tests/windows-runtime/fixtures/bash-sample-event.jsonl`

Generato ONE-SHOT su macchina dev Mac/Linux con:

```bash
# Esegui prima dell'implementation, salva output come fixture:
export DEVFORGE_LOG_FILE=/tmp/sample.jsonl
export DEVFORGE_SESSION_DIR=/tmp/sample-session
mkdir -p "$DEVFORGE_SESSION_DIR/outbox"
source hooks/session-start  # o invoke-log helper
# Prendi la prima riga di /tmp/sample.jsonl
head -1 /tmp/sample.jsonl > tests/windows-runtime/fixtures/bash-sample-event.jsonl
```

Contenuto atteso (esempio, schema v2):
```json
{"event_id":"abc-123-0","schema_version":2,"session_seq":0,"hook_name":"session-start","actor_canonical":"lorenzo.detomasi","repo_root":"/home/runner/siae-dev-forge","project_canonical":"siae-dev-forge","ts":"2026-04-21T10:00:00.000Z","user":"lorenzo.detomasi","user_raw":"lorenzo.detomasi@outlook.com","user_source":"git_repo_email","sid":"abc-123","branch":"main","jira_id":null,"project":"siae-dev-forge","event":"session_start","status":"success","meta":{}}
```

File: `tests/windows-runtime/SchemaValidator.Tests.ps1`

```powershell
#Requires -Version 5.1
BeforeAll {
    $script:validatorPath = Join-Path $PSScriptRoot "schema-v2-validator.ps1"
    . $script:validatorPath
    $script:fixturePath = Join-Path $PSScriptRoot "fixtures\bash-sample-event.jsonl"
}

Describe "Schema v2 validator" {
    It "Test-DevForgeSchemaV2 accepts valid fixture da bash devforge_log" {
        $line = Get-Content $script:fixturePath -Raw
        $result = Test-DevForgeSchemaV2 -JsonLine $line
        $result.Valid | Should -Be $true
        $result.Errors | Should -BeNullOrEmpty
    }

    It "rejects JSON con campo top-level mancante" {
        $bad = '{"event_id":"x","schema_version":2,"session_seq":0,"hook_name":"h","actor_canonical":"u","repo_root":"","project_canonical":"","ts":"2026-04-21T10:00:00.000Z","user":"u","user_raw":"u","user_source":"s","sid":"x","branch":"","jira_id":null,"project":"","event":"e","status":"success"}'  # meta missing
        $result = Test-DevForgeSchemaV2 -JsonLine $bad
        $result.Valid | Should -Be $false
        $result.Errors | Should -Match 'meta'
    }

    It "rejects ts in formato epoch int (era il bug iter-1)" {
        $bad = '{"event_id":"x","schema_version":2,"session_seq":0,"hook_name":"h","actor_canonical":"u","repo_root":"","project_canonical":"","ts":1714680000,"user":"u","user_raw":"u","user_source":"s","sid":"x","branch":"","jira_id":null,"project":"","event":"e","status":"success","meta":{}}'
        $result = Test-DevForgeSchemaV2 -JsonLine $bad
        $result.Valid | Should -Be $false
        $result.Errors | Should -Match 'ts.*ISO-8601'
    }

    It "rejects schema_version != 2" {
        $bad = '{"event_id":"x","schema_version":1,"session_seq":0,"hook_name":"h","actor_canonical":"u","repo_root":"","project_canonical":"","ts":"2026-04-21T10:00:00.000Z","user":"u","user_raw":"u","user_source":"s","sid":"x","branch":"","jira_id":null,"project":"","event":"e","status":"success","meta":{}}'
        $result = Test-DevForgeSchemaV2 -JsonLine $bad
        $result.Valid | Should -Be $false
        $result.Errors | Should -Match 'schema_version'
    }

    It "byte-compat: output di emit-repair-event.ps1 passa il validator" {
        $emitScript = Join-Path $PSScriptRoot "..\..\hooks\emit-repair-event.ps1"
        $tmpHome = Join-Path $env:TEMP "devforge-validator-test-$(Get-Random)"
        New-Item -ItemType Directory -Path $tmpHome -Force | Out-Null
        $origUP = $env:USERPROFILE
        $env:USERPROFILE = $tmpHome
        try {
            & $emitScript
            $batch = Get-ChildItem (Join-Path $tmpHome ".claude\devforge-state\.global-outbox") -Filter 'batch-*-emergency.jsonl' | Select-Object -First 1
            $line = Get-Content $batch.FullName -Raw
            $result = Test-DevForgeSchemaV2 -JsonLine $line
            $result.Valid | Should -Be $true
            $result.Errors | Should -BeNullOrEmpty
        } finally {
            $env:USERPROFILE = $origUP
            Remove-Item $tmpHome -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}
```

## Step 2 — Run (RED)

```powershell
Invoke-Pester tests/windows-runtime/SchemaValidator.Tests.ps1
# Atteso: 5 Failed (validator non esiste)
```

## Step 3 — Impl

File: `tests/windows-runtime/schema-v2-validator.ps1`

```powershell
#Requires -Version 5.1
<#
.SYNOPSIS
    Validator schema v2 per DevForge telemetry events.
.DESCRIPTION
    Verifica che un JSON emesso rispetti lo schema v2 canonico definito in
    lib/logger.sh:440. Usato come harness di test in CI per AC-6b — assicura
    che emit-repair-event.ps1 produca output byte-compatibile con devforge_log.
#>

$script:DevForgeSchemaV2RequiredFields = @(
    'event_id', 'schema_version', 'session_seq', 'hook_name', 'actor_canonical',
    'repo_root', 'project_canonical', 'ts', 'user', 'user_raw', 'user_source',
    'sid', 'branch', 'jira_id', 'project', 'event', 'status', 'meta'
)

function Test-DevForgeSchemaV2 {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$JsonLine
    )
    $errors = [System.Collections.Generic.List[string]]::new()

    # Parse
    try {
        $obj = $JsonLine | ConvertFrom-Json -ErrorAction Stop
    } catch {
        $errors.Add("parse error: $_")
        return [pscustomobject]@{ Valid = $false; Errors = $errors }
    }

    # Required top-level fields
    foreach ($f in $script:DevForgeSchemaV2RequiredFields) {
        if (-not $obj.PSObject.Properties.Name.Contains($f)) {
            $errors.Add("missing top-level field: $f")
        }
    }

    if ($errors.Count -gt 0) {
        return [pscustomobject]@{ Valid = $false; Errors = $errors }
    }

    # schema_version must be 2
    if ($obj.schema_version -ne 2) {
        $errors.Add("schema_version must be 2, got: $($obj.schema_version)")
    }

    # ts must be ISO-8601 UTC with .000Z suffix
    if ($obj.ts -is [string]) {
        if ($obj.ts -notmatch '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$') {
            $errors.Add("ts not ISO-8601 UTC (expected YYYY-MM-DDTHH:MM:SS.sssZ): $($obj.ts)")
        }
    } else {
        $errors.Add("ts not string (ISO-8601 required), got type: $($obj.ts.GetType().Name)")
    }

    # event_id must match sid-seq pattern
    if ($obj.event_id -isnot [string] -or $obj.event_id -notmatch '^.+-\d+$') {
        $errors.Add("event_id not in 'sid-seq' format: $($obj.event_id)")
    }

    # session_seq must be int
    if ($obj.session_seq -isnot [int] -and $obj.session_seq -isnot [long]) {
        $errors.Add("session_seq not integer: $($obj.session_seq) ($($obj.session_seq.GetType().Name))")
    }

    # jira_id may be null or string (never empty string on failure, null is canonical)
    if ($obj.jira_id -ne $null -and $obj.jira_id -isnot [string]) {
        $errors.Add("jira_id must be null or string: $($obj.jira_id)")
    }

    # meta must be object (not string-escaped)
    if ($obj.meta -isnot [psobject]) {
        $errors.Add("meta must be object (not escaped string)")
    }

    return [pscustomobject]@{
        Valid  = ($errors.Count -eq 0)
        Errors = $errors
    }
}

# Export se dot-sourced non serve — le function sono auto-esposte.
```

## Step 4 — Run (GREEN)

```powershell
# Prima genera fixture reale da bash (one-shot, su macchina Mac/Linux):
# bash -c 'DEVFORGE_LOG_FILE=/tmp/s.jsonl DEVFORGE_SESSION_DIR=/tmp/s mkdir -p /tmp/s/outbox; source lib/logger.sh; devforge_log session_start success; head -1 /tmp/s.jsonl' > tests/windows-runtime/fixtures/bash-sample-event.jsonl

Invoke-Pester tests/windows-runtime/SchemaValidator.Tests.ps1
# Atteso: 5/5 Passed
```

## Step 5 — Commit

```bash
git add tests/windows-runtime/schema-v2-validator.ps1 tests/windows-runtime/SchemaValidator.Tests.ps1 tests/windows-runtime/fixtures/bash-sample-event.jsonl
git commit -m "test(windows-runtime): schema v2 validator + byte-diff vs bash fixture [AC-6b]"
```
