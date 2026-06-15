# branch-tracker.ps1  -  PowerShell equivalent
# Hook: PostToolUse | Matcher: Bash | Timeout: 5s
# Emits branch_created event on git checkout -b / git switch -c.
# Best-effort, never blocking: any error exits 0 silently.
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "branch-tracker"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

$hookInput = Read-StdinAll
$CMD = ""
try {
    $data = $hookInput | ConvertFrom-Json -ErrorAction Stop
    $CMD  = $data.tool_input.command
} catch { }
if (-not $CMD) { exit 0 }

# Fase 1: detect git checkout or git switch with branch-creation flag
$isCheckout = $CMD -match '(?:^|[;&|]\s*)git\s+checkout\b'
$isSwitch   = $CMD -match '(?:^|[;&|]\s*)git\s+switch\b'
if (-not ($isCheckout -or $isSwitch)) { exit 0 }

$hasCreateFlag = $CMD -match '\s(-b|-c|--branch)\s'
if (-not $hasCreateFlag) { exit 0 }

# Fase 2: extract target branch name after creation flag
$TARGET = ""
if ($CMD -match '(?:-b|-c|--branch)\s+(\S+)') {
    $TARGET = $Matches[1]
}
if (-not $TARGET) { exit 0 }

# Guard: branch must have been actually created (HEAD == TARGET)
$CUR = (git rev-parse --abbrev-ref HEAD 2>$null)
if ($CUR -ne $TARGET) { exit 0 }

# Get base branch (previous branch before the switch)
$BASE_BRANCH = (git rev-parse --abbrev-ref "@{-1}" 2>$null)
if (-not $BASE_BRANCH) { $BASE_BRANCH = "" }

# Log telemetry
try {
    Initialize-DevForgeSession 2>$null
    $safeBase = Convert-ToDevForgeJson $BASE_BRANCH
    Write-DevForgeLog -Event "branch_created" -Status "success" -Meta "{`"base_branch`":`"$safeBase`"}" 2>$null
} catch { }

exit 0
