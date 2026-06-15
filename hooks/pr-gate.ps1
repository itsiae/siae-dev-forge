# pr-gate.ps1  -  PowerShell equivalent
# Hook: PreToolUse | Matcher: Bash | Timeout: 15s
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "pr-gate"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

$hookInput   = Read-StdinAll
$toolCommand = Get-JsonField $hookInput "command"
if (-not $toolCommand) { $toolCommand = Get-JsonField $hookInput "tool_input.command" }

if ($toolCommand -notmatch 'gh\s+pr\s+(create|edit)') { Write-Output '{}'; exit 0 }

Initialize-DevForgeSession 2>$null
$safeCmd = Convert-ToDevForgeJson $toolCommand
Write-DevForgeLog -Event "pr_gate" -Status "success" -Meta "{`"check`":`"pr_security_activated`",`"command`":`"$safeCmd`"}" 2>$null

# ── Runner auto-bootstrap SYNC v1.63.8 ─────────────────────────────────────
# Garantisce i runner OSS installati PRIMA del security scan.
# Non-blocking: warning se install fallisce, ma il scan prosegue.
try {
    $runnerBootstrapPs1 = Join-Path $PLUGIN_ROOT "scripts\runner-bootstrap.ps1"
    $runnerBootstrapSh  = Join-Path $PLUGIN_ROOT "scripts\runner-bootstrap.sh"
    if (Test-Path $runnerBootstrapPs1) {
        Write-DevForgeLog -Event "pr_gate" -Status "info" -Meta "{`"check`":`"runner_bootstrap_start`"}" 2>$null
        & $runnerBootstrapPs1 --sync 2>$null
        Write-DevForgeLog -Event "pr_gate" -Status "success" -Meta "{`"check`":`"runner_bootstrap_done`"}" 2>$null
    } elseif (Test-Path $runnerBootstrapSh) {
        Write-DevForgeLog -Event "pr_gate" -Status "info" -Meta "{`"check`":`"runner_bootstrap_start`"}" 2>$null
        # Run bash bootstrap silently in background; non-blocking
        Start-Process bash -ArgumentList "$runnerBootstrapSh --sync" -WindowStyle Hidden -ErrorAction SilentlyContinue
        Write-DevForgeLog -Event "pr_gate" -Status "success" -Meta "{`"check`":`"runner_bootstrap_done`"}" 2>$null
    }
} catch {}

# Security scan on diff
$mergeBase = ""
try { $mergeBase = (git merge-base HEAD origin/sviluppo 2>$null).Trim() } catch {}
if (-not $mergeBase) { try { $mergeBase = (git merge-base HEAD origin/main 2>$null).Trim() } catch {} }
if (-not $mergeBase) { $mergeBase = "HEAD~1" }

$diffContent = try { (git diff "${mergeBase}...HEAD" 2>$null) } catch { "" }

$criticalFindings = @()

if ($diffContent -match 'AKIA[0-9A-Z]{16}') {
    $criticalFindings += "AWS Access Key (AKIA...) trovata nel diff"
}
if ($diffContent -match '-----BEGIN .* PRIVATE KEY-----') {
    $criticalFindings += "Private key trovata nel diff"
}
if ($diffContent -match '[pP]assword\s*[:=]\s*"[^"]{4,}"') {
    $criticalFindings += "Password hardcoded trovata nel diff"
}
if ($diffContent -match '(mysql|postgres|mongodb|redis|amqp)://[^:]+:[^@]+@') {
    $criticalFindings += "Connection string con credenziali trovata nel diff"
}
if ($diffContent -match 'gh[pousr]_[A-Za-z0-9_]{36,}') {
    $criticalFindings += "GitHub Personal Access Token trovato nel diff"
}
$stripeLines = $diffContent -split "`n" | Where-Object { $_ -notmatch '^\s*#|^\s*//|\$\{|process\.env|os\.environ|System\.getenv' }
if (($stripeLines -join "`n") -match '(sk|rk)_(live|test)_[A-Za-z0-9]{20,}') {
    $criticalFindings += "Stripe secret key trovata nel diff"
}
if ($diffContent -match '(client_secret|secret_key|auth_token|access_token)\s*[:=]\s*"[^"]{8,}"') {
    $criticalFindings += "Generic secret hardcoded trovato nel diff"
}

# API key hardcoded (filter out variable references and required-flag names)
$apiKeyLines = $diffContent -split "`n" | Where-Object { $_ -notmatch 'api_key_required|apiKeyRequired|\$\{?[A-Z_]+\}?' }
if (($apiKeyLines -join "`n") -match '[aA][pP][iI][-_]?[kK][eE][yY]\s*[:=]\s*"[^"]{8,}"') {
    $criticalFindings += "API key hardcoded trovata nel diff"
}

