# tdd-gate.ps1  -  PowerShell equivalent
# Hook: PreToolUse | Matcher: Edit, Write | Timeout: 5s
# History: v1.3.0 ALLOW+warn → v1.4.0 BLOCK → v1.47.0 task-scoped (ADR-001+005)
#
# Task-scoped enforcement (PR #2 ADR-001):
#   task_id = sha256(branch|latest-design-doc|mtime)[:12] per-task TDD validation.
#   Fallback: DEVFORGE_USE_SESSION_SCOPE=1 restores legacy session-scoped behavior.
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "tdd-gate"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

# ─── Track which libs actually loaded (mirrors bash _LIB_MISSING pattern) ─────
# Since file-taxonomy and block-explainer are inlined below, we track whether
# a hypothetical external version would have been loadable (always "missing"
# for the external file, since no .ps1 counterparts exist).
# We log hook_degraded only if we cannot inline the required logic — in our
# case, we always inline, so we skip the degraded log for taxonomy.
# However, we do replicate the bash pattern: if task-id lib unavailable we note it.
$_libMissing = ""
# Get-DevForgeTaskId is provided by DevForge-Helpers.psm1, so it is always present.
# If the module failed to load, flag degraded mode.
if (-not (Get-Command Get-DevForgeTaskId -ErrorAction SilentlyContinue)) {
    $_libMissing = "task-id "
}
if (-not (Get-Command Test-DevForgeTaskSkillValidated -ErrorAction SilentlyContinue)) {
    $_libMissing += "evidence-check "
}
if ($_libMissing.Trim()) {
    Write-DevForgeLog -Event "hook_degraded" -Status "warning" `
        -Meta "{`"hook`":`"tdd-gate`",`"missing`":`"$($_libMissing.Trim())`"}" 2>$null
}

$hookInput = Read-StdinAll

# ─── Extract file_path ───────────────────────────────────────────────────────
$filePath = Get-JsonField $hookInput "file_path"
if (-not $filePath) { $filePath = Get-JsonField $hookInput "tool_input.file_path" }
if (-not $filePath) { Write-Output '{}'; exit 0 }

# ─── Normalize to absolute ───────────────────────────────────────────────────
if (-not [System.IO.Path]::IsPathRooted($filePath)) {
    $filePath = Join-Path (Get-Location) $filePath
}

# ─── Walk up to nearest existing dir ─────────────────────────────────────────
$fileDir = Split-Path $filePath
while ($fileDir -and -not (Test-Path $fileDir -PathType Container)) {
    $fileDir = Split-Path $fileDir
}
if (-not $fileDir) { Write-Output '{}'; exit 0 }

# ─── Must be inside a git repo ───────────────────────────────────────────────
$gitRoot = ""
try { $gitRoot = (git -C $fileDir rev-parse --show-toplevel 2>$null).Trim() } catch {}
if (-not $gitRoot) { Write-Output '{}'; exit 0 }

# ─── Scope: itsiae/* only ─────────────────────────────────────────────────────
$remote = ""
try { $remote = (git -C $gitRoot remote get-url origin 2>$null).Trim() } catch {}
if ($remote -notmatch '[/:]itsiae/') { Write-Output '{}'; exit 0 }

# ─── lib/block-explainer.sh inlined ──────────────────────────────────────────
# Mirrors devforge_block_explainer. Returns " <line>" with leading space, or "".
function Invoke-DevForgeBlockExplainer {
    param([string]$SkillName)
    if ($env:DEVFORGE_DISABLE_EXPLAINER -eq "1") { return "" }
    if (-not $SkillName) { return "" }
    $analyzer = Join-Path $PLUGIN_ROOT "lib\adoption-analyzer.py"
    if (-not (Test-Path $analyzer)) { return "" }
    if (-not (Get-Command python3 -ErrorAction SilentlyContinue)) { return "" }

    $cacheDir = Join-Path $HOME ".claude\.devforge-explainer-cache"
    if (-not (Test-Path $cacheDir)) { New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null }
    $cacheFile = Join-Path $cacheDir $SkillName
    $ttlSec    = 86400  # 24h

    if (Test-Path $cacheFile) {
        $age = ((Get-Date) - (Get-Item $cacheFile).LastWriteTime).TotalSeconds
        if ($age -lt $ttlSec) {
            $cached = (Get-Content $cacheFile -Raw -ErrorAction SilentlyContinue).Trim()
            if ($cached) { return " $cached" }
        }
    }

    $line = (python3 $analyzer --format block --skill $SkillName 2>$null)
    if (-not $line) { return "" }
    Set-Content $cacheFile $line -NoNewline -ErrorAction SilentlyContinue
    return " $line"
}

# ─── lib/file-taxonomy.sh inlined ────────────────────────────────────────────
# Mirrors _devforge_file_excluded + devforge_file_requires_tdd.
# Includes .tf/.hcl support (brainstorming_only class — NOT tdd_required per taxonomy).
function Test-DevForgeFileExcluded {
    param([string]$Path)
    $p = $Path -replace '\\', '/'
    if ($p -match '\.md$') { return $true }
    if ($p -match '(^|/)test/|(^|/)tests/|(^|/)__tests__/|(^|/)spec/|(^|/)docs/|(^|/)plans/|(^|/)evals/') { return $true }
    if ($p -match '\.spec\.|\.test\.') { return $true }
    if ($p -match '(Test|IT)\.(java|kt)$') { return $true }
    if ($p -match '(^|/)test_[^/]+\.py$') { return $true }
    if ($p -match '_test\.go$') { return $true }
    if ($p -match '(^|/)SKILL\.md$|(^|/)CLAUDE\.md$') { return $true }
    return $false
}

