# skill-advisory.ps1  -  PowerShell equivalent
# Hook: PostToolUse | Matcher: Skill | Timeout: 5s
# Suggerisce skill prerequisita SE mancante nello state file.
# NEVER blocca: exit 0 sempre, output via additionalContext stdout.
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "skill-advisory"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

$hookInput = Read-StdinAll
$skillName = Get-JsonField $hookInput "tool_input.skill"
if (-not $skillName) { $skillName = Get-JsonField $hookInput "tool_input.skill_name" }
if (-not $skillName) { exit 0 }

if ($skillName -like "*:*") { $skillName = $skillName.Split(':')[-1] }

# --- State file resolution (mirrors skill-advisory-helpers.sh) ----------------
# STATE_FILE = $CLAUDE_PROJECT_DIR/.claude/projects/<project>/.skill-state
#            fallback: ./.claude/projects/<project>/.skill-state
function Get-SkillStateFile {
    $projectName = Split-Path (Get-Location) -Leaf
    $baseDir = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { Get-Location }
    return Join-Path $baseDir ".claude\projects\$projectName\.skill-state"
}

# Reads a key from the .skill-state JSON file; returns "" if absent or on error.
function Read-SkillState {
    param([string]$key)
    $stateFile = Get-SkillStateFile
    if (-not (Test-Path $stateFile)) { return "" }
    try {
        if (Get-Command python3 -ErrorAction SilentlyContinue) {
            $val = python3 -c @"
import json, sys
try:
    data = json.load(open(r'$stateFile'))
    print(data.get('$key', ''))
except Exception:
    print('')
"@ 2>$null
            return if ($val) { $val.Trim() } else { "" }
        }
        # Fallback: parse with PowerShell ConvertFrom-Json
        $data = Get-Content $stateFile -Raw | ConvertFrom-Json -ErrorAction Stop
        $v = $data.$key
        return if ($v -ne $null) { "$v".Trim() } else { "" }
    } catch {
        return ""
    }
}

# --- Suggestion table (mirrors suggestion_for() in skill-advisory-helpers.sh) -
function Get-SkillSuggestion {
    param([string]$skill)
    switch ($skill) {
        "siae-verification" {
            $lastFix = Read-SkillState "last_fix_or_implementation_done"
            if (-not $lastFix) {
                return "Suggerimento: la verifica si applica DOPO un fix o implementazione completata. Se stai iniziando nuovo lavoro, valuta siae-brainstorming."
            }
        }
        "siae-architecture" {
            $lastBrainstorm = Read-SkillState "last_brainstorm_step"
            $emit = $false
            if (-not $lastBrainstorm) {
                $emit = $true
            } else {
                try { if ([int]$lastBrainstorm -lt 4) { $emit = $true } } catch { $emit = $true }
            }
            if ($emit) {
                return "Suggerimento: architecture skill e' specialistica per Step 4 brainstorming (proposta opzioni). Considera siae-brainstorming prima."
            }
        }
        "siae-finishing-branch" {
            $lastVerify = Read-SkillState "last_verification_passed"
            if (-not $lastVerify) {
                return "Suggerimento: pre-PR checklist si applica DOPO siae-verification passata. Considera invocarla prima."
            }
        }
        "siae-tdd" {
            $lastBrainstorm = Read-SkillState "last_brainstorm_completed"
            if (-not $lastBrainstorm) {
                return "Suggerimento: TDD assume design approvato. Se non hai brainstormato il task, valuta siae-brainstorming prima."
            }
        }
        default {
            return ""  # nessun suggerimento per altre skill
        }
    }
    return ""
}

$suggestion = Get-SkillSuggestion $skillName
if (-not $suggestion) { exit 0 }

# Truncate to ~1900 chars (stay under additionalContext 2KB cap)
if ($suggestion.Length -gt 1900) { $suggestion = $suggestion.Substring(0, 1897) + "..." }

$safeSuggestion = Convert-ToDevForgeJson "[skill-advisory] $suggestion"
@"
{"additionalContext": "$safeSuggestion"}
"@
exit 0
