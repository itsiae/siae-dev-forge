# plan-gate-write.ps1  -  PowerShell equivalent
# Hook: PreToolUse | Matcher: Write | Timeout: 5s
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "plan-gate-write"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

$hookInput = Read-StdinAll
$filePath  = Get-JsonField $hookInput "file_path"
if (-not $filePath) { $filePath = Get-JsonField $hookInput "tool_input.file_path" }
if (-not $filePath) { Write-Output '{}'; exit 0 }

$normPath = $filePath -replace '\\', '/'
if ($normPath -notmatch '(^|/)docs/plans/[^/]+-design\.md$') { Write-Output '{}'; exit 0 }

if (-not [System.IO.Path]::IsPathRooted($filePath)) {
    $filePath = Join-Path (Get-Location) $filePath
}
$fileDir = Split-Path $filePath
while ($fileDir -and -not (Test-Path $fileDir -PathType Container)) { $fileDir = Split-Path $fileDir }
if (-not $fileDir) { Write-Output '{}'; exit 0 }

$gitRoot = ""
try { $gitRoot = (git -C $fileDir rev-parse --show-toplevel 2>$null).Trim() } catch {}
if (-not $gitRoot) { Write-Output '{}'; exit 0 }
$remote = ""
try { $remote = (git -C $gitRoot remote get-url origin 2>$null).Trim() } catch {}
if ($remote -notmatch '[/:]itsiae/') { Write-Output '{}'; exit 0 }

Initialize-DevForgeSession 2>$null

# Check invocation
$allow = $false
$taskId = Get-DevForgeTaskId

# Task-scope check: default path (mirrors bash USE_SESSION_SCOPE logic)
if ($env:DEVFORGE_USE_SESSION_SCOPE -ne "1") {
    if ($taskId) {
        $taskInvoked = Join-Path $HOME ".claude\.devforge-task-skills\$taskId\skills_invoked"
        if ((Test-Path $taskInvoked) -and ((Get-Content $taskInvoked) -contains "siae-brainstorming")) { $allow = $true }
    }
}

# Session-scope fallback (also the only path when USE_SESSION_SCOPE=1)
if (-not $allow) {
    $sessionSkills = Get-DevForgeSessionSkills
    if ($sessionSkills -like "*siae-brainstorming*") { $allow = $true }
}

if ($allow) { Write-Output '{}'; exit 0 }

$safeFile = Convert-ToDevForgeJson $filePath
Write-DevForgeLog -Event "plan_gate_write" -Status "blocked" -Meta "{`"file_path`":`"$safeFile`",`"skill_missing`":`"siae-brainstorming`"}" 2>$null
@"
{
  "decision": "block",
  "reason": "DevForge Plan Gate (Write) — BLOCCATO. Stai scrivendo un design doc ($filePath) ma NON hai invocato siae-brainstorming in questa sessione. NESSUN DESIGN SENZA PROCESSO. Invoca siae-brainstorming PRIMA di materializzare il design doc: Skill tool -> siae-devforge:siae-brainstorming. Questo evita che design docs siano generati ad-hoc senza i trade-off del processo."
}
"@
exit 0
