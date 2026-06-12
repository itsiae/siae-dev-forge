# stop-gate.ps1  -  PowerShell equivalent
# Hook: Stop | Matcher: * | Timeout: 5s
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "stop-gate"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

Initialize-DevForgeSession 2>$null

# --- FIX 4: Pre-flush telemetria PRIMA dei gate (Zero-loss) ---
# Garantisce che il backlog sia svuotato anche se un gate blocca lo stop.
# Il secondo flush dentro Emit-SessionEnd resta come flush idempotente
# per catturare gli eventi della session_end stessa.
try {
    $telemetryUploader = Join-Path $PLUGIN_ROOT "lib\telemetry-upload.py"
    if (Test-Path $telemetryUploader) {
        python3 $telemetryUploader 2>$null
    }
} catch {}

$hookInput = Read-StdinAll

# --- Read counters early ---
$sessionStartFile  = Join-Path $HOME ".claude\.devforge-session-start-ns"
$sessionCommits    = Join-Path $HOME ".claude\.devforge-session-commits"
$sessionSkillsFile = Join-Path $HOME ".claude\.devforge-session-skills"

$sessionStartNs  = if (Test-Path $sessionStartFile) { (Get-Content $sessionStartFile -Raw).Trim() } else { "0" }
$commitsCount    = if (Test-Path $sessionCommits) { [int](Get-Content $sessionCommits -Raw).Trim() } else { 0 }
$skillsList      = if (Test-Path $sessionSkillsFile) { (Get-Content $sessionSkillsFile -Raw).Trim() } else { "" }
$skillsUsedCount = if ($skillsList) { ($skillsList.Split(',') | Sort-Object -Unique | Measure-Object).Count } else { 0 }

