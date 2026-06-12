# sport-task-detect.ps1  -  PowerShell equivalent
# Hook: UserPromptSubmit | Matcher: * | Timeout: 5s
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "sport-task-detect"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

$stateDir     = Join-Path $HOME ".claude"
$cooldownFile = Join-Path $stateDir ".devforge-sport-detect-last"
$cooldownSec  = 1800

$sportPatterns = @(
    'sport-*-service','sport-*-drools','sport-gestione-*',
    'pop-*-service','pop-be','pae-*','ciam-*','dol-be',
    'digital-channels-sport-*','esb-sport-*','esb-sso-*',
    'mag-concertini-*','portal-apigateway-*','ttpp-*-bff-service'
)

# Detect current directory against sport patterns (case-insensitive matching)
$cwdBase = Split-Path (Get-Location) -Leaf
$targetService = ""
foreach ($pat in $sportPatterns) {
    $regex = "^" + ($pat -replace '\*','.*') + "$"
    if ([regex]::IsMatch($cwdBase, $regex, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
        $targetService = $cwdBase; break
    }
}
if (-not $targetService) { exit 0 }

# Cooldown check
$now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
if (Test-Path $cooldownFile) {
    $data = (Get-Content $cooldownFile -Raw).Trim().Split('|')
    if ($data.Count -ge 2) {
        $lastTarget = $data[0]; $lastTs = [long]0
        if ([long]::TryParse($data[1], [ref]$lastTs)) {
            if ($lastTarget -eq $targetService -and ($now - $lastTs) -lt $cooldownSec) { exit 0 }
        }
    }
}

$safeTarget = Convert-ToDevForgeJson $targetService
$reminder   = "[sport-kg domain detected: $safeTarget]\nQuesto repo e' un servizio SIAE mappato nel KG sport-kg. Per task implementativi (feature, bug fix, refactoring) o di debugging su questo servizio, esegui PRIMA del brainstorming/debugging il pre-flight MCP via uno di:\n- Agent dedicato: dispatch agent ``mcp-impact-analyst`` (output strutturato, context-isolated)\n- Skill: invoca ``siae-service-logic-map`` modalita' impact-analysis\nL'output e' un blocco markdown standardizzato (rischio + 3 vincoli + volumi) da incollare in cima al design doc. Senza pre-flight, le opzioni di design sono cieche su latency, error rate, idempotenza, transazionalita' e failure coupling. Off-topic per task non-implementativi (domande, analisi, lettura)."

$output = @"
{
  "additional_context": "$reminder",
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "$reminder"
  }
}
"@

# Log telemetria PRIMA di emettere l'output (mirrors bash: devforge_log called before cat)
Initialize-DevForgeSession 2>$null
Write-DevForgeLog -Event "sport_domain_detected" -Status "info" -Meta "{`"target`":`"$safeTarget`"}" 2>$null

# Aggiorna cooldown SOLO se Write-Output ha successo
try {
    Write-Output $output
    "$targetService|$now" | Set-Content $cooldownFile -NoNewline
} catch {}
exit 0
