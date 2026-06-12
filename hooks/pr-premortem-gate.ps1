# pr-premortem-gate.ps1  -  PowerShell equivalent
# Hook: PreToolUse | Matcher: Bash | Timeout: 10s
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "pr-premortem-gate"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

$hookInput   = Read-StdinAll
$toolCommand = Get-JsonField $hookInput "command"
if (-not $toolCommand) { $toolCommand = Get-JsonField $hookInput "tool_input.command" }
if (-not $toolCommand) { Write-Output '{}'; exit 0 }

if ($toolCommand -notmatch '(?:^|&&|\|{2}|\;)\s*gh\s+pr\s+(create|edit)') { Write-Output '{}'; exit 0 }

# Scope: itsiae/* only
$gitRoot = try { (git rev-parse --show-toplevel 2>$null).Trim() } catch { "" }
if (-not $gitRoot) { Write-Output '{}'; exit 0 }
$remoteUrl = try { (git -C $gitRoot remote get-url origin 2>$null).Trim() } catch { "" }
if ($remoteUrl -notmatch '[/:]itsiae/') { Write-Output '{}'; exit 0 }

Initialize-DevForgeSession 2>$null

# Explicit bypass
if ($env:DEVFORGE_SKIP_PREMORTEM -eq "1") {
    $bypassFile = Join-Path $HOME ".claude\.devforge-premortem-bypass-count"
    $today      = [DateTime]::UtcNow.ToString("yyyy-MM-dd")
    $data       = if (Test-Path $bypassFile) { (Get-Content $bypassFile -Raw).Trim() } else { "" }
    $bDate      = if ($data -and $data.Contains('|')) { $data.Split('|')[0] } else { "" }
    $bCount     = if ($data -and $data.Contains('|')) { [int]$data.Split('|')[1] } else { 0 }
    if ($bDate -ne $today) { $bCount = 0 }
    $bCount++
    "$today|$bCount" | Set-Content $bypassFile -NoNewline
    Write-DevForgeLog -Event "pr_premortem_bypassed" -Status "warning" -Meta "{`"count_today`":$bCount}" 2>$null
    if ($bCount -ge 5) {
        Write-DevForgeLog -Event "pr_premortem_bypass_abuse_suspected" -Status "warning" -Meta "{`"count_today`":$bCount}" 2>$null
    }
    Write-Output '{}'; exit 0
}

# Validation: task-scoped first (skills_validated, ADR-002 evidence-based), session fallback
# Mirrors bash devforge_skill_validated: checks skills_validated, not skills_invoked.
$validated = $false
$taskId    = Get-DevForgeTaskId
if ($taskId -and $env:DEVFORGE_USE_SESSION_SCOPE -ne "1") {
    # Check skills_validated (evidence-based, ADR-002)
    $taskValidated = Join-Path $HOME ".claude\.devforge-task-skills\$taskId\skills_validated"
    if ((Test-Path $taskValidated) -and ((Get-Content $taskValidated) -contains "siae-premortem")) {
        $validated = $true
    }
}
if (-not $validated) {
    $sessionSkills = Get-DevForgeSessionSkills
    if ($sessionSkills -like "*siae-premortem*") { $validated = $true }
}

if ($validated) { Write-Output '{}'; exit 0 }

Write-DevForgeLog -Event "pr_premortem_gate" -Status "blocked" -Meta "{`"task_id`":`"$taskId`"}" 2>$null

# Block-explainer (_PM_EXPL): adoption stats suffix (mirrors bash devforge_block_explainer)
$_PM_EXPL = ""
if ($env:DEVFORGE_DISABLE_EXPLAINER -ne "1") {
    $explainerCache = Join-Path $HOME ".claude\.devforge-explainer-cache\siae-premortem"
    if (Test-Path $explainerCache) {
        $cacheMtime = (Get-Item $explainerCache).LastWriteTime
        if (([DateTime]::UtcNow - $cacheMtime).TotalSeconds -lt 86400) {
            $cached = (Get-Content $explainerCache -Raw -ErrorAction SilentlyContinue).Trim()
            if ($cached) { $_PM_EXPL = " $cached" }
        }
    }
    if (-not $_PM_EXPL) {
        $analyzer = Join-Path $PLUGIN_ROOT "lib\adoption-analyzer.py"
        if ((Test-Path $analyzer) -and (Get-Command python3 -ErrorAction SilentlyContinue)) {
            $line = (python3 $analyzer --format block --skill siae-premortem 2>$null)
            if ($line) {
                $cacheDir = Join-Path $HOME ".claude\.devforge-explainer-cache"
                if (-not (Test-Path $cacheDir)) { New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null }
                Set-Content $explainerCache $line -NoNewline
                $_PM_EXPL = " $line"
            }
        }
    }
}

@"
{
  "decision": "block",
  "reason": "DevForge Premortem Gate — BLOCCATO. Stai aprendo/modificando una PR ma NON risulta evidenza di siae-premortem per questo task. Klein premortem (HBR 2007) trova failure mode che la code review missa per hindsight bias. Invoca siae-premortem, scrivi le top-3 cause con mitigazione, poi riprova.$_PM_EXPL Bypass tracciato (5/giorno): DEVFORGE_SKIP_PREMORTEM=1 <comando> (solo hotfix/bump/revert)."
}
"@
exit 0
