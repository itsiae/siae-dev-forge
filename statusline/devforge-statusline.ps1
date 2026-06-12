# devforge-statusline.ps1  -  Status line for Claude Code (Windows/PS5.1)
# Reads JSON from stdin + DevForge state files, outputs 2 formatted lines.
#
# State files written by: hooks/session-start, hooks/post-skill,
#   hooks/capture-test-result, hooks/batch-checkpoint
param()
$ErrorActionPreference = 'SilentlyContinue'

# --- 1. ANSI Colors (PS5.1: use [char]27 ESC prefix) ---
$ESC    = [char]27
$RED    = "$ESC[31m"
$GREEN  = "$ESC[32m"
$YELLOW = "$ESC[33m"
$RESET  = "$ESC[0m"

# --- 2. Paths ---
$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
$DEVFORGE_DIR = Join-Path $HOME ".claude"
$CACHE_FILE   = Join-Path $DEVFORGE_DIR ".devforge-git-cache"

# --- 3. Read stdin with 300ms timeout (non-blocking, matches bash read -t 0.3) ---
# Uses ReadLineAsync().Wait(ms) available in .NET 4.x / PS5.1
$CTX_USED   = 0
$QUOTA_5H   = ""
$AGENT_NAME = ""
$STDIN_JSON = ""

try {
    $readTask = [System.Console]::In.ReadLineAsync()
    if ($readTask.Wait(300)) {
        $STDIN_JSON = if ($readTask.Result) { $readTask.Result } else { "" }
    }
} catch {}

if ($STDIN_JSON) {
    $parsed = $null
    try { $parsed = $STDIN_JSON | ConvertFrom-Json -ErrorAction Stop } catch {}
    if ($parsed) {
        # context_window.used_percentage
        if ($parsed.context_window -and $parsed.context_window.used_percentage -ne $null) {
            $CTX_USED = [int][Math]::Floor([double]($parsed.context_window.used_percentage))
        }
        # rate_limits.five_hour.used_percentage
        if ($parsed.rate_limits -and $parsed.rate_limits.five_hour -and
            $parsed.rate_limits.five_hour.used_percentage -ne $null) {
            $QUOTA_5H = [int][Math]::Floor([double]($parsed.rate_limits.five_hour.used_percentage))
        }
        # agent.name
        if ($parsed.agent -and $parsed.agent.name) {
            $AGENT_NAME = $parsed.agent.name
        }
    }
}

# --- 4. Helper: read first line of a file ---
function Read-StatFile {
    param([string]$Path)
    if (Test-Path $Path) {
        $c = Get-Content $Path -TotalCount 1 -ErrorAction SilentlyContinue
        if ($c) { return $c.Trim() }
    }
    return ""
}

# --- 5. Read DevForge state files ---

# Skill start: timestamp_ns|skill_name|sdlc_phase
$skillStartRaw = Read-StatFile (Join-Path $DEVFORGE_DIR ".devforge-skill-start")
$CURRENT_SKILL = ""
$SDLC_PHASE    = ""
if ($skillStartRaw) {
    $parts = $skillStartRaw -split '\|'
    if ($parts.Count -ge 2) { $CURRENT_SKILL = $parts[1] }
    if ($parts.Count -ge 3) { $SDLC_PHASE    = $parts[2] }
}

# TDD state: PHASE|target|test_name|timestamp
$tddRaw   = Read-StatFile (Join-Path $DEVFORGE_DIR ".devforge-tdd-state")
$TDD_PHASE = ""
if ($tddRaw) { $TDD_PHASE = ($tddRaw -split '\|')[0] }

# Session skills: skill1,skill2,skill3
$SESSION_SKILLS = Read-StatFile (Join-Path $DEVFORGE_DIR ".devforge-session-skills")

# Session commits
$sessionCommitsRaw = Read-StatFile (Join-Path $DEVFORGE_DIR ".devforge-session-commits")
$SESSION_COMMITS = 0
if ($sessionCommitsRaw -match '\d+') { $SESSION_COMMITS = [int]($sessionCommitsRaw -replace '[^0-9]','') }

# Token stats from session dir
$SESSION_TOKENS = ""
$SESSION_COST   = ""
$sessionDir = $env:DEVFORGE_SESSION_DIR
if ($sessionDir -and (Test-Path (Join-Path $sessionDir "token-stats.json"))) {
    $tokenFile = Join-Path $sessionDir "token-stats.json"
    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        $tdata = (python3 -c @"
import json,sys
try:
    d=json.load(open(r'$tokenFile'))
    t=d.get('total',0)
    c=d.get('cost_eur',0)
    tok=f'{t/1e6:.1f}M' if t>=1e6 else f'{t/1e3:.0f}K' if t>=1e3 else str(t)
    print(f'{tok}\t{c:.2f}')
except: pass
"@ 2>$null)
        if ($tdata -and $tdata -match '\t') {
            $SESSION_TOKENS = ($tdata -split '\t')[0].Trim()
            $SESSION_COST   = ($tdata -split '\t')[1].Trim()
        }
    }
}

# Batch counter and checkpoint
$batchCounterRaw = Read-StatFile (Join-Path $DEVFORGE_DIR ".devforge-batch-counter")
$BATCH_COUNTER   = 0
if ($batchCounterRaw -match '\d+') { $BATCH_COUNTER = [int]($batchCounterRaw -replace '[^0-9]','') }
$BATCH_CHECKPOINT = Test-Path (Join-Path $DEVFORGE_DIR ".devforge-batch-checkpoint")