# Bearer/JWT token (filter out comments, env var refs, examples)
$bearerLines = $diffContent -split "`n" | Where-Object { $_ -notmatch '^\s*#|^\s*//|\$\{|process\.env|os\.environ|System\.getenv|<[A-Z_]+>|[Ee]xample' }
if (($bearerLines -join "`n") -match '(Bearer|bearer)\s+[A-Za-z0-9\-_\.]{20,}') {
    $criticalFindings += "Bearer/JWT token trovato nel diff"
}

# AWS Secret Access Key
$awsSecretLines = $diffContent -split "`n" | Where-Object { $_ -match '(?i)(aws_secret|secret_access_key)' }
if (($awsSecretLines -join "`n") -match '[''"][A-Za-z0-9/+=]{40}[''"]') {
    $criticalFindings += "AWS Secret Access Key trovata nel diff"
}

# ── BLOCK if critical findings (mirrors bash: block BEFORE suppressions/Drools) ──
if ($criticalFindings) {
    $findings = $criticalFindings -join "`n"
    $safeFindings = Convert-ToDevForgeJson ("DevForge PR Security Gate  -  BLOCCATO`n`nIssue CRITICI trovati nel diff:`n$findings`n`n--- Remediation ---`n1. Rimuovi i secret dal codice sorgente`n2. Usa AWS Secrets Manager, SSM Parameter Store, o variabili d'ambiente`n3. Se il secret e' gia' stato committato in history: usa BFG Repo-Cleaner per riscrivere la storia`n4. Ruota IMMEDIATAMENTE le credenziali esposte`n5. Dopo la remediation, ri-esegui gh pr create`n`nNON procedere finche' tutti i secret non sono stati rimossi.")
    Write-DevForgeLog -Event "pr_gate" -Status "blocked" -Meta "{`"reason`":`"critical_secrets_found`"}" 2>$null
    @"
{"decision": "block", "reason": "$safeFindings"}
"@
    exit 0
}

# Changed file list (needed for Drools + suppressions checks)
$changedFileList = try { (git diff --name-only "${mergeBase}...HEAD" 2>$null) } catch { "" }

# ── SIAE Semgrep suppressions.yaml schema validation (ADR-009) ──────────────
# bash validates only the fixed path rules/semgrep/siae/suppressions.yaml
$repoTarget = try { (git rev-parse --show-toplevel 2>$null).Trim() } catch { (Get-Location).Path }
$suppressionsFile = Join-Path $repoTarget "rules\semgrep\siae\suppressions.yaml"
if (Test-Path $suppressionsFile) {
    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        try {
            $suppOut = (python3 -c @"
import sys
from pathlib import Path
sys.path.insert(0, r'$PLUGIN_ROOT')
try:
    from lib.review_evidence.suppression_validator import validate_suppressions_yaml, ValidationError
    validate_suppressions_yaml(Path(r'$suppressionsFile'))
    print('OK')
except ValidationError as e:
    print(f'FAIL: {e}', flush=True)
    sys.exit(2)
except ImportError:
    print('SKIP: suppression_validator not importable', flush=True)
    sys.exit(0)
"@ 2>&1)
            $suppRc = $LASTEXITCODE
            if ($suppRc -eq 2) {
                Write-DevForgeLog -Event "pr_gate" -Status "fail" `
                    -Meta "{`"check`":`"suppressions_schema`",`"reason`":`"validation_failed`"}" 2>$null
                $safeSuppOut = Convert-ToDevForgeJson ($suppOut | Select-Object -First 20 | Out-String)
                @"
{
  "permissionDecision": "deny",
  "reason": "DevForge PR Gate — suppressions.yaml schema ADR-009 violation:\n$safeSuppOut"
}
"@
                exit 0
            }
            Write-DevForgeLog -Event "pr_gate" -Status "success" `
                -Meta "{`"check`":`"suppressions_schema`",`"result`":`"$suppOut`"}" 2>$null
        } catch {}
    }
}

