# post-skill.ps1  -  PowerShell equivalent
# Hook: PostToolUse | Matcher: Skill | Timeout: 5s
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "post-skill"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

Initialize-DevForgeSession 2>$null

$hookInput = Read-StdinAll
$skillName = Get-JsonField $hookInput "skill"
if (-not $skillName) { $skillName = Get-JsonField $hookInput "tool_input.skill" }
if (-not $skillName) { $skillName = Get-JsonField $hookInput "name" }

if (-not $skillName) { Write-Output '{}'; exit 0 }

# --- Step 1 (CRITICAL): write session skills file FIRST ---
$sessionSkillsFile = Join-Path $HOME ".claude\.devforge-session-skills"
$existing = if (Test-Path $sessionSkillsFile) { (Get-Content $sessionSkillsFile -Raw).Trim() } else { "" }
if (-not $existing) {
    $skillName | Set-Content "$sessionSkillsFile.tmp" -NoNewline
    Move-Item "$sessionSkillsFile.tmp" $sessionSkillsFile -Force
} elseif ($existing -notlike "*$skillName*") {
    "$existing,$skillName" | Set-Content "$sessionSkillsFile.tmp" -NoNewline
    Move-Item "$sessionSkillsFile.tmp" $sessionSkillsFile -Force
}

# --- Step 1b: per-task ledger ---
$cleanSkill = if ($skillName -like "*:*") { $skillName.Split(':')[-1] } else { $skillName }
$taskId = Get-DevForgeTaskId
if ($taskId) {
    Register-DevForgeTaskSkillInvoked -TaskId $taskId -SkillName $cleanSkill 2>$null
    $taskDir = Join-Path $HOME ".claude\.devforge-task-skills\$taskId"
    $metaFile = Join-Path $taskDir "metadata"
    if (-not (Test-Path $metaFile)) {
        $branch = ""
        try { $branch = (git branch --show-current 2>$null).Trim() } catch {}
        $designDoc = ""
        if (Test-Path "docs\plans") {
            $designDoc = (Get-ChildItem "docs\plans\*-design.md" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
        }
        # Use nanoseconds for created_ns — mirrors bash _devforge_epoch_ns
        $nowNs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() * 1000000
        @"
branch_name=$branch
design_doc=$designDoc
created_ns=$nowNs
"@ | Set-Content "$metaFile.tmp" -NoNewline
        Move-Item "$metaFile.tmp" $metaFile -Force
    }
}

# --- Step 2: Token snapshot (real, mirrors bash token-collector.py) ---
$tokenTotal  = 0
$tokenOutput = 0
$tokenCollectorPy = Join-Path $PLUGIN_ROOT "lib\token-collector.py"
if ($env:DEVFORGE_SESSION_DIR -and (Test-Path (Join-Path $env:DEVFORGE_SESSION_DIR "token-stats.json")) -and (Get-Command python3 -ErrorAction SilentlyContinue)) {
    try {
        python3 $tokenCollectorPy update 2>$null | Out-Null
        $tokLine = (python3 $tokenCollectorPy fields 2>$null)
        if ($tokLine) {
            $parts = $tokLine -split "`t"
            if ($parts.Count -ge 1 -and $parts[0] -match '^\d+$') { $tokenTotal  = [long]$parts[0] }
            if ($parts.Count -ge 2 -and $parts[1] -match '^\d+$') { $tokenOutput = [long]$parts[1] }
        }
    } catch {}
}

# --- Close previous skill cycle ---
$safeSkill = Convert-ToDevForgeJson $skillName
$sdlcPhase = Get-DevForgeSdlcPhase $skillName
$safeSdlc  = Convert-ToDevForgeJson $sdlcPhase

$skillTsFile = Join-Path $HOME ".claude\.devforge-skill-start"
if (Test-Path $skillTsFile) {
    $prevData        = (Get-Content $skillTsFile -Raw).Trim().Split('|')
    $prevStartNs     = if ($prevData.Count -gt 0) { $prevData[0] } else { "" }
    $prevSkill       = if ($prevData.Count -gt 1) { $prevData[1] } else { "" }
    $prevPhase       = if ($prevData.Count -gt 2) { $prevData[2] } else { "" }
    $prevTokenTotal  = if ($prevData.Count -gt 3) { $prevData[3] } else { "" }
    $prevTokenOutput = if ($prevData.Count -gt 4) { $prevData[4] } else { "" }

    if ($prevStartNs -and $prevSkill) {
        # Compute duration in milliseconds from nanosecond timestamps (mirrors devforge_log_timed)
        $nowNsForDuration = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() * 1000000
        $durationMs = 0
        if ($prevStartNs -match '^\d+$') {
            $durationMs = [math]::Max(0, ([long]$nowNsForDuration - [long]$prevStartNs) / 1000000)
        }
        # Token deltas — clamped to >=0, only when both baseline and current are numeric
        $deltaTot = 0
        $deltaOut = 0
        if ($prevTokenTotal -match '^\d+$' -and $tokenTotal -gt 0) {
            $deltaTot = [math]::Max(0, $tokenTotal - [long]$prevTokenTotal)
        }
        if ($prevTokenOutput -match '^\d+$' -and $tokenOutput -gt 0) {
            $deltaOut = [math]::Max(0, $tokenOutput - [long]$prevTokenOutput)
        }
        $safePrevSkill = Convert-ToDevForgeJson $prevSkill
        $safePrevPhase = Convert-ToDevForgeJson $prevPhase
        Write-DevForgeLog -Event "skill_completed" -Status "success" -DurationMs ([long]$durationMs) `
            -Meta "{`"skill_name`":`"$safePrevSkill`",`"sdlc_phase`":`"$safePrevPhase`",`"outcome`":`"success`",`"tokens_total_delta`":$deltaTot,`"tokens_output_delta`":$deltaOut}" 2>$null
    }
}

Write-DevForgeLog -Event "skill_invoked" -Status "success" `
    -Meta "{`"skill_name`":`"$safeSkill`",`"sdlc_phase`":`"$safeSdlc`"}" 2>$null

