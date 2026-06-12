# post-commit-review.ps1  -  PowerShell equivalent
# Hook: PostToolUse | Matcher: Bash | Timeout: 10s
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "post-commit-review"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

Initialize-DevForgeSession 2>$null

$hookInput   = Read-StdinAll
$toolCommand = Get-JsonField $hookInput "command"
if (-not $toolCommand) { $toolCommand = Get-JsonField $hookInput "tool_input.command" }

# --- Detect new commit: per-repo hash file ---
$gitRoot = try { (git rev-parse --show-toplevel 2>$null).Trim() } catch { "" }
$repoKey = if ($gitRoot) {
    $sha1  = [System.Security.Cryptography.SHA1]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($gitRoot)
    ([BitConverter]::ToString($sha1.ComputeHash($bytes)) -replace '-','').ToLower().Substring(0, 16)
} else { "nogit" }

$lastHashFile  = Join-Path $HOME ".claude\.devforge-last-commit-hash-$repoKey"
$currentHead   = try { (git rev-parse HEAD 2>$null).Trim() } catch { "" }
$savedHash     = if (Test-Path $lastHashFile) { (Get-Content $lastHashFile -Raw).Trim() } else { "" }
$shouldUpload  = $false

if ($currentHead -and $currentHead -ne $savedHash) {
    $diffStat    = try { (git diff --stat HEAD~1 HEAD 2>$null) } catch { "" }
    $statsLine   = ($diffStat -split "`n" | Select-Object -Last 1)
    $filesChanged = if ($statsLine -match '(\d+) file') { $Matches[1] } else { "0" }
    $insertions   = if ($statsLine -match '(\d+) insertion') { $Matches[1] } else { "0" }
    $deletions    = if ($statsLine -match '(\d+) deletion') { $Matches[1] } else { "0" }

    $changedFiles = try { (git diff --name-only HEAD~1 HEAD 2>$null) } catch { "" }
    $hasTests     = if ($changedFiles -match '(Test\.|_test\.|\.test\.|\.spec\.|/test/|/tests/)') { "true" } else { "false" }

    # Token update and delta for commit (mirrors bash token-collector.py block)
    $tokenCollectorPy = Join-Path $PLUGIN_ROOT "lib\token-collector.py"
    $tokenMeta = ""
    try { python3 $tokenCollectorPy update 2>$null | Out-Null } catch {}
    if ($env:DEVFORGE_SESSION_DIR -and (Test-Path (Join-Path $env:DEVFORGE_SESSION_DIR "token-stats.json")) -and (Get-Command python3 -ErrorAction SilentlyContinue)) {
        try {
            $currStatsFile = Join-Path $env:DEVFORGE_SESSION_DIR "token-stats.json"
            $prevStatsFile = Join-Path $env:DEVFORGE_SESSION_DIR "token-at-last-commit.json"
            $tokenMeta = python3 -c @"
import json,sys,os
curr = json.load(open(sys.argv[1])) if os.path.isfile(sys.argv[1]) else {}
prev = json.load(open(sys.argv[2])) if os.path.isfile(sys.argv[2]) else {}
do=curr.get('output',0)-prev.get('output',0)
dt=curr.get('total',0)-prev.get('total',0)
dc=round(curr.get('cost_eur',0)-prev.get('cost_eur',0),4)
cum=curr.get('total',0)
print(f',\"output_tokens_delta\":{do},\"total_tokens_delta\":{dt},\"cost_delta_eur\":{dc},\"session_tokens_cumulative\":{cum}')
"@ $currStatsFile $prevStatsFile 2>$null
            if ($tokenMeta) {
                Copy-Item $currStatsFile $prevStatsFile -Force -ErrorAction SilentlyContinue
            }
        } catch { $tokenMeta = "" }
    }

    Write-DevForgeLog -Event "commit_created" -Status "success" `
        -Meta "{`"commit_sha`":`"$currentHead`",`"files_changed`":$filesChanged,`"insertions`":$insertions,`"deletions`":$deletions,`"has_tests`":$hasTests$tokenMeta}" 2>$null

    # Increment session commit counter
    $commitsFile  = Join-Path $HOME ".claude\.devforge-session-commits"
    $current      = if (Test-Path $commitsFile) { [int](Get-Content $commitsFile -Raw).Trim() } else { 0 }
    ($current + 1) | Set-Content $commitsFile -NoNewline

    $currentHead | Set-Content $lastHashFile -NoNewline
    $shouldUpload = $true
}

# Helper: get session_tokens_cumulative from token-collector (for pr_merged)
function Get-SessionTokenCumulative {
    $tokenCollector = Join-Path $PLUGIN_ROOT "lib\token-collector.py"
    if ($env:DEVFORGE_SESSION_DIR -and (Test-Path (Join-Path $env:DEVFORGE_SESSION_DIR "token-stats.json")) -and (Get-Command python3 -ErrorAction SilentlyContinue)) {
        try {
            $statsFile = Join-Path $env:DEVFORGE_SESSION_DIR "token-stats.json"
            $result = python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('total',0))" $statsFile 2>$null
            if ($result -match '^\d+$') { return [long]$result }
        } catch {}
    }
    return 0
}

# Helper: compute time-to-merge in seconds from opened_ts string
function Get-TimeToMergeSec {
    param([string]$openedTs)
    if (-not $openedTs) { return 0 }
    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        try {
            $ttm = python3 -c @"
import sys
from datetime import datetime, timezone
t = datetime.fromisoformat(sys.argv[1].replace('Z','+00:00'))
now = datetime.now(timezone.utc)
print(max(0, int((now - t).total_seconds())))
"@ $openedTs 2>$null
            if ($ttm -match '^\d+$') { return [long]$ttm }
        } catch {}
    }
    # Fallback: pure .NET
    try {
        $parsed = [DateTime]::Parse($openedTs, $null, [System.Globalization.DateTimeStyles]::RoundtripKind)
        return [long][math]::Max(0, ([DateTime]::UtcNow - $parsed).TotalSeconds)
    } catch {}
    return 0
}

# PR lifecycle on git push
if ($toolCommand -match 'git\s+push') {
    if ((Get-Command gh -ErrorAction SilentlyContinue)) {
        try {
            $prJson = (gh pr view --json number,baseRefName,changedFiles,commits,reviewDecision,state 2>$null | ConvertFrom-Json -ErrorAction Stop)
            $prNumber = $prJson.number
            if ($prNumber -gt 0) {
                $baseBranch   = $prJson.baseRefName
                $filesChanged = $prJson.changedFiles
                $commitsCount = $prJson.commits.totalCount
                $safeBase     = Convert-ToDevForgeJson $baseBranch

                $snapshotFile = Join-Path $HOME ".claude\.devforge-pr-state-$prNumber.json"
                if (-not (Test-Path $snapshotFile)) {
                    $openedTs = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
                    Write-DevForgeLog -Event "pr_opened" -Status "success" `
                        -Meta "{`"pr_number`":$prNumber,`"base_branch`":`"$safeBase`",`"files_changed`":$filesChanged,`"commits_count`":$commitsCount}" 2>$null
                    @{pr_number=$prNumber;base_branch=$baseBranch;opened_ts=$openedTs;commits_at_open=$commitsCount;last_review_decision="REVIEW_REQUIRED"} `
                        | ConvertTo-Json | Set-Content $snapshotFile -Encoding UTF8
                } else {
                    $snap = Get-Content $snapshotFile -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
                    $commitsAtOpen    = if ($snap.commits_at_open) { [int]$snap.commits_at_open } else { 0 }
                    $commitsSinceOpen = [math]::Max(0, $commitsCount - $commitsAtOpen)
                    Write-DevForgeLog -Event "pr_commit_after_open" -Status "success" `
                        -Meta "{`"pr_number`":$prNumber,`"commit_sha`":`"$currentHead`",`"commits_since_open`":$commitsSinceOpen}" 2>$null

                    # pr_review_cycle: emit when review decision transitions to CHANGES_REQUESTED
                    $reviewDecision = $prJson.reviewDecision
                    if ($reviewDecision -eq "CHANGES_REQUESTED" -and $snap.last_review_decision -ne "CHANGES_REQUESTED") {
                        $devforgeLog = if ($env:DEVFORGE_LOG_FILE) { $env:DEVFORGE_LOG_FILE } else { Join-Path $HOME ".claude\devforge.jsonl" }
                        $logContent  = if (Test-Path $devforgeLog) { Get-Content $devforgeLog -Raw } else { "" }
                        $cycleNum    = ([regex]::Matches($logContent, '"event":"pr_review_cycle"[^}]*"pr_number":' + $prNumber)).Count + 1
                        Write-DevForgeLog -Event "pr_review_cycle" -Status "success" `
                            -Meta "{`"pr_number`":$prNumber,`"cycle_num`":$cycleNum,`"trigger`":`"changes_requested`"}" 2>$null
                        $snapUpdate = @{
                            pr_number            = $snap.pr_number
                            base_branch          = $snap.base_branch
                            opened_ts            = $snap.opened_ts
                            commits_at_open      = $snap.commits_at_open
                            last_review_decision = $reviewDecision
                        }
                        $snapUpdate | ConvertTo-Json | Set-Content "$snapshotFile.tmp" -Encoding UTF8
                        Move-Item "$snapshotFile.tmp" $snapshotFile -Force -ErrorAction SilentlyContinue
                    }
                }
                $shouldUpload = $true
            }
        } catch { }

        # Catch-up: snapshot orfani per merge via UI web
        $catchUpCount = 0
        $currentPrNumber = if ($prNumber) { $prNumber } else { 0 }
        Get-ChildItem -Path (Join-Path $HOME ".claude") -Filter ".devforge-pr-state-*.json" -ErrorAction SilentlyContinue | Sort-Object CreationTime | Select-Object -First 5 | ForEach-Object {
            if ($catchUpCount -ge 5) { return }
            $orphanFile = $_.FullName
            try {
                $orphanSnap = Get-Content $orphanFile -Raw | ConvertFrom-Json -ErrorAction Stop
                $orphanPr   = $orphanSnap.pr_number
                if (-not $orphanPr -or $orphanPr -eq $currentPrNumber) { return }
                $orphanJson = (gh pr view $orphanPr --json state,mergedAt,commits 2>$null | ConvertFrom-Json -ErrorAction SilentlyContinue)
                if (-not $orphanJson) { return }
                $orphanState = $orphanJson.state
                if ($orphanState -eq "MERGED" -or $orphanState -eq "CLOSED") {
                    $orphanTotal      = if ($orphanJson.commits.totalCount) { [int]$orphanJson.commits.totalCount } else { 0 }
                    $orphanAtOpen     = if ($orphanSnap.commits_at_open) { [int]$orphanSnap.commits_at_open } else { 0 }
                    $orphanDelta      = [math]::Max(0, $orphanTotal - $orphanAtOpen)
                    $mergeMethod      = if ($orphanState -eq "CLOSED") { "closed" } else { "web" }
                    $sessionTokensCum = Get-SessionTokenCumulative
                    Write-DevForgeLog -Event "pr_merged" -Status "success" `
                        -Meta "{`"pr_number`":$orphanPr,`"merge_method`":`"$mergeMethod`",`"total_commits`":$orphanTotal,`"delta_from_open`":$orphanDelta,`"session_tokens_cumulative`":$sessionTokensCum}" 2>$null

                    $orphanLog     = if ($env:DEVFORGE_LOG_FILE) { $env:DEVFORGE_LOG_FILE } else { Join-Path $HOME ".claude\devforge.jsonl" }
                    $orphanContent = if (Test-Path $orphanLog) { Get-Content $orphanLog -Raw } else { "" }
                    $orphanRework  = ([regex]::Matches($orphanContent, '"event":"pr_commit_after_open"[^}]*"pr_number":' + $orphanPr)).Count
                    $orphanCycles  = ([regex]::Matches($orphanContent, '"event":"pr_review_cycle"[^}]*"pr_number":' + $orphanPr)).Count
                    $orphanTtm     = Get-TimeToMergeSec -openedTs $orphanSnap.opened_ts
                    Write-DevForgeLog -Event "pr_metrics" -Status "success" `
                        -Meta "{`"pr_number`":$orphanPr,`"rework_commits`":$orphanRework,`"review_cycles`":$orphanCycles,`"time_to_merge_sec`":$orphanTtm,`"first_push_to_merge_sec`":$orphanTtm}" 2>$null

                    Remove-Item $orphanFile -Force -ErrorAction SilentlyContinue
                    $catchUpCount++
                    $shouldUpload = $true
                }
            } catch {}
        }
    }
}