# Helper: emit session_end
function Emit-SessionEnd {
    $guardDir = Join-Path $HOME ".claude\.devforge-session-end-guard"
    if (-not (New-Item -ItemType Directory -Path $guardDir -ErrorAction SilentlyContinue)) { return }

    # --- FIX 3: Last skill close con durata calcolata in millisecondi corretti ---
    # Legge SKILL_TS_FILE e calcola la durata reale usando il timestamp in ns.
    $skillTsFile = Join-Path $HOME ".claude\.devforge-skill-start"
    if (Test-Path $skillTsFile) {
        $prevData    = (Get-Content $skillTsFile -Raw).Trim().Split('|')
        $prevStartNs = if ($prevData.Count -gt 0) { $prevData[0] } else { "" }
        $prevSkill   = if ($prevData.Count -gt 1) { $prevData[1] } else { "" }
        $prevPhase   = if ($prevData.Count -gt 2) { $prevData[2] } else { "" }
        if ($prevStartNs -and $prevSkill) {
            $safeSkill = Convert-ToDevForgeJson $prevSkill
            $safePhase = Convert-ToDevForgeJson $prevPhase
            # Calcola durata in ms dai nanoseconds (come devforge_log_timed in bash)
            $durationMs = -1
            try {
                $nowNs    = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() * 1000000L
                $startNsL = [long]$prevStartNs
                $diffNs   = $nowNs - $startNsL
                if ($diffNs -gt 0) { $durationMs = [long]($diffNs / 1000000) }
            } catch { $durationMs = -1 }
            Write-DevForgeLog -Event "skill_completed" -Status "success" -DurationMs $durationMs `
                -Meta "{`"skill_name`":`"$safeSkill`",`"sdlc_phase`":`"$safePhase`",`"outcome`":`"success`"}" 2>$null
        }
        Remove-Item $skillTsFile -Force -ErrorAction SilentlyContinue
    }

    # --- FIX 1: Token tracking arricchito da token-collector.py ---
    # Aggiorna prima le stats, poi legge i campi in formato tab-separato.
    $tokenTotal      = 0
    $tokenOutput     = 0
    $tokenCostEur    = "0"
    $tokenModel      = ""
    $tokenInput      = 0
    $tokenCacheRead  = 0
    $tokenCw5m       = 0
    $tokenCw1h       = 0
    $tokenByModel    = "{}"
    $tokenByTool     = "{}"
    $tokenBySkill    = "{}"
    $tokenByModelTok = "{}"
    $tokenPricing    = "{}"

    try {
        $tokenCollector = Join-Path $PLUGIN_ROOT "lib\token-collector.py"
        $tokenStatsFile = if ($env:DEVFORGE_SESSION_DIR) { Join-Path $env:DEVFORGE_SESSION_DIR "token-stats.json" } else { "" }
        if ((Test-Path $tokenCollector) -and $tokenStatsFile -and (Test-Path $tokenStatsFile)) {
            # Prima aggiorna le stats
            python3 $tokenCollector update 2>$null
            # Poi legge i campi in formato tab-separato (stesso ordine della bash)
            $tdata = python3 $tokenCollector fields 2>$null
            if ($tdata) {
                $tfields = $tdata -split "`t"
                if ($tfields.Count -ge 1  -and $tfields[0])  { $tokenTotal      = $tfields[0] }
                if ($tfields.Count -ge 2  -and $tfields[1])  { $tokenOutput     = $tfields[1] }
                if ($tfields.Count -ge 3  -and $tfields[2])  { $tokenCostEur    = $tfields[2] }
                if ($tfields.Count -ge 4  -and $tfields[3])  { $tokenModel      = $tfields[3] }
                if ($tfields.Count -ge 5  -and $tfields[4])  { $tokenInput      = $tfields[4] }
                if ($tfields.Count -ge 6  -and $tfields[5])  { $tokenCacheRead  = $tfields[5] }
                if ($tfields.Count -ge 7  -and $tfields[6])  { $tokenCw5m       = $tfields[6] }
                if ($tfields.Count -ge 8  -and $tfields[7])  { $tokenCw1h       = $tfields[7] }
                if ($tfields.Count -ge 9  -and $tfields[8])  { $tokenByModel    = $tfields[8] }
                if ($tfields.Count -ge 10 -and $tfields[9])  { $tokenByTool     = $tfields[9] }
                if ($tfields.Count -ge 11 -and $tfields[10]) { $tokenBySkill    = $tfields[10] }
                if ($tfields.Count -ge 12 -and $tfields[11]) { $tokenByModelTok = $tfields[11] }
                if ($tfields.Count -ge 13 -and $tfields[12]) { $tokenPricing    = $tfields[12] }
            }
        }
    } catch {}

    $safeModel = Convert-ToDevForgeJson $tokenModel

    # Calcola durata sessione in ms dai nanoseconds
    $sessionDurationMs = -1
    try {
        $startNsL = [long]$sessionStartNs
        if ($startNsL -gt 0) {
            $nowNs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() * 1000000L
            $diffNs = $nowNs - $startNsL
            if ($diffNs -gt 0) { $sessionDurationMs = [long]($diffNs / 1000000) }
        }
    } catch { $sessionDurationMs = -1 }

    $sessionEndMeta = "{`"skills_used_count`":$skillsUsedCount,`"commits_count`":$commitsCount," +
        "`"total_tokens`":$tokenTotal,`"output_tokens`":$tokenOutput," +
        "`"cost_estimate_eur`":$tokenCostEur,`"model_prevalent`":`"$safeModel`"," +
        "`"input_tokens`":$tokenInput,`"cache_read_tokens`":$tokenCacheRead," +
        "`"cache_write_5m_tokens`":$tokenCw5m,`"cache_write_1h_tokens`":$tokenCw1h," +
        "`"by_model`":$tokenByModel,`"by_tool`":$tokenByTool," +
        "`"by_skill`":$tokenBySkill,`"by_model_tokens`":$tokenByModelTok," +
        "`"pricing`":$tokenPricing}"

    Write-DevForgeLog -Event "session_end" -Status "success" -DurationMs $sessionDurationMs `
        -Meta $sessionEndMeta 2>$null

    # --- FIX 2: adoption-analyzer.py recap su stderr (ADR-009) ---
    # 3-line recap non bloccante. Opt-out via DEVFORGE_DISABLE_RECAP=1.
    try {
        $adoptionAnalyzer = Join-Path $PLUGIN_ROOT "lib\adoption-analyzer.py"
        if ($env:DEVFORGE_DISABLE_RECAP -ne "1" -and (Test-Path $adoptionAnalyzer)) {
            $recapLines = python3 $adoptionAnalyzer --format recap 2>$null
            if ($recapLines) {
                $recapLines -split "`n" | ForEach-Object {
                    if ($_) { [Console]::Error.WriteLine("[devforge-recap] $_") }
                }
            }
        }
    } catch {}

    # Secondo flush telemetria (idempotente, cattura eventi session_end stessa)
    try {
        $telemetryUploader = Join-Path $PLUGIN_ROOT "lib\telemetry-upload.py"
        if (Test-Path $telemetryUploader) {
            python3 $telemetryUploader 2>$null
        }
    } catch {}

    # Cleanup session files
    Remove-Item $sessionStartFile, $sessionCommits, $sessionSkillsFile -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $HOME ".claude\.devforge-session-user") -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $HOME ".claude\.devforge-session-user-source") -Force -ErrorAction SilentlyContinue

    # Cleanup session-scoped evidence bypass
    $sid = Get-DevForgeSid
    if ($sid) {
        $bypassMarker = Join-Path $HOME ".claude\devforge-state\$sid\.bypass-evidence"
        Remove-Item $bypassMarker -Force -ErrorAction SilentlyContinue
    }

    # Cleanup guard
    Remove-Item $guardDir -Recurse -Force -ErrorAction SilentlyContinue
}

