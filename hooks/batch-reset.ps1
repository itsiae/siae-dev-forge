# batch-reset.ps1  -  PowerShell equivalent
# Hook: UserPromptSubmit | Matcher: * | Timeout: 5s
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "batch-reset"

$stateDir             = Join-Path $HOME ".claude"
$batchCheckpointFile  = Join-Path $stateDir ".devforge-batch-checkpoint"
$batchCounterFile     = Join-Path $stateDir ".devforge-batch-counter"

if (-not (Test-Path $batchCheckpointFile)) { exit 0 }

$age = ([DateTime]::UtcNow - (Get-Item $batchCheckpointFile).LastWriteTimeUtc).TotalSeconds
if ($age -lt 10) { exit 0 }

Remove-Item $batchCheckpointFile -Force 2>$null
Set-Content $batchCounterFile "0" -NoNewline

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null
Initialize-DevForgeSession 2>$null
Write-DevForgeLog -Event "batch_checkpoint" -Status "reset" -Meta '{"reason":"user_feedback_received"}' 2>$null

exit 0
