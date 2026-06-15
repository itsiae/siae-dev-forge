# pre-commit.ps1  -  PowerShell equivalent
# Hook: PreToolUse | Matcher: Bash | Timeout: 10s
param()
$ErrorActionPreference = 'SilentlyContinue'
$env:DEVFORGE_CURRENT_HOOK = "pre-commit"

$SCRIPT_DIR  = Split-Path $MyInvocation.MyCommand.Path
$PLUGIN_ROOT = Split-Path $SCRIPT_DIR
Import-Module (Join-Path $PLUGIN_ROOT "lib\DevForge-Helpers.psm1") -Force 2>$null

$hookInput   = Read-StdinAll
$toolCommand = Get-JsonField $hookInput "command"
if (-not $toolCommand) { $toolCommand = Get-JsonField $hookInput "tool_input.command" }

# Tool counter for periodic catalog re-injection
$toolCounterFile    = Join-Path $HOME ".claude\.devforge-tool-counter"
$counter = if (Test-Path $toolCounterFile) { [int](Get-Content $toolCounterFile -Raw).Trim() } else { 0 }
$counter++
$counter | Set-Content $toolCounterFile -NoNewline

$sessionSkills = Get-DevForgeSessionSkills

# Detect git commit / checkout — mirrors bash 3-tier compound-command parser (cmd-parser.sh)
# Tier 1: standard compound operators (&&, ||, ;) and start of string
# Tier 2: env-var prefix pattern (VAR=val git commit)
# Tier 3: cd-then-commit pattern (cd X && git commit)
$isGitCommit = (
    $toolCommand -match '(?:^|&&|\|{2}|;)\s*(?:[A-Z_][A-Z0-9_]*=\S*\s+)*git\s+commit' -or
    $toolCommand -match '\benv\s+[^;|&]*git\s+commit' -or
    $toolCommand -match '\bcd\s+\S+\s*&&\s*git\s+commit'
)
$isGitCheckout = $toolCommand -match '(?:^|&&|\|{2}|;)\s*git\s+(?:checkout|switch)'

