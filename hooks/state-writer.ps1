# state-writer.ps1  -  PowerShell equivalent
# Hook: PostToolUse | Matcher: Skill | Timeout: 5s
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "state-writer"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR

$hookInput = Read-StdinAll

$skillName = ""
$isError   = $null
try {
    $data = $hookInput | ConvertFrom-Json -ErrorAction Stop
    $skillName = $data.tool_input.skill
    if (-not $skillName) { $skillName = $data.tool_input.skill_name }
    $isError = $data.tool_response.is_error
} catch { }

if (-not $skillName) { Write-Output '{}'; exit 0 }
# Conservative: absent is_error treated as True (error), matching bash `is_error=True` default
# bash: success = d.get('tool_response',{}).get('is_error', True) is False
if ($isError -ne $false) { Write-Output '{}'; exit 0 }

if ($skillName -like "*:*") { $skillName = $skillName.Split(':')[-1] }

# State file location — mirrors bash STATE_DIR="${CLAUDE_PROJECT_DIR:-.}/.claude/projects/$(basename $(pwd))"
# bash uses basename $(pwd) (current directory), NOT basename $CLAUDE_PROJECT_DIR.
$projectDir = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { (Get-Location).Path }
$stateDir  = Join-Path $projectDir ".claude\projects\$(Split-Path (Get-Location).Path -Leaf)"
$stateFile = Join-Path $stateDir ".skill-state"
New-Item -ItemType Directory -Path $stateDir -Force | Out-Null 2>$null

# Load existing state
$state = @{ version = 1 }
if (Test-Path $stateFile) {
    try {
        $json = Get-Content $stateFile -Raw | ConvertFrom-Json -ErrorAction Stop
        $json.PSObject.Properties | ForEach-Object { $state[$_.Name] = $_.Value }
    } catch { }
}

$now = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")

switch ($skillName) {
    "siae-brainstorming"  { $state['last_brainstorm_completed'] = $now; $state['last_brainstorm_step'] = 7 }
    "siae-debugging"      { $state['last_debug_phase'] = 4 }
    "siae-tdd"            { $state['last_tdd_cycle'] = $now; $state['last_fix_or_implementation_done'] = $now }
    "siae-verification"   { $state['last_verification_passed'] = $now }
    "siae-writing-plans"  { $state['last_plan_written'] = $now }
}

$state | ConvertTo-Json -Depth 5 | Set-Content "$stateFile.tmp" -Encoding UTF8
Move-Item "$stateFile.tmp" $stateFile -Force 2>$null

Write-Output '{}'
exit 0
