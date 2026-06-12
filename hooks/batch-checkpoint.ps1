# batch-checkpoint.ps1  -  PowerShell equivalent
# Hook: PostToolUse | Matcher: Bash | Timeout: 5s
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "batch-checkpoint"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

$BATCH_SIZE            = 3
$stateDir              = Join-Path $HOME ".claude"
$batchCounterFile      = Join-Path $stateDir ".devforge-batch-counter"
$batchCheckpointFile   = Join-Path $stateDir ".devforge-batch-checkpoint"

$hookInput   = Read-StdinAll
$toolCommand = Get-JsonField $hookInput "command"
if (-not $toolCommand) { $toolCommand = Get-JsonField $hookInput "tool_input.command" }

# Only care about git commits marking plan tasks DONE
if ($toolCommand -notmatch 'git\s+commit') { Write-Output '{}'; exit 0 }
if ($toolCommand -notmatch '(docs\(plans\)|docs/plans/|task\s+\d+.*DONE|mark.*task.*DONE)') { Write-Output '{}'; exit 0 }

$sessionSkills = Get-DevForgeSessionSkills
if ($sessionSkills -notlike "*siae-executing-plans*") { Write-Output '{}'; exit 0 }

# Blocked: checkpoint pending
if (Test-Path $batchCheckpointFile) {
    Initialize-DevForgeSession 2>$null
    $completed = if (Test-Path $batchCounterFile) { [int](Get-Content $batchCounterFile -Raw).Trim() } else { 0 }
    Write-DevForgeLog -Event "batch_checkpoint" -Status "blocked" `
        -Meta "{`"completed_tasks`":$completed,`"batch_size`":$BATCH_SIZE}" 2>$null
    @"
{
  "decision": "block",
  "reason": "DevForge Batch Checkpoint — BLOCCATO. Hai completato $completed task (batch di $BATCH_SIZE). DEVI presentare il report post-batch e attendere feedback dall'utente PRIMA di procedere con il prossimo batch. Formato report: BATCH COMPLETATO: Task [N]-[M] + Implementato + Stato piano + Verifica + Prossimo batch."
}
"@
    exit 0
}

# Increment counter
$current = if (Test-Path $batchCounterFile) { [int](Get-Content $batchCounterFile -Raw).Trim() } else { 0 }
$current++
$current | Set-Content $batchCounterFile -NoNewline

if ($current -ge $BATCH_SIZE) {
    $ts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    "checkpoint_at=$ts|tasks=$current" | Set-Content $batchCheckpointFile -NoNewline

    Initialize-DevForgeSession 2>$null
    Write-DevForgeLog -Event "batch_checkpoint" -Status "triggered" `
        -Meta "{`"completed_tasks`":$current,`"batch_size`":$BATCH_SIZE}" 2>$null

    $msg = "BATCH COMPLETATO ($current task). DEVI: 1) Presentare il report post-batch 2) Attendere feedback utente 3) Solo dopo il feedback, puoi procedere col prossimo batch. Per sbloccare il prossimo batch, l'utente deve dare conferma esplicita."
    $safeMsg = Convert-ToDevForgeJson $msg
    @"
{
  "additional_context": "<EXTREMELY_IMPORTANT>\nDevForge Batch Checkpoint: $safeMsg\n</EXTREMELY_IMPORTANT>"
}
"@
    exit 0
}

Write-Output '{}'
exit 0