# If stdin empty: just emit session_end
if (-not $hookInput.Trim()) {
    Emit-SessionEnd
    exit 0
}

# Extract last assistant message
$lastAssistantMsg = ""
try {
    $data = $hookInput | ConvertFrom-Json -ErrorAction Stop
    $messages = if ($data.messages) { $data.messages } elseif ($data.transcript) { $data.transcript } else { @() }
    $last = $messages | Where-Object { $_.role -eq "assistant" } | Select-Object -Last 1
    if ($last) {
        if ($last.content -is [string]) { $lastAssistantMsg = $last.content }
        else { $lastAssistantMsg = ($last.content | Where-Object { $_.type -eq "text" } | ForEach-Object { $_.text }) -join " " }
    }
} catch { }

# --- FIX 7: Completion keywords — aggiunto 'mergeat' (presente in bash, mancante in PS1) ---
$completionPattern = 'fatto|fatti|fatta|fatte|fixato|fixata|completato|completata|completati|funziona|done|fixed|pass|implementato|implementata|risolto|risolta|aggiornato|creato|aggiunto|rimosso|corretto|pubblicato|deployato|mergeat|mergiato|finito|finita|concluso|conclusa|terminato|terminata|pronto|pronta'

if ($lastAssistantMsg -notmatch $completionPattern) {
    Emit-SessionEnd
    exit 0
}

# --- Retrospective gate ---
if ($skillsUsedCount -gt 0 -or $commitsCount -gt 0) {
    if ($skillsList -notlike "*siae-retrospective*") {
        if ($env:DEVFORGE_SKIP_RETRO_GATE -eq "1") {
            Write-DevForgeLog -Event "stop_gate" -Status "skipped_retro" `
                -Meta "{`"reason`":`"DEVFORGE_SKIP_RETRO_GATE=1`",`"skills`":$skillsUsedCount,`"commits`":$commitsCount}" 2>$null
            Emit-SessionEnd
            exit 0
        }
        Write-DevForgeLog -Event "stop_gate" -Status "blocked_retro" `
            -Meta "{`"reason`":`"retrospective_missing`",`"skills`":$skillsUsedCount,`"commits`":$commitsCount}" 2>$null
        @"
{
  "decision": "block",
  "reason": "DevForge Retrospective Gate  -  Sessione produttiva ($skillsUsedCount skill invocate, $commitsCount commit) senza siae-retrospective. Le lezioni non salvate sono lezioni perse. Invoca siae-retrospective per estrarre e persistere le lezioni apprese, poi potrai fermarti."
}
"@
        exit 0
    }
}

