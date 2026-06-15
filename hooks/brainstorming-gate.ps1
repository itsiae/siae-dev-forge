# brainstorming-gate.ps1  -  PowerShell equivalent
# Hook: PreToolUse | Matcher: Edit, Write | Timeout: 5s
# History: v1.45.0 NEW → v1.47.0 task-scoped + W2_DEFAULT removed (ADR-001+005+006)
#
# PR #2 changes:
#   - W2_DEFAULT=0 escape hatch removed (gate always-on; global override
#     DEVFORGE_ENFORCEMENT_OFF=1 preserved).
#   - File scope extended to .tf/.hcl via lib/file-taxonomy (inlined).
#   - Counter is task-scoped (per task_id) by default, with
#     DEVFORGE_USE_SESSION_SCOPE=1 restoring the legacy SID-anchored
#     counter for rollback.
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "brainstorming-gate"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

# ─── Global escape hatch ─────────────────────────────────────────────────────
if ($env:DEVFORGE_ENFORCEMENT_OFF -eq "1") { Write-Output '{}'; exit 0 }

$hookInput = Read-StdinAll

# ─── Extract file_path ───────────────────────────────────────────────────────
$filePath = Get-JsonField $hookInput "file_path"
if (-not $filePath) { $filePath = Get-JsonField $hookInput "tool_input.file_path" }
if (-not $filePath) { Write-Output '{}'; exit 0 }

# ─── Normalize relative → absolute ───────────────────────────────────────────
if (-not [System.IO.Path]::IsPathRooted($filePath)) {
    $filePath = Join-Path (Get-Location) $filePath
}

# ─── Walk up to nearest existing dir (needed for Write of new files) ─────────
$fileDir = Split-Path $filePath
while ($fileDir -and -not (Test-Path $fileDir -PathType Container)) {
    $fileDir = Split-Path $fileDir
}
if (-not $fileDir) { Write-Output '{}'; exit 0 }

$gitRoot = ""
try { $gitRoot = (git -C $fileDir rev-parse --show-toplevel 2>$null).Trim() } catch {}
if (-not $gitRoot) { Write-Output '{}'; exit 0 }

# ─── Scope: itsiae/* only ─────────────────────────────────────────────────────
$remote = ""
try { $remote = (git -C $gitRoot remote get-url origin 2>$null).Trim() } catch {}
if ($remote -notmatch '[/:]itsiae/') { Write-Output '{}'; exit 0 }

Initialize-DevForgeSession 2>$null

# ─── lib/block-explainer.sh inlined ──────────────────────────────────────────
# Mirrors devforge_block_explainer from lib/block-explainer.sh.
# Returns a string like " La tua adoption siae-brainstorming: 42% · team median: 78%"
# or empty string if disabled / python3 missing / analyzer missing.
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
# Mirrors _devforge_file_excluded + devforge_file_requires_brainstorming.
# Uses forward-slash normalized path for cross-platform consistent matching.
function Test-DevForgeFileExcluded {
    param([string]$Path)
    $p = $Path -replace '\\', '/'

    # Markdown always excluded
    if ($p -match '\.md$') { return $true }

    # Test directories anywhere in the path
    if ($p -match '(^|/)test/|(^|/)tests/|(^|/)__tests__/|(^|/)spec/|(^|/)docs/|(^|/)plans/|(^|/)evals/') { return $true }

    # Test file naming conventions
    if ($p -match '\.spec\.|\.test\.') { return $true }
    if ($p -match '(Test|IT)\.(java|kt)$') { return $true }
    if ($p -match '(^|/)test_[^/]+\.py$') { return $true }
    if ($p -match '_test\.go$') { return $true }

    # Named files excluded
    if ($p -match 'SKILL\.md$') { return $true }
    if ($p -match 'CLAUDE\.md$') { return $true }

    return $false
}

function Test-DevForgeFileTddRequired {
    param([string]$Path)
    $p = $Path -replace '\\', '/'
    if (Test-DevForgeFileExcluded $p) { return $false }

    if ($p -match '\.(java|ts|tsx|js|jsx|py|vue|go|kt)$') { return $true }
    if ($p -match '\.(sh|bash)$') {
        return ($env:DEVFORGE_BASH_TDD -eq "1")
    }
    return $false
}

function Test-DevForgeFileBrainstormingRequired {
    param([string]$Path)
    $p = $Path -replace '\\', '/'
    if (Test-DevForgeFileExcluded $p) { return $false }
    if ($p -match '\.(tf|hcl)$') { return $true }
    return (Test-DevForgeFileTddRequired $p)
}