# --- 6. Git branch with 5s TTL cache ---
function Get-GitBranch {
    $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    if (Test-Path $CACHE_FILE) {
        $lines = Get-Content $CACHE_FILE -ErrorAction SilentlyContinue
        if ($lines -and $lines.Count -ge 2) {
            $cachedTime   = [long]($lines[0] -replace '[^0-9]','')
            $cachedBranch = $lines[1].Trim()
            if ($cachedBranch -and ($now - $cachedTime) -lt 5) {
                return $cachedBranch
            }
        }
    }
    $branch = (git rev-parse --abbrev-ref HEAD 2>$null)
    if (-not $branch) { $branch = "no-repo" }
    $branch = $branch.Trim()
    if (-not $branch) { $branch = "no-repo" }
    try { "$now`n$branch" | Set-Content $CACHE_FILE -Encoding UTF8 } catch {}
    return $branch
}

$GIT_BRANCH = Get-GitBranch
# Sanitize: keep only safe chars
$GIT_BRANCH = $GIT_BRANCH -replace '[^a-zA-Z0-9/_.\-]', ''

# --- 7. Helper functions ---

function Get-ContextBar {
    param([int]$Pct)
    $filled = [Math]::Floor($Pct / 10)
    if ($filled -lt 0)  { $filled = 0 }
    if ($filled -gt 10) { $filled = 10 }
    $empty = 10 - $filled

    $color = $GREEN
    if ($Pct -ge 90)    { $color = $RED }
    elseif ($Pct -ge 70) { $color = $YELLOW }

    $bar = ("$([char]0x2588)" * $filled) + ("$([char]0x2591)" * $empty)
    return "${color}${bar} ${Pct}%${RESET}"
}

function Get-TddBadge {
    param([string]$Phase)
    switch ($Phase) {
        "RED"      { return "TDD: ${RED}[RED]${RESET}" }
        "GREEN"    { return "TDD: ${GREEN}[GREEN]${RESET}" }
        "REFACTOR" { return "TDD: ${YELLOW}[REFACTOR]${RESET}" }
        "INIT"     { return "TDD: [INIT]" }
        default    { return "" }
    }
}

function Get-SkillCheck {
    param([string]$Skill, [string]$Skills)
    if ($Skills -like "*$Skill*") { return "[x]" } else { return "[ ]" }
}

function Test-HasSkill {
    param([string]$Skill)
    return ($SESSION_SKILLS -like "*$Skill*")
}

# --- 8. Compose line 1 — Operational status ---
$LINE1 = "DevForge"

if ($SDLC_PHASE -and $SDLC_PHASE -ne "idle" -and $SDLC_PHASE -ne "unknown") {
    $LINE1 += " [$SDLC_PHASE]"
}
if ($AGENT_NAME) {
    $LINE1 += " ($AGENT_NAME)"
}

$LINE1 += " | $GIT_BRANCH"

if ($TDD_PHASE) {
    $tddStr = Get-TddBadge $TDD_PHASE
    if ($tddStr) { $LINE1 += " | $tddStr" }
}

if ($SESSION_TOKENS) {
    $LINE1 += " | ${SESSION_TOKENS} tok"
    if ($SESSION_COST -and $SESSION_COST -ne "0.00") {
        $LINE1 += " ~${SESSION_COST}EUR"
    }
}

# --- 9. Compose line 2 — Awareness + warnings ---
$WARN_PARTS = @()

if ($CTX_USED -ge 80) {
    $WARN_PARTS += "${YELLOW}[!] Context alto - nuova sessione${RESET}"
}
if ($BATCH_CHECKPOINT) {
    $WARN_PARTS += "${YELLOW}[||] Batch completo - serve report${RESET}"
}
if ($SESSION_COMMITS -gt 0 -and -not (Test-HasSkill "siae-verification")) {
    $WARN_PARTS += "${YELLOW}[!] Verification non invocata${RESET}"
}
if ($SDLC_PHASE -and ($SDLC_PHASE -match "implement|testing") -and -not (Test-HasSkill "siae-brainstorming")) {
    $WARN_PARTS += "${YELLOW}[!] Brainstorming saltato${RESET}"
}

$BRAIN_CHK = Get-SkillCheck "brainstorming" $SESSION_SKILLS
$TDD_CHK   = Get-SkillCheck "tdd"           $SESSION_SKILLS
$VERIF_CHK = Get-SkillCheck "verification"  $SESSION_SKILLS

$LINE2 = "${BRAIN_CHK}brain ${TDD_CHK}tdd ${VERIF_CHK}verif"

if ($BATCH_COUNTER -gt 0) {
    $LINE2 += " | Task ${BATCH_COUNTER}/3"
}

$ctxBar = Get-ContextBar $CTX_USED
$LINE2 += " | Ctx: $ctxBar"

if ($QUOTA_5H -ne "" -and $QUOTA_5H -ne $null) {
    $q = [int]$QUOTA_5H
    $qColor = $GREEN
    if ($q -ge 90)    { $qColor = $RED }
    elseif ($q -ge 70) { $qColor = $YELLOW }
    $LINE2 += " | 5h: ${qColor}${q}%${RESET}"
}

if ($WARN_PARTS.Count -gt 0) {
    $warnStr = $WARN_PARTS -join " "
    $LINE2 = "$warnStr | $LINE2"
}

# --- 10. Output ---
[Console]::Out.WriteLine($LINE1)
[Console]::Out.WriteLine($LINE2)