# ── Drools DRL review check (ADR-007 + EC-29 — WARNING, NON BLOCK) ────────
# bash uses lib/review_evidence/drools_check.py (verified on disk)
$drlFiles = ($changedFileList -split "`n") | Where-Object { $_ -match '\.drl$' }
if ($drlFiles) {
    # Primary name (confirmed on disk): drools_check.py; fallback: drools_checker.py
    $droolsChecker = Join-Path $PLUGIN_ROOT "lib\review_evidence\drools_check.py"
    if (-not (Test-Path $droolsChecker)) {
        $droolsChecker = Join-Path $PLUGIN_ROOT "lib\review_evidence\drools_checker.py"
    }
    if ((Test-Path $droolsChecker) -and (Get-Command python3 -ErrorAction SilentlyContinue)) {
        try {
            $repoTarget = try { (git rev-parse --show-toplevel 2>$null).Trim() } catch { (Get-Location).Path }
            $prLabels   = if ($env:GITHUB_PR_LABELS) { $env:GITHUB_PR_LABELS } else { "" }
            $drlList    = ($drlFiles | Where-Object { $_ }) -join "`n"
            $droolsOut  = (python3 -c @"
import sys
from pathlib import Path
sys.path.insert(0, r'$PLUGIN_ROOT')
try:
    from lib.review_evidence.drools_check import check_drools_review
    modified = [Path(f.strip()) for f in '''$drlList'''.split('\n') if f.strip()]
    labels = [l.strip() for l in '''$prLabels'''.split(',') if l.strip()]
    result = check_drools_review(modified, labels)
    print(result.message if not result.ok else f'OK via {result.method}')
except ImportError:
    print('SKIP: drools_check not importable')
"@ 2>$null)
            Write-DevForgeLog -Event "pr_gate" -Status "success" `
                -Meta "{`"check`":`"drools_review`",`"output`":`"$($droolsOut.Substring(0, [Math]::Min(200, $droolsOut.Length)))`"}" 2>$null
        } catch {}
    }
}

Write-DevForgeLog -Event "pr_gate" -Status "success" -Meta "{`"check`":`"security_scan_clean`"}" 2>$null

$prGateInstructions = @'
# DevForge PR Gate — Security scan PASSED

Il security scan automatico e' passato (nessun secret nel diff).

## AZIONE OBBLIGATORIA — Dispatch Agent Review

DEVI dispatchare ENTRAMBI gli agent ADESSO, PRIMA di eseguire gh pr create.
Questo NON e' opzionale. NON e' un suggerimento. E' un gate bloccante.

### Step 0: Ottieni il diff (OBBLIGATORIO)

```bash
git diff origin/main...HEAD
```

Salva l'output. Lo passerai nel prompt di ENTRAMBI gli agent.
NON passare i path dei file — passa il DIFF TESTUALE. Leggere file interi spreca token.

### Step 1: Dispatch code-reviewer agent

Usa il tool Agent con subagent_type siae-devforge:code-reviewer.
Il prompt deve includere: il DIFF TESTUALE (da Step 0), design doc se presente.
L'agent NON deve usare Read/Glob per leggere file — tutto il contesto e' nel diff.
ATTENDI il risultato.

Se il verdetto e' BLOCKED (>= 1 CRITICAL): BLOCCA la PR. NON procedere.
Se il verdetto e' CHANGES REQUESTED (>= 1 MAJOR): mostra all'utente e chiedi conferma.
Se il verdetto e' APPROVED: procedi.

### Step 2: Dispatch spec-reviewer agent

Usa il tool Agent con subagent_type siae-devforge:spec-reviewer.
Il prompt deve includere: il DIFF TESTUALE (da Step 0), design doc path per i criteri di accettazione.
L'agent NON deve leggere i file interi — solo il diff + criteri dal design doc.
ATTENDI il risultato.

Se il verdetto e' FAIL: mostra discrepanze e chiedi conferma all'utente.
Se il verdetto e' PASS: procedi.

### Step 3: Verifica versione plugin.json

```bash
LATEST_TAG=$(gh release list --limit 1 --json tagName --jq '.[0].tagName' 2>/dev/null || echo "")
CURRENT_VERSION=$(python3 -c "import json; print(json.load(open('.claude-plugin/plugin.json'))['version'])" 2>/dev/null || echo "")
echo "Ultimo release: $LATEST_TAG"
echo "plugin.json:    v$CURRENT_VERSION"
```

Se versioni uguali: avvisa l'utente che la versione non e' stata aggiornata.

### Step 4: Solo dopo aver completato 1-3, procedi con `gh pr create`

Se hai saltato Step 1 o Step 2, stai violando il gate. FERMATI e torna indietro.

| Pensiero | Realta' |
|----------|---------|
| "Sono solo file markdown, non serve review" | Ogni PR merita review. I bug nascono dalle assunzioni. |
| "Ho gia' verificato io" | Il self-review ha bias. Gli agent sono indipendenti. |
| "L'utente ha fretta" | I bug in produzione rallentano piu' di una review. |
| "Gli agent sono lenti" | Lancia entrambi in parallelo. |
'@

$safePrGate = Convert-ToDevForgeJson $prGateInstructions
$prGateContext = "<EXTREMELY_IMPORTANT>\nDevForge PR Gate attivo  -  security scan PASSED.\n\n$safePrGate\n</EXTREMELY_IMPORTANT>"

@"
{
  "additional_context": "$prGateContext",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "$prGateContext"
  }
}
"@
exit 0
