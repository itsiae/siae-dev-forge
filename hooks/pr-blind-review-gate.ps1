# pr-blind-review-gate.ps1  -  PowerShell equivalent
# Hook: PreToolUse | Matcher: Bash | Timeout: 10s
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "pr-blind-review-gate"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

$hookInput   = Read-StdinAll
$toolCommand = Get-JsonField $hookInput "command"
if (-not $toolCommand) { $toolCommand = Get-JsonField $hookInput "tool_input.command" }
if (-not $toolCommand) { Write-Output '{}'; exit 0 }

# Mirrors bash 3-tier compound-command parser: operators, env-var prefix, cd-then-gh
$isGhPrCreateEdit = (
    $toolCommand -match '(?:^|&&|\|{2}|;)\s*(?:[A-Z_][A-Z0-9_]*=\S*\s+)*gh\s+pr\s+(create|edit)' -or
    $toolCommand -match '\benv\s+[^;|&]*gh\s+pr\s+(create|edit)' -or
    $toolCommand -match '\bcd\s+\S+\s*&&\s*gh\s+pr\s+(create|edit)'
)
if (-not $isGhPrCreateEdit) { Write-Output '{}'; exit 0 }

# Scope: itsiae/* only
$gitRoot = try { (git rev-parse --show-toplevel 2>$null).Trim() } catch { "" }
if (-not $gitRoot) { Write-Output '{}'; exit 0 }
$remoteUrl = try { (git -C $gitRoot remote get-url origin 2>$null).Trim() } catch { "" }
if ($remoteUrl -notmatch '[/:]itsiae/') { Write-Output '{}'; exit 0 }

Initialize-DevForgeSession 2>$null

# Validation: task-scoped first (skills_validated only, ADR-002 evidence-based), session fallback
# Mirrors bash devforge_skill_validated which checks skills_validated exclusively.
$validated = $false
$taskId    = Get-DevForgeTaskId
if ($taskId -and $env:DEVFORGE_USE_SESSION_SCOPE -ne "1") {
    # Check skills_validated (evidence-based, ADR-002 — no skills_invoked fallback here)
    $taskValidated = Join-Path $HOME ".claude\.devforge-task-skills\$taskId\skills_validated"
    if ((Test-Path $taskValidated) -and ((Get-Content $taskValidated) -contains "siae-blind-review")) {
        $validated = $true
    }
}
if (-not $validated) {
    $sessionSkills = Get-DevForgeSessionSkills
    if ($sessionSkills -like "*siae-blind-review*") { $validated = $true }
}

if ($validated) { Write-Output '{}'; exit 0 }

Write-DevForgeLog -Event "pr_blind_review_gate" -Status "blocked" -Meta "{`"task_id`":`"$taskId`"}" 2>$null

# Block-explainer (_BR_EXPL): adoption stats suffix (mirrors bash devforge_block_explainer)
$_BR_EXPL = ""
if ($env:DEVFORGE_DISABLE_EXPLAINER -ne "1") {
    $analyzer = Join-Path $PLUGIN_ROOT "lib\adoption-analyzer.py"
    if ((Test-Path $analyzer) -and (Get-Command python3 -ErrorAction SilentlyContinue)) {
        $line = (python3 $analyzer --format block --skill siae-blind-review 2>$null)
        if ($line) { $_BR_EXPL = " $line" }
    }
}

@"
{
  "decision": "block",
  "reason": "DevForge Blind Review Gate — BLOCCATO. Stai aprendo o modificando una PR ma NON risulta evidenza di siae-blind-review per questo task. Il blind review verifica l'allineamento spec ↔ codice con atteggiamento da auditor ostile. Invoca siae-blind-review, completa il verdict, poi riprova.$_BR_EXPL"
}
"@
exit 0
