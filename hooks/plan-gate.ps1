# plan-gate.ps1  -  PowerShell equivalent
# Hook: PreToolUse | Matcher: EnterPlanMode | Timeout: 5s
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "plan-gate"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

$sessionSkills = Get-DevForgeSessionSkills
$sessionOk = ($sessionSkills -like "*siae-brainstorming*")

# Task-scope layer: shadow-log divergence (mirrors bash plan-gate)
if ($env:DEVFORGE_USE_SESSION_SCOPE -ne "1") {
    $pgTaskId = Get-DevForgeTaskId
    if ($pgTaskId) {
        $pgInvokedFile = Join-Path $HOME ".claude\.devforge-task-skills\$pgTaskId\skills_invoked"
        $pgTaskOk = (Test-Path $pgInvokedFile) -and ((Get-Content $pgInvokedFile) -contains "siae-brainstorming")
        if (($sessionOk -and -not $pgTaskOk) -or (-not $sessionOk -and $pgTaskOk)) {
            $pgSessionInt = if ($sessionOk) { 1 } else { 0 }
            $pgTaskInt    = if ($pgTaskOk)  { 1 } else { 0 }
            Write-DevForgeLog -Event "plan_gate_task_divergence" -Status "info" `
                -Meta "{`"task_id`":`"$pgTaskId`",`"session`":$pgSessionInt,`"task`":$pgTaskInt}" 2>$null
        }
    }
}

if ($sessionOk) { Write-Output '{}'; exit 0 }

Initialize-DevForgeSession 2>$null
Write-DevForgeLog -Event "plan_gate" -Status "blocked" -Meta '{"skill_missing":"siae-brainstorming"}' 2>$null

@'
{
  "decision": "block",
  "reason": "DevForge Plan Gate  -  BLOCCATO. Stai per entrare in PlanMode ma NON hai invocato siae-brainstorming in questa sessione. NESSUNA IMPLEMENTAZIONE SENZA DESIGN APPROVATO. Invoca siae-brainstorming PRIMA di procedere: Skill tool -> siae-devforge:siae-brainstorming. Dopo il brainstorming, potrai usare EnterPlanMode."
}
'@
exit 0