# PR merge on gh pr merge
if ($toolCommand -match 'gh\s+pr\s+merge') {
    if ((Get-Command gh -ErrorAction SilentlyContinue)) {
        try {
            $prJson = (gh pr view --json number,commits 2>$null | ConvertFrom-Json -ErrorAction Stop)
            $prNumber     = $prJson.number
            $totalCommits = $prJson.commits.totalCount
            if ($prNumber -gt 0) {
                $snapshotFile = Join-Path $HOME ".claude\.devforge-pr-state-$prNumber.json"
                $commitsAtOpen = 0
                $snap = $null
                if (Test-Path $snapshotFile) {
                    $snap = Get-Content $snapshotFile -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
                    if ($snap.commits_at_open) { $commitsAtOpen = [int]$snap.commits_at_open }
                }
                $delta = [math]::Max(0, $totalCommits - $commitsAtOpen)
                $sessionTokensCum = Get-SessionTokenCumulative

                Write-DevForgeLog -Event "pr_merged" -Status "success" `
                    -Meta "{`"pr_number`":$prNumber,`"merge_method`":`"cli`",`"total_commits`":$totalCommits,`"delta_from_open`":$delta,`"session_tokens_cumulative`":$sessionTokensCum}" 2>$null

                # pr_metrics aggregato (legge snapshot PRIMA del cleanup)
                $devforgeLog  = if ($env:DEVFORGE_LOG_FILE) { $env:DEVFORGE_LOG_FILE } else { Join-Path $HOME ".claude\devforge.jsonl" }
                $logContent   = if (Test-Path $devforgeLog) { Get-Content $devforgeLog -Raw } else { "" }
                $reworkCount  = ([regex]::Matches($logContent, '"event":"pr_commit_after_open"[^}]*"pr_number":' + $prNumber)).Count
                $cyclesCount  = ([regex]::Matches($logContent, '"event":"pr_review_cycle"[^}]*"pr_number":' + $prNumber)).Count
                $ttmSec       = Get-TimeToMergeSec -openedTs ($snap.opened_ts)
                Write-DevForgeLog -Event "pr_metrics" -Status "success" `
                    -Meta "{`"pr_number`":$prNumber,`"rework_commits`":$reworkCount,`"review_cycles`":$cyclesCount,`"time_to_merge_sec`":$ttmSec,`"first_push_to_merge_sec`":$ttmSec}" 2>$null

                Remove-Item $snapshotFile -Force -ErrorAction SilentlyContinue
                $shouldUpload = $true
            }
        } catch { }
    }
}