# ─── File-taxonomy gate ───────────────────────────────────────────────────────
if (-not (Test-DevForgeFileBrainstormingRequired $filePath)) {
    Write-Output '{}'
    exit 0
}

# ─── Short-circuit: siae-brainstorming already invoked ───────────────────────
$sessionSkills = Get-DevForgeSessionSkills
if ($sessionSkills -like "*siae-brainstorming*") {
    # Dual-write: mirror into task-skills ledger for observability
    $taskIdForDualWrite = Get-DevForgeTaskId
    if ($taskIdForDualWrite) {
        Register-DevForgeTaskSkillInvoked -taskId $taskIdForDualWrite -skillName "siae-brainstorming" 2>$null
    }
    Write-Output '{}'
    exit 0
}

# ─── Progressive counter — task-scoped by default, SID-anchored on rollback ──
$useSessionScope = ($env:DEVFORGE_USE_SESSION_SCOPE -eq "1")
$counterKey  = ""
$counterFile = ""

if (-not $useSessionScope) {
    $taskId = Get-DevForgeTaskId
    if ($taskId) {
        $counterKey  = "task:$taskId"
        $counterDir  = Join-Path $HOME ".claude\.devforge-task-skills\$taskId"
        $counterFile = Join-Path $counterDir "brainstorm-counter"
        if (-not (Test-Path $counterDir)) {
            New-Item -ItemType Directory -Path $counterDir -Force | Out-Null
        }
    }
}

if (-not $counterFile) {
    # Rollback / non-itsiae-taskable path → legacy SID-anchored counter
    $currentSid  = Get-DevForgeSid
    $counterKey  = "sid:$currentSid"
    $counterFile = Join-Path $HOME ".claude\.devforge-brainstorm-counter"
}

$data      = if (Test-Path $counterFile) { (Get-Content $counterFile -Raw).Trim() } else { "" }
$storedKey = if ($data -and $data.Contains('|')) { $data.Split('|')[0] } else { "" }
$storedN   = if ($data -and $data.Contains('|')) { [int]$data.Split('|')[1] } else { 0 }
if ($storedKey -ne $counterKey -or -not $storedN) { $storedN = 0 }
$newN = $storedN + 1

# Atomic write via temp-then-move
$counterTmp = "$counterFile.tmp"
"$counterKey|$newN" | Set-Content $counterTmp -NoNewline
Move-Item $counterTmp $counterFile -Force

$safeFile = Convert-ToDevForgeJson $filePath
$basename = Split-Path $filePath -Leaf
$explainer = Invoke-DevForgeBlockExplainer -SkillName "siae-brainstorming"

if ($newN -eq 1) {
    Write-DevForgeLog -Event "brainstorming_nudge_soft" -Status "success" `
        -Meta "{`"file_path`":`"$safeFile`",`"counter`":1,`"scope`":`"$counterKey`"}" 2>$null
    Write-Output '{}'
    exit 0
} elseif ($newN -le 3) {
    Write-DevForgeLog -Event "brainstorming_gate_warn" -Status "success" `
        -Meta "{`"file_path`":`"$safeFile`",`"counter`":$newN,`"scope`":`"$counterKey`"}" 2>$null
    @"
{
  "decision": "block",
  "reason": "DevForge Brainstorming Nudge — ${newN}° edit senza design. Hai modificato $basename senza invocare siae-brainstorming. Skippare il design costa 3-5x rework. Opzioni: (1) Invoca Skill siae-devforge:siae-brainstorming ora, (2) Continua senza — hard block al 4°.$explainer"
}
"@
    exit 0
} else {
    Write-DevForgeLog -Event "brainstorming_gate_blocked" -Status "blocked" `
        -Meta "{`"file_path`":`"$safeFile`",`"counter`":$newN,`"scope`":`"$counterKey`",`"violation`":`"no_brainstorm`"}" 2>$null
    @"
{
  "decision": "block",
  "reason": "DevForge Brainstorming Gate — BLOCCATO. $newN edit senza siae-brainstorming. Legge di Ferro SIAE: nessuna implementazione senza design. Sblocca: Skill tool -> siae-devforge:siae-brainstorming. Se ritieni il gate inappropriato per questo caso, segnala a #devforge-support.$explainer"
}
"@
    exit 0
}