# --- FIX 6: Verification gate — evidence-based (allineato a bash ADR-006 + ADR-008) ---
# Il gate passa quando siae-verification risulta validata per il task corrente:
#   task-scoped (default): controlla skills_validated (evidence-based, come devforge_skill_validated)
#   session-scoped (fallback/rollback): grep su session-skills file
#
# USE_SESSION_SCOPE: se DEVFORGE_USE_SESSION_SCOPE=1 salta il check task-scoped
$useSessionScope  = $env:DEVFORGE_USE_SESSION_SCOPE -eq "1"
$verificationOk   = $false
$taskId           = Get-DevForgeTaskId

if (-not $useSessionScope -and $taskId) {
    # Check task-scoped evidence: skills_validated file (più robusto di skills_invoked)
    $taskValidated = Join-Path $HOME ".claude\.devforge-task-skills\$taskId\skills_validated"
    $taskInvoked   = Join-Path $HOME ".claude\.devforge-task-skills\$taskId\skills_invoked"
    if ((Test-Path $taskValidated) -and ((Get-Content $taskValidated) -contains "siae-verification")) {
        $verificationOk = $true
    } elseif ((Test-Path $taskInvoked) -and ((Get-Content $taskInvoked) -contains "siae-verification")) {
        # Fallback su skills_invoked se skills_validated non esiste ancora
        $verificationOk = $true
    }
}

# Session-scope fallback: se il check task-scoped non ha validato (o rollback attivo),
# accetta il legacy grep su session-skills. Mantiene dual-write / rollback stabile.
if (-not $verificationOk -and $skillsList -like "*siae-verification*") { $verificationOk = $true }

if ($verificationOk) {
    Remove-Item (Join-Path $HOME ".claude\.devforge-retro-reminded") -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $HOME ".claude\.devforge-stop-block-count") -Force -ErrorAction SilentlyContinue
    Emit-SessionEnd
    exit 0
}

# Explicit bypass
if ($env:DEVFORGE_FORCE_STOP -eq "1") {
    $forceFile = Join-Path $HOME ".claude\.devforge-force-stop-count"
    $today     = [DateTime]::UtcNow.ToString("yyyy-MM-dd")
    $fdata     = if (Test-Path $forceFile) { (Get-Content $forceFile -Raw).Trim() } else { "" }
    $bDate     = if ($fdata -and $fdata.Contains('|')) { $fdata.Split('|')[0] } else { "" }
    $bCount    = if ($fdata -and $fdata.Contains('|')) { [int]$fdata.Split('|')[1] } else { 0 }
    if ($bDate -ne $today) { $bCount = 0 }
    $bCount++
    "$today|$bCount" | Set-Content $forceFile -NoNewline
    Write-DevForgeLog -Event "stop_gate_forced" -Status "warning" -Meta "{`"count_today`":$bCount}" 2>$null
    if ($bCount -ge 3) {
        Write-DevForgeLog -Event "force_stop_abuse_suspected" -Status "warning" -Meta "{`"count_today`":$bCount}" 2>$null
    }
    Emit-SessionEnd
    exit 0
}

# --- FIX 5: Hard block con _SG_EXPL (block-explainer) ---
Write-DevForgeLog -Event "stop_gate" -Status "blocked" `
    -Meta "{`"reason`":`"completion_claim_without_verification`",`"task_id`":`"$taskId`"}" 2>$null

# Legge eventuale spiegazione aggiuntiva dal block-explainer (non bloccante)
$sgExpl = ""
try {
    $blockExplainer = Join-Path $PLUGIN_ROOT "lib\block-explainer.py"
    if (Test-Path $blockExplainer) {
        $explText = python3 $blockExplainer siae-verification 2>$null
        if ($explText) { $sgExpl = " $($explText.Trim())" }
    }
} catch {}

@"
{
  "decision": "block",
  "reason": "DevForge Verification Gate  -  BLOCCATO. Il tuo ultimo output contiene un claim di completamento ma NON risulta evidenza di siae-verification per questo task. NESSUN CLAIM SENZA EVIDENZA. Invoca siae-verification e segui il protocollo IDENTIFICA -> ESEGUI -> LEGGI -> VERIFICA -> AFFERMA.$sgExpl Escape esplicito (tracciato 3/giorno): DEVFORGE_FORCE_STOP=1 <comando>."
}
"@
exit 0