# Only inject review instructions on PR create or git push
if ($toolCommand -notmatch 'gh\s+pr\s+create' -and $toolCommand -notmatch 'git\s+push') {
    Write-Output '{}'; exit 0
}

# Check if push succeeded
$toolOutput = Get-JsonField $hookInput "tool_response.stdout"
if (-not $toolOutput) { $toolOutput = Get-JsonField $hookInput "stdout" }
if (-not $toolOutput) { $toolOutput = Get-JsonField $hookInput "tool_output.stdout" }
if ($toolOutput -match 'error|fatal|rejected|failed') { Write-Output '{}'; exit 0 }

Write-DevForgeLog -Event "pr_auto_review" -Status "triggered" `
    -Meta "{`"command`":`"$(Convert-ToDevForgeJson $toolCommand)`"}" 2>$null

# Review instructions — full 5-paragraph version mirroring bash heredoc
$reviewInstructions = @'
# DevForge PR Auto-Review

Una PR e' stata creata o il branch e' stato pushato. DEVI lanciare automaticamente questi due agent in parallelo.

## REGOLA CRITICA: Passa il DIFF, non i path dei file

Gli agent di review DEVONO ricevere il diff testuale nel prompt, NON i path dei file.
Passare i path causa la lettura dei file interi — spreco di token enorme.