function Test-DevForgeFileTddRequired {
    param([string]$Path)
    $p = $Path -replace '\\', '/'
    if (Test-DevForgeFileExcluded $p) { return $false }
    # TDD required: tdd_required class (NOT .tf/.hcl which are brainstorming_only)
    if ($p -match '\.(java|ts|tsx|js|jsx|py|vue|go|kt)$') { return $true }
    if ($p -match '\.(sh|bash)$') { return ($env:DEVFORGE_BASH_TDD -eq "1") }
    return $false
}

# ─── File-taxonomy gate ───────────────────────────────────────────────────────
if (-not (Test-DevForgeFileTddRequired $filePath)) {
    Write-Output '{}'
    exit 0
}

# ─── Check session skills ─────────────────────────────────────────────────────
$sessionSkills = Get-DevForgeSessionSkills
$skillInvoked  = ($sessionSkills -like "*siae-tdd*")

Initialize-DevForgeSession 2>$null

# ─── Task-scoped layer (default) with session-scoped rollback ─────────────────
$useSessionScope = ($env:DEVFORGE_USE_SESSION_SCOPE -eq "1")
$taskId = ""

if (-not $useSessionScope) {
    if (Get-Command Get-DevForgeTaskId -ErrorAction SilentlyContinue) {
        $taskId = ""
        try { $taskId = (& { Set-Location $gitRoot; Get-DevForgeTaskId } 2>$null) } catch {}
    }

    if ($taskId -and (Get-Command Register-DevForgeTaskSkillInvoked -ErrorAction SilentlyContinue)) {
        # Dual-write: record session skill invocations into per-task ledger (idempotent)
        if ($skillInvoked) {
            Register-DevForgeTaskSkillInvoked -taskId $taskId -skillName "siae-tdd" 2>$null
        }
    }
}

if ($skillInvoked) {
    # ─── TDD Phase State Machine ──────────────────────────────────────────────
    $tddStateFile = Join-Path $HOME ".claude\.devforge-tdd-state"
    $tddPhase = ""
    if (Test-Path $tddStateFile) {
        $tddPhase = ((Get-Content $tddStateFile -Raw).Split('|')[0]).Trim()
    }

    if ($tddPhase -eq "INIT") {
        $basename = Split-Path $filePath -Leaf
        $safeFile = Convert-ToDevForgeJson $filePath
        $taskIdJson = Convert-ToDevForgeJson $taskId
        Write-DevForgeLog -Event "tdd_gate" -Status "blocked" `
            -Meta "{`"file_path`":`"$safeFile`",`"phase`":`"INIT`",`"violation`":`"prod_code_before_test`",`"task_id`":`"$taskIdJson`"}" 2>$null
        @"
{
  "decision": "block",
  "reason": "DevForge TDD Phase Gate — BLOCCATO. Hai invocato siae-tdd ma non hai ancora un test fallente. Scrivi PRIMA il test per $basename, eseguilo (deve fallire → fase RED), poi potrai scrivere il codice di produzione."
}
"@
        exit 0
    }

    # ─── Evidence-based check (task-scoped only) ──────────────────────────────
    if ($taskId -and -not $useSessionScope) {
        if (Get-Command Test-DevForgeTaskSkillValidated -ErrorAction SilentlyContinue) {
            $validated = Test-DevForgeTaskSkillValidated -taskId $taskId -skillName "siae-tdd"
            if (-not $validated) {
                # Invoked but no RED→GREEN transition observed for THIS task.
                # Allow-with-log: phase-gate above already blocks INIT.
                Write-DevForgeLog -Event "tdd_gate_task_divergence" -Status "info" `
                    -Meta "{`"task_id`":`"$taskId`",`"session_allow`":true,`"task_validated`":false}" 2>$null
            }
        }
    }

    # RED / GREEN / REFACTOR / empty → allow
    Write-Output '{}'
    exit 0
}

# ─── siae-tdd NOT invoked — BLOCK (hard gate) ─────────────────────────────────
$basename = Split-Path $filePath -Leaf
$safeFile = Convert-ToDevForgeJson $filePath
$taskIdJson = Convert-ToDevForgeJson $taskId
Write-DevForgeLog -Event "tdd_gate" -Status "blocked" `
    -Meta "{`"file_path`":`"$safeFile`",`"skill_missing`":`"siae-tdd`",`"task_id`":`"$taskIdJson`"}" 2>$null

$explainer = Invoke-DevForgeBlockExplainer -SkillName "siae-tdd"

@"
{
  "decision": "block",
  "reason": "DevForge TDD Gate — BLOCCATO. Stai modificando codice di produzione ($basename) ma NON hai invocato siae-tdd in questa sessione. La Legge di Ferro: TEST PRIMA DEL CODICE, SEMPRE. Invoca siae-tdd PRIMA di scrivere codice di produzione: Skill tool -> siae-devforge:siae-tdd. Dopo aver invocato la skill, potrai procedere.$explainer"
}
"@
exit 0
