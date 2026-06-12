# devforge-context.ps1  -  PowerShell equivalent
# Hook: UserPromptSubmit | Matcher: * | Timeout: 5s
# Replaces: user-prompt-context + devforge-reinject + devforge-context-always
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "devforge-context"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

Initialize-DevForgeSession 2>$null

$stateDir   = Join-Path $HOME ".claude"
$hashFile   = Join-Path $stateDir ".devforge-last-injection-hash"
$maxBytes   = 2048

# -- Compute state hash -------------------------------------------------------
# Includes: skills, branch, tdd phase, gate violation flag, design doc mtime.
# Mirrors compute_state_hash() in bash.
function Get-StateHash {
    $rawSkills = Get-Content (Join-Path $stateDir ".devforge-session-skills") -Raw -ErrorAction SilentlyContinue
    $skills    = if ($rawSkills) { $rawSkills } else { "" }

    $branch = ""
    try { $branch = (git branch --show-current 2>$null).Trim() } catch {}

    $tddPhase = ""
    $tddFile  = Join-Path $stateDir ".devforge-tdd-state"
    if (Test-Path $tddFile) { $tddPhase = ((Get-Content $tddFile -Raw).Split('|')[0]).Trim() }

    # Recent block (<60s) → gate_violation = 1
    $gateViolation = 0
    $sbcFile = Join-Path $stateDir ".devforge-stop-block-count"
    if (Test-Path $sbcFile) {
        $mtime = (Get-Item $sbcFile).LastWriteTimeUtc
        if (([DateTime]::UtcNow - $mtime).TotalSeconds -lt 60) { $gateViolation = 1 }
    }

    $designMtime = 0
    if (Test-Path "docs\plans") {
        $latest = Get-ChildItem "docs\plans\*-design.md" -ErrorAction SilentlyContinue |
                  Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latest) { $designMtime = [DateTimeOffset]::new($latest.LastWriteTime).ToUnixTimeSeconds() }
    }

    $material = "${skills}|${branch}|${tddPhase}|${gateViolation}|${designMtime}"
    $sha = [System.Security.Cryptography.SHA1]::Create()
    return ([BitConverter]::ToString($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($material))) -replace '-','').ToLower()
}

$currentHash = Get-StateHash
$lastHash    = if (Test-Path $hashFile) { (Get-Content $hashFile -Raw).Trim() } else { "" }

# Skip if state unchanged (diff-based dedup)
if ($currentHash -eq $lastHash) { exit 0 }

# -- Task transition (ADR-001) -----------------------------------------------
# If the current task_id differs from the last observed one, copy evidence
# forward (mirrors devforge_task_id_transition logic in bash task-id.sh).
try {
    $currTaskId = Get-DevForgeTaskId 2>$null
    $lastTaskIdFile = Join-Path $stateDir ".devforge-last-task-id"
    $lastTaskId = if (Test-Path $lastTaskIdFile) { (Get-Content $lastTaskIdFile -Raw).Trim() } else { "" }

    if ($currTaskId -and $lastTaskId -and $currTaskId -ne $lastTaskId) {
        # Copy evidence files from old task dir to new task dir
        try {
            Invoke-DevForgeTaskIdTransition -OldId $lastTaskId -NewId $currTaskId 2>$null
        } catch {}
        # Log the transition
        try {
            Write-DevForgeLog -Event "task_id_transition" -Status "info" `
                -Meta "{`"from`":`"$lastTaskId`",`"to`":`"$currTaskId`"}" 2>$null
        } catch {}
    }

    if ($currTaskId) {
        # Atomic save: write to .tmp then rename (mirrors bash: echo > .tmp && mv)
        $tmpFile = "${lastTaskIdFile}.tmp"
        Set-Content $tmpFile $currTaskId -NoNewline
        Move-Item $tmpFile $lastTaskIdFile -Force
    }
} catch {}

# -- Determine tier -----------------------------------------------------------
# Tier "important" if stop-block-count file was modified < 60s ago.
# Mirrors bash TIER logic in devforge-context.
$tier     = "none"
$tagOpen  = ""
$tagClose = ""

$sbcFile = Join-Path $stateDir ".devforge-stop-block-count"
if (Test-Path $sbcFile) {
    try {
        $sbMtime = (Get-Item $sbcFile).LastWriteTimeUtc
        if (([DateTime]::UtcNow - $sbMtime).TotalSeconds -lt 60) {
            $tier     = "important"
            $tagOpen  = "<IMPORTANT>"
            $tagClose = "</IMPORTANT>"
        }
    } catch {}
}

# -- Build compact payload (max $maxBytes bytes) ------------------------------
$payload = ""

try {
    $gitBranch = (git branch --show-current 2>$null).Trim()
    $gitLast   = (git log --oneline -1 2>$null).Trim()
    $payload  += "Git: branch=$gitBranch | $gitLast\n"
} catch {}

$skillsFile  = Join-Path $stateDir ".devforge-session-skills"
$skillsCount = 0
if (Test-Path $skillsFile) {
    $skills = Get-Content $skillsFile -Raw
    if ($skills) { $skillsCount = ($skills.Split(',') | Where-Object { $_ }).Count }
}
$commitsFile  = Join-Path $stateDir ".devforge-session-commits"
$commitsCount = if (Test-Path $commitsFile) { (Get-Content $commitsFile -Raw).Trim() } else { "0" }
$payload     += "Session: skills=$skillsCount | commits=$commitsCount\n"
$payload     += "Backbone: brainstorm->plan->tdd->verification. If 1% applicable, invoke skill.\n"

if ($payload.Length -gt $maxBytes) { $payload = $payload.Substring(0, $maxBytes) }

$payloadEscaped = Convert-ToDevForgeJson $payload

# -- Final context with optional tier tag ------------------------------------
# Mirrors bash: if TAG_OPEN is set, wrap with <IMPORTANT>...</IMPORTANT>
if ($tagOpen) {
    $context = "${tagOpen}\n[DevForge Context]\n${payloadEscaped}${tagClose}"
} else {
    $context = "[DevForge Context]\n$payloadEscaped"
}

# -- Emit context JSON to stdout ---------------------------------------------
$output = @"
{
  "additional_context": "$context",
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "$context"
  }
}
"@

# Telemetry BEFORE output (mirrors bash: devforge_log called before `if cat`)
$size = [System.Text.Encoding]::UTF8.GetByteCount($context)
Write-DevForgeLog -Event "prompt_injection_emitted" -Status "success" `
    -Meta "{`"size_bytes`":$size,`"tier`":`"$tier`"}" 2>$null

Write-Output $output

# Atomic save hash: write to .tmp then rename (mirrors bash: echo > .tmp && mv)
# Hash is stored ONLY on successful emission (Write-Output above).
try {
    $hashTmp = "${hashFile}.tmp"
    Set-Content $hashTmp $currentHash -NoNewline
    Move-Item $hashTmp $hashFile -Force
} catch {
    # Degraded path: direct write if atomic rename fails
    Set-Content $hashFile $currentHash -NoNewline 2>$null
}

exit 0