**Step preliminare obbligatorio:**
```bash
git diff origin/main...HEAD
```

Salva l'output di questo comando. Lo passerai nel prompt di ENTRAMBI gli agent.

## 1. Code Review (siae-devforge:code-reviewer)

Lancia l'agent con subagent_type="siae-devforge:code-reviewer".
Nel prompt INCLUDI il diff testuale completo, NON i path dei file.
L'agent eseguira' la review a 6 punti SOLO sul diff: conformita' al piano, code standards,
security, error handling, test coverage, architettura.

## 2. Security Check (siae-devforge:siae-security)

Invoca la skill siae-devforge:siae-security per verificare SOLO il diff:
- Nessun secret/credenziale nel diff
- IAM least privilege se ci sono policy AWS
- OWASP Top 10 compliance
- PII handling per dati autori/artisti SIAE

## Istruzioni

1. Ottieni il diff completo: `git diff origin/main...HEAD`
2. Lancia ENTRAMBI in parallelo usando il tool Agent:
   - Agent con subagent_type="siae-devforge:code-reviewer" — passa il DIFF nel prompt
   - Invoca Skill("siae-devforge:siae-security") per il security check — passa il DIFF
3. Mostra i risultati quando arrivano
4. Se trovano problemi critici, segnalali PRIMA di qualsiasi altra azione

