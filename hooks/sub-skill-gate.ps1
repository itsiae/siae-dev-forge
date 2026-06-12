# sub-skill-gate.ps1  -  PowerShell equivalent
# Hook: PreToolUse | Matcher: Skill | Timeout: 5s
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "sub-skill-gate"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

$hookInput = Read-StdinAll
$skillName = Get-JsonField $hookInput "skill"
if (-not $skillName) { $skillName = Get-JsonField $hookInput "tool_input.skill" }
if (-not $skillName) { Write-Output '{}'; exit 0 }

# Strip plugin prefix
if ($skillName -like "*:*") { $skillName = $skillName.Split(':')[-1] }

# Load prerequisite map
$prereqMapFile = Join-Path $PLUGIN_ROOT "lib\prereq-map.generated"
$prereqMap = @()
if (Test-Path $prereqMapFile) {
    Get-Content $prereqMapFile | Where-Object { $_ -and -not $_.StartsWith('#') } | ForEach-Object { $prereqMap += $_ }
}
if (-not $prereqMap) {
    $prereqMap = @(
        "siae-git-workflow=siae-git-env",
        "siae-finishing-branch=siae-git-env,siae-git-workflow",
        "siae-git-worktrees=siae-git-env",
        "siae-service-logic-map=siae-microservices-map",
        "siae-writing-plans=siae-brainstorming",
        "siae-executing-plans=siae-writing-plans",
        "siae-requesting-review=siae-finishing-branch"
    )
}

# Find prerequisites
$requiredPrereqs = ""
foreach ($entry in $prereqMap) {
    $parts = $entry.Split('=', 2)
    if ($parts.Count -eq 2 -and $parts[0].Trim() -eq $skillName) {
        $requiredPrereqs = $parts[1].Trim()
        break
    }
}
if (-not $requiredPrereqs) { Write-Output '{}'; exit 0 }

$sessionSkills  = Get-DevForgeSessionSkills
$missingPrereqs = @()
foreach ($prereq in $requiredPrereqs.Split(',')) {
    $p = $prereq.Trim()
    if ($sessionSkills -notlike "*$p*") { $missingPrereqs += $p }
}
if (-not $missingPrereqs) { Write-Output '{}'; exit 0 }

Initialize-DevForgeSession 2>$null
$missing = $missingPrereqs -join ", "
$safeSkill   = Convert-ToDevForgeJson $skillName
$safeMissing = Convert-ToDevForgeJson $missing
Write-DevForgeLog -Event "sub_skill_gate" -Status "blocked" -Meta "{`"skill`":`"$safeSkill`",`"missing_prereqs`":`"$safeMissing`"}" 2>$null

@"
{
  "decision": "block",
  "reason": "DevForge Sub-Skill Gate  -  BLOCCATO. La skill $skillName richiede come prerequisito: $missing. Invoca prima le skill mancanti, poi riprova $skillName."
}
"@
exit 0