if ($isGitCommit) {
    if ($sessionSkills -notlike "*siae-git-workflow*") {
        Initialize-DevForgeSession 2>$null
        $safeCmd = Convert-ToDevForgeJson $toolCommand
        Write-DevForgeLog -Event "pre_commit" -Status "blocked" `
            -Meta "{`"command`":`"$safeCmd`",`"skill_missing`":`"siae-git-workflow`"}" 2>$null
        # Dynamic block-explainer (mirrors devforge_block_explainer siae-git-workflow in bash)
        $pcExpl = ""
        if ($env:DEVFORGE_DISABLE_EXPLAINER -ne "1") {
            $explainerCache = Join-Path $HOME ".claude\.devforge-explainer-cache\siae-git-workflow"
            if (Test-Path $explainerCache) {
                $cacheMtime = (Get-Item $explainerCache).LastWriteTime
                if (([DateTime]::UtcNow - $cacheMtime).TotalSeconds -lt 86400) {
                    $cached = (Get-Content $explainerCache -Raw -ErrorAction SilentlyContinue).Trim()
                    if ($cached) { $pcExpl = " $cached" }
                }
            }
            if (-not $pcExpl) {
                try {
                    $adoptionAnalyzer = Join-Path $PLUGIN_ROOT "lib\adoption-analyzer.py"
                    if ((Test-Path $adoptionAnalyzer) -and (Get-Command python3 -ErrorAction SilentlyContinue)) {
                        $explText = python3 $adoptionAnalyzer --format block --skill siae-git-workflow 2>$null
                        if ($explText) {
                            $cacheDir = Join-Path $HOME ".claude\.devforge-explainer-cache"
                            if (-not (Test-Path $cacheDir)) { New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null }
                            Set-Content $explainerCache $explText.Trim() -NoNewline
                            $pcExpl = " $($explText.Trim())"
                        }
                    }
                } catch {}
            }
        }
        @"
{
  "decision": "block",
  "reason": "DevForge Git Gate — BLOCCATO. NON hai invocato siae-git-workflow in questa sessione. La skill stabilisce naming convention, conventional commits, e pre-flight checks. Invoca siae-git-workflow PRIMA di procedere con il commit: Skill tool -> siae-devforge:siae-git-workflow. Dopo aver invocato la skill, potrai procedere.$pcExpl"
}
"@
        exit 0
    }

    # ── Task-scope shadow log (ADR-001) ──────────────────────────────
    # Session is still source of truth — we just record divergence for
    # post-deploy analysis (mirrors bash pre-commit behaviour).
    $pcUseSession = $env:DEVFORGE_USE_SESSION_SCOPE
    if ($pcUseSession -ne "1") {
        try {
            $pcTaskId = Get-DevForgeTaskId 2>$null
            if ($pcTaskId) {
                $pcInvokedFile = Join-Path $HOME ".claude\.devforge-task-skills\$pcTaskId\skills_invoked"
                $pcTaskOk = $false
                if (Test-Path $pcInvokedFile) {
                    $pcInvoked = Get-Content $pcInvokedFile -ErrorAction SilentlyContinue
                    if ($pcInvoked -contains "siae-git-workflow") { $pcTaskOk = $true }
                }
                # session_ok = true here (we passed the elseif above)
                if (-not $pcTaskOk) {
                    Write-DevForgeLog -Event "pre_commit_task_divergence" -Status "info" `
                        -Meta "{`"task_id`":`"$pcTaskId`",`"session`":1,`"task`":0}" 2>$null
                }
            }
        } catch {}
    }

    $SKILL_REMINDER = ""

    # Coverage gate
    $coverageFile = Join-Path $HOME ".claude\.devforge-last-coverage"
    if (Test-Path $coverageFile) {
        $covData = (Get-Content $coverageFile -Raw).Trim().Split('|')
        $covPct  = $covData[0]; $covTs = if ($covData.Count -gt 1) { $covData[1] } else { "0" }
        if ($covPct -match '^\d+(\.\d+)?$') {
            $branch    = try { (git branch --show-current 2>$null).Trim() } catch { "" }
            $threshold = if ($branch -match '^feature/') { 80 } else { 70 }
            $covInt    = [int]($covPct -replace '\.\d+$', '')
            if ($covInt -lt $threshold) {
                $nowS  = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
                $covAge = $nowS - [long]$covTs
                if ($covAge -lt 1800) {
                    Initialize-DevForgeSession 2>$null
                    $safeBranch = Convert-ToDevForgeJson $branch
                    Write-DevForgeLog -Event "coverage_gate" -Status "blocked" `
                        -Meta "{`"coverage`":$covPct,`"threshold`":$threshold,`"branch`":`"$safeBranch`"}" 2>$null
                    @"
{
  "decision": "block",
  "reason": "DevForge Coverage Gate  -  BLOCCATO. Coverage attuale: ${covPct}% (soglia minima: ${threshold}%). Aggiungi test per raggiungere almeno ${threshold}% di copertura prima di committare. Branch: $branch (feature = 80%, altro = 70%)."
}
"@
                    exit 0
                }
            }
        }
    }

    # Coverage force-run: if staging test files and coverage is stale
    $stagedFiles = try { (git diff --cached --name-only 2>$null) } catch { "" }
    $stagedTestHits = $stagedFiles | Where-Object { $_ -match '\.(spec|test)\.|Test\.java$|IT\.java$|test_.*\.py$|_test\.go$' }
    if ($stagedTestHits) {
        $covAge = 9999
        if (Test-Path $coverageFile) {
            $covTs2 = (Get-Content $coverageFile -Raw).Trim().Split('|')[1]
            $nowS   = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
            $covAge = $nowS - [long]$covTs2
        }
        if ($covAge -gt 1800) {
            Initialize-DevForgeSession 2>$null
            Write-DevForgeLog -Event "coverage_force_run" -Status "blocked" -Meta "{`"age_s`":$covAge}" 2>$null
            @"
{
  "decision": "block",
  "reason": "DevForge Coverage Force-Run  -  BLOCCATO. Stai committando file di test ma i dati di coverage sono stale (${covAge}s > 1800s) o assenti. Esegui la test suite con coverage (mvn test, npm test -- --coverage, pytest --cov) prima del commit."
}
"@
            exit 0
        }
    }

    # Proceed to quality gate instructions
    Initialize-DevForgeSession 2>$null
    $safeCmd = Convert-ToDevForgeJson $toolCommand
    Write-DevForgeLog -Event "quality_gate" -Status "success" `
        -Meta "{`"check_name`":`"pre_commit_activated`",`"command`":`"$safeCmd`"}" 2>$null

    # Generate catalog re-injection if counter interval hit (every 20 calls)
    $catalogReinject = ""
    if ($counter % 20 -eq 0) {
        $skillsJs = Join-Path $PLUGIN_ROOT "lib\skills-core.js"
        if (Test-Path $skillsJs) {
            try { $catalogReinject = (node $skillsJs $PLUGIN_ROOT 2>$null) } catch {}
        }
    }

    $precommitInstructions = @'
# DevForge Pre-Commit Quality Gate

Prima di procedere con il commit, DEVI eseguire TUTTE le verifiche seguenti sui file staged.
Se una qualsiasi verifica fallisce, BLOCCA il commit e mostra la pre-flight card appropriata
secondo il DevForge Visual Design System.

---

## 1. Secret Scan (CRITICO)

Controlla TUTTI i file staged per i seguenti pattern. Se trovi una corrispondenza,
mostra la pre-flight card CRITICO e BLOCCA il commit.

Pattern regex da intercettare:
- **AWS Keys**: `AKIA[0-9A-Z]{16}`, `aws_secret_access_key\s*=\s*.+`
- **Password**: `[pP]assword\s*[:=]\s*["'][^"']+["']`
- **API Key**: `[aA][pP][iI][-_]?[kK][eE][yY]\s*[:=]\s*["'][^"']+["']`
- **Token**: `[tT]oken\s*[:=]\s*["'][^"']+["']`
- **Secret generico**: `[sS]ecret\s*[:=]\s*["'][^"']+["']`
- **Env hardcoded**: `process\.env\.\w+\s*\|\|\s*["'][^"']+["']`
- **Private key**: `-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----`
- **Connection string con password**: `(mysql|postgres|mongodb)://[^:]+:[^@]+@`

File ad alto rischio da verificare sempre:
- `.env`, `.env.*` — mai in git
- `.aws/credentials` — mai in git
- `application-*.yml` con campi password/secret
- Qualsiasi file con estensione `.pem`, `.key`, `.p12`, `.pfx`

Se trovi un secret:

| CRITICO (irreversibile) — DevForge · pre-commit-quality-gate |
|:---|
| COMMIT BLOCCATO — SECRET RILEVATO |
| Pattern: `[tipo di secret rilevato]` |
| 1. Azione: Rimuovi il secret prima di procedere |
| File: `[percorso del file]` |
| Perche': Credenziali nei sorgenti sono una violazione critica di sicurezza |
| Se non risolto: Le credenziali finiscono nel repository e sono compromesse |

---

## 2. Naming Convention Check (MEDIO)

Verifica che i file staged rispettino le convenzioni SIAE:

- **File sorgente**: `kebab-case` (es. `user-service.ts`, `payment-handler.ts`)
  - Eccezioni: file Python usano `snake_case` (es. `user_service.py`)
  - Eccezioni: file Terraform di base usano `_prefix` (es. `_input.tf`, `_local.tf`)
  - Eccezioni: classi Java seguono `PascalCase` (es. `UserService.java`)
- **Classi / Tipi**: `PascalCase` (es. `UserService`, `PaymentDto`)
- **Costanti**: `UPPER_SNAKE_CASE` (es. `MAX_RETRY_COUNT`)
- **Directory**: `kebab-case` (es. `diritti-api/`, `common-networking/`)

Se trovi violazioni, elencale con una pre-flight card MEDIO prima di procedere.

---

## 3. Test Check (MEDIO)

Per ogni file sorgente modificato nello staging, verifica che esista un file di test corrispondente:

| Stack | File sorgente | File test atteso |
|-------|--------------|-----------------|
| TypeScript | `src/user-service.ts` | `test/user-service.spec.ts` o `__tests__/user-service.spec.ts` |
| Java | `src/.../UserService.java` | `test/.../UserServiceTest.java` o `UserServiceIT.java` |
| Python | `src/user_service.py` | `tests/test_user_service.py` |

Se mancano test per file sorgente modificati, avvisa l'utente con una pre-flight card MEDIO.
Non bloccare il commit, ma segnala chiaramente i file senza copertura test.

---

## 4. File Size Check (ALTO)

Controlla che nessun file staged superi 1 MB (1048576 byte).

File grandi nel repository causano problemi di performance e spesso indicano
che un artefatto binario e' stato aggiunto per errore.

Se trovi file > 1 MB:

| ALTO (difficile da annullare) — DevForge · pre-commit-quality-gate |
|:---|
| OPERAZIONE DIFFICILE DA ANNULLARE |
| File: `[percorso del file] ([dimensione] MB)` |
| 1. Azione: File staged supera 1 MB |
| Perche': File grandi degradano performance del repository |
| Se NO: Il file grande viene committato nel repository |

---

## 5. Lint Check (MEDIO)

Se il progetto ha un linter configurato, eseguilo sui file staged:

| Linter | File di config | Comando |
|--------|---------------|---------|
| **ESLint** | `.eslintrc.*`, `eslint.config.*` | `npx eslint [files]` |
| **Checkstyle** | `checkstyle.xml`, nel POM | `mvn checkstyle:check` |
| **Flake8** | `.flake8`, `setup.cfg` | `flake8 [files]` |
| **tflint** | `.tflint.hcl` | `tflint` |
| **Prettier** | `.prettierrc*` | `npx prettier --check [files]` |
| **Shellcheck** | `.shellcheckrc` | `shellcheck [files.sh]` |

Verifica se il file di configurazione esiste nella root del progetto E se il binary del linter
e' disponibile nel PATH (usa `which <linter>` o `command -v <linter>`).

Se entrambe le condizioni sono vere, esegui il linter. Se rileva errori, mostra una pre-flight
card MEDIO con il riepilogo degli errori prima di procedere con il commit.

In tutti gli altri casi (config assente, binary non installato, errore di rete, timeout),
salta silenziosamente con SKIP — non bloccare mai il commit per tool assenti.

---

## Riepilogo Quality Gate

Dopo aver completato tutte le verifiche, mostra un riepilogo compatto come markdown table.

Usa queste emoji per ogni esito:
- PASS  -> OK
- FAIL  -> FAIL
- WARN  -> WARN
- SKIP  -> SKIP

Per l'esito complessivo:
- Tutti i check bloccanti PASS -> COMMIT CONSENTITO
- Almeno un check bloccante FAIL -> COMMIT BLOCCATO
- Solo check non-bloccanti in WARN/FAIL -> COMMIT CONSENTITO CON AVVISI

Esempio di formato:

| DevForge · Pre-Commit Quality Gate — Riepilogo |
|:---|
| 1. Secret Scan:       OK PASS |
| 2. Naming Convention: OK PASS |
| 3. Test Coverage:     SKIP (file .md) |
| 4. File Size:         OK PASS |
| 5. Lint Check:        SKIP |
| **Esito: COMMIT CONSENTITO** |

**Regole di blocco:**
- Secret Scan FAIL -> COMMIT BLOCCATO (non negoziabile)
- File Size FAIL -> COMMIT BLOCCATO (richiede conferma esplicita per override)
- Naming / Test / Lint FAIL -> Mostra warning, consenti commit con conferma utente

Procedi con il commit SOLO se tutte le verifiche bloccanti passano.
'@

    $safeInstructions = Convert-ToDevForgeJson $precommitInstructions

    # Compose catalog section if due for re-injection
    $catalogSection = ""
    if ($catalogReinject) {
        $safeCatalog = Convert-ToDevForgeJson $catalogReinject
        $catalogSection = "\n\n**DevForge Skill Catalog (re-injection periodica):**\n\n$safeCatalog"
    }

    $precommitContext = "${SKILL_REMINDER}<EXTREMELY_IMPORTANT>\nDevForge Pre-Commit Quality Gate attivo.\n\n**PRIMA di eseguire qualsiasi commit, DEVI completare TUTTE le verifiche seguenti sui file staged.**\n\n$safeInstructions$catalogSection\n</EXTREMELY_IMPORTANT>"

    @"
{
  "additional_context": "$precommitContext",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "$precommitContext"
  }
}
"@
    exit 0

} elseif ($isGitCheckout) {
    # Branch checkout: warn if feature branch without design doc
    # Step 1: try to extract JIRA ID from the command itself
    $branchName = ($toolCommand -split '\s+' | Select-Object -Last 1).Trim()
    $jiraId = if ($branchName -match '([A-Z]+-\d+)') { $Matches[1] } else { "" }

    # Step 2: if not found in command, try $env:BRANCH_NAME
    if (-not $jiraId -and $env:BRANCH_NAME) {
        if ($env:BRANCH_NAME -match '([A-Z]+-\d+)') { $jiraId = $Matches[1] }
    }

    # Step 3: if still not found, try current git branch
    if (-not $jiraId) {
        $currentBranchForJira = try { (git rev-parse --abbrev-ref HEAD 2>$null).Trim() } catch { "" }
        if ($currentBranchForJira -match '([A-Z]+-\d+)') { $jiraId = $Matches[1] }
    }

    if (-not $jiraId) { Write-Output '{}'; exit 0 }

    $plansDir = Join-Path $PLUGIN_ROOT "docs\plans"
    if (Test-Path $plansDir) {
        $designDoc = Get-ChildItem $plansDir -Filter "*$jiraId*design*" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($designDoc) { Write-Output '{}'; exit 0 }
    }

    $warn = "Stai creando il branch '$branchName'. Non esiste un design doc in docs/plans/ per $jiraId. Hai eseguito siae-brainstorming prima di iniziare il codice? Procedo comunque con git checkout, ma il design e' consigliato prima dell'implementazione."
    $safeWarn = Convert-ToDevForgeJson $warn
    $branchContext = "<IMPORTANT>\nDevForge Branch Check: $safeWarn\n</IMPORTANT>"

    @"
{
  "additional_context": "$branchContext",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "$branchContext"
  }
}
"@
    exit 0

} else {
    # Non-git commands: periodic catalog re-injection
    if ($counter % 20 -eq 0) {
        $skillsJs = Join-Path $PLUGIN_ROOT "lib\skills-core.js"
        $catalog  = ""
        if (Test-Path $skillsJs) {
            try { $catalog = (node $skillsJs $PLUGIN_ROOT 2>$null) } catch {}
        }
        if ($catalog) {
            $safeCatalog = Convert-ToDevForgeJson $catalog
            $reinjectContext = "<IMPORTANT>\nDevForge Skill Catalog (reminder periodico - invoca le skill rilevanti):\n\n$safeCatalog\n</IMPORTANT>"
            @"
{
  "additional_context": "$reinjectContext",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "$reinjectContext"
  }
}
"@
            exit 0
        }
    }
    Write-Output '{}'
    exit 0
}