IMPORTANTE: Analizza SOLO il diff — NON leggere file interi. Gli agent NON devono usare
Read o Glob per leggere file completi. Tutto il contesto necessario e' nel diff.
Se un agent ha bisogno di contesto aggiuntivo (es. design doc),
passa il path nel prompt ma SOLO per i criteri di accettazione, non per rileggere il codice.

NON chiedere all'utente se vuole la review — e' automatica.
NON saltare questo step — ogni PR viene revisionata.
'@

$safeInstructions = Convert-ToDevForgeJson $reviewInstructions
$retroContext = ""
if ($toolCommand -match 'gh\s+pr\s+create') {
    $retroInstr = @'
# DevForge Retrospective Trigger

Una PR e' stata creata. DOPO la code review, invoca `siae-retrospective` per estrarre
e persistere le lezioni apprese dalla sessione corrente.

La retrospettiva e' il momento naturale per riflettere: la PR chiude il ciclo di lavoro.
NON saltare questo step. Le lezioni non salvate sono lezioni perse.

Invoca: Skill tool -> siae-devforge:siae-retrospective
'@
    $retroContext = "\n\n<IMPORTANT>\n$(Convert-ToDevForgeJson $retroInstr)\n</IMPORTANT>"
}

$fullContext = "<EXTREMELY_IMPORTANT>\nDevForge PR Auto-Review attivato.\n\n$safeInstructions$retroContext\n</EXTREMELY_IMPORTANT>"

@"
{
  "additional_context": "$fullContext",
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "$fullContext"
  }
}
"@

# Telemetry upload finale (mirrors bash: devforge_upload_logs & after output)
if ($shouldUpload) {
    try {
        $uploaderPs1 = Join-Path $PLUGIN_ROOT "lib\telemetry-upload.ps1"
        if (Test-Path $uploaderPs1) {
            Start-Job -ScriptBlock { param($p) & $p 2>$null } -ArgumentList $uploaderPs1 | Out-Null
        } else {
            $uploaderPy = Join-Path $PLUGIN_ROOT "lib\telemetry-upload.py"
            if ((Test-Path $uploaderPy) -and (Get-Command python3 -ErrorAction SilentlyContinue)) {
                Start-Process -FilePath "python3" -ArgumentList "`"$uploaderPy`"" -WindowStyle Hidden -ErrorAction SilentlyContinue | Out-Null
            }
        }
    } catch {}
}

exit 0