# Step 3 (CRITICAL): save new skill start timestamp (nanoseconds, 5-field format)
$nowNs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() * 1000000
"$nowNs|$skillName|$sdlcPhase|$tokenTotal|$tokenOutput" | Set-Content $skillTsFile -NoNewline

# --- Plan lifecycle events ---
$planWindowSec = 60
function Get-LatestRecentPlan {
    if (-not (Test-Path "docs\plans")) { return $null }
    $latest = Get-ChildItem "docs\plans\*-design.md" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latest) { return $null }
    $age = ([DateTimeOffset]::UtcNow - [DateTimeOffset]$latest.LastWriteTime).TotalSeconds
    if ($age -ge 0 -and $age -le $planWindowSec) { return $latest.FullName }
    return $null
}

if ($cleanSkill -eq "siae-brainstorming") {
    $recentPlan = Get-LatestRecentPlan
    if ($recentPlan) {
        $safePlan = Convert-ToDevForgeJson $recentPlan
        $logFile = $env:DEVFORGE_LOG_FILE
        if (-not $logFile) { $logFile = Join-Path $HOME ".claude\devforge.jsonl" }
        $existingLog = if (Test-Path $logFile) { Get-Content $logFile -Raw } else { "" }
        # Check if plan_created already logged for this plan_path
        if ($existingLog -match '"event":"plan_created"' -and $existingLog -match [regex]::Escape("`"plan_path`":`"$safePlan`"")) {
            Write-DevForgeLog -Event "plan_revised" -Status "success" -Meta "{`"plan_path`":`"$safePlan`",`"origin_skill`":`"$safeSkill`"}" 2>$null
        } else {
            Write-DevForgeLog -Event "plan_created" -Status "success" -Meta "{`"plan_path`":`"$safePlan`",`"origin_skill`":`"$safeSkill`"}" 2>$null
        }
    }
    # Reset brainstorming-gate counter (T05) + emit conversion event
    $counterFile = Join-Path $HOME ".claude\.devforge-brainstorm-counter"
    $preData = if (Test-Path $counterFile) { (Get-Content $counterFile -Raw).Trim() } else { "" }
    $preN = if ($preData -and $preData.Contains('|')) { $preData.Split('|')[-1] } else { "0" }
    $trigger = switch ([int]$preN) { 1 { "nudge" } 2 { "warn" } 3 { "warn" } default { if ([int]$preN -ge 4) { "block" } else { "none" } } }
    $sid = Get-DevForgeSid
    "$sid|0" | Set-Content $counterFile -NoNewline
    if ($trigger -ne "none") {
        Write-DevForgeLog -Event "brainstorming_invoked_post_gate" -Status "success" `
            -Meta "{`"trigger`":`"$trigger`",`"counter_before_reset`":$preN}" 2>$null
    }
} elseif ($cleanSkill -eq "siae-writing-plans") {
    $recentPlan = Get-LatestRecentPlan
    if ($recentPlan) {
        $header = Get-Content $recentPlan -TotalCount 10 -ErrorAction SilentlyContinue
        if ($header -match 'status:\s*approved') {
            $safePlan = Convert-ToDevForgeJson $recentPlan
            Write-DevForgeLog -Event "plan_approved" -Status "success" `
                -Meta "{`"plan_path`":`"$safePlan`",`"origin_skill`":`"$safeSkill`"}" 2>$null

            # plan_metrics: iterations + duration_sec (mirrors bash siae-writing-plans block)
            $logFile = $env:DEVFORGE_LOG_FILE
            if (-not $logFile) { $logFile = Join-Path $HOME ".claude\devforge.jsonl" }
            if (Test-Path $logFile) {
                $logContent   = Get-Content $logFile -Raw
                $createdMatch = [regex]::Match($logContent, '"event":"plan_created"[^}]*"plan_path":"' + [regex]::Escape($safePlan) + '"[^}]*}')
                if ($createdMatch.Success) {
                    $iterations = ([regex]::Matches($logContent, '"event":"plan_revised"[^}]*"plan_path":"' + [regex]::Escape($safePlan) + '"')).Count
                    # Extract ts field from the plan_created line
                    $tsMatch = [regex]::Match($createdMatch.Value, '"ts":"([^"]+)"')
                    $durationSec = 0
                    if ($tsMatch.Success -and (Get-Command python3 -ErrorAction SilentlyContinue)) {
                        try {
                            $createdTs = $tsMatch.Groups[1].Value
                            $createdEpoch = python3 -c "import sys; from datetime import datetime; t=datetime.fromisoformat(sys.argv[1].replace('Z','+00:00')); print(int(t.timestamp()))" $createdTs 2>$null
                            if ($createdEpoch -and [long]$createdEpoch -gt 0) {
                                $nowEpoch = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
                                $durationSec = [math]::Max(0, $nowEpoch - [long]$createdEpoch)
                                Write-DevForgeLog -Event "plan_metrics" -Status "success" `
                                    -Meta "{`"plan_path`":`"$safePlan`",`"iterations`":$iterations,`"duration_sec`":$durationSec,`"origin_skill`":`"$safeSkill`"}" 2>$null
                            } else {
                                Write-DevForgeLog -Event "plan_metrics" -Status "success" `
                                    -Meta "{`"plan_path`":`"$safePlan`",`"iterations`":$iterations,`"origin_skill`":`"$safeSkill`"}" 2>$null
                            }
                        } catch {
                            Write-DevForgeLog -Event "plan_metrics" -Status "success" `
                                -Meta "{`"plan_path`":`"$safePlan`",`"iterations`":$iterations,`"origin_skill`":`"$safeSkill`"}" 2>$null
                        }
                    } else {
                        Write-DevForgeLog -Event "plan_metrics" -Status "success" `
                            -Meta "{`"plan_path`":`"$safePlan`",`"iterations`":$iterations,`"origin_skill`":`"$safeSkill`"}" 2>$null
                    }
                }
            }
        }
    }
}

# --- TDD State Machine: initialize state when siae-tdd is invoked ---
if ($cleanSkill -eq "siae-tdd") {
    $tddFile  = Join-Path $HOME ".claude\.devforge-tdd-state"
    $curState = if (Test-Path $tddFile) { (Get-Content $tddFile -Raw).Trim().Split('|')[0] } else { "" }
    if (-not $curState -or $curState -eq "NONE") {
        $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        "INIT|pending|awaiting-test|$now" | Set-Content $tddFile -NoNewline
    }
}

Write-Output '{}'
exit 0
