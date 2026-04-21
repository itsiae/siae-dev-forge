# Windows Telemetry Enforcement — Design Doc

**Data:** 2026-04-21
**Autore:** Lorenzo De Tomasi
**Stato:** Draft in review (post-brainstorming, scope enforcement-only)
**Branch target:** `feat/windows-telemetry-enforcement`
**Repo:** `itsiae/siae-dev-forge`
**SP stima:** 6 SP-Umano / 2.5 SP-Augmented
**Scope:** enforcement della telemetria esistente su Windows — **NON aggiunge** nuovi event type, stream, Lambda, dashboard. Garantisce solo che le dipendenze runtime (`bash`, `python3`, `jq`) siano presenti così i log esistenti (`session_start`, `session_end`, `commit_created`, `skill_invoked`, …) partano anche da Windows identici a Mac/Linux.

---

## 1. Contesto e motivazione

### 1.1. Stato attuale

Telemetria DevForge è hook-based (bash) con upload S3 via `lib/telemetry-upload.sh`. Dopo PR1/PR2/PR3 (Telemetry V2 initiative, memoria `project_telemetry_v2.md`), il sistema è robusto su Mac/Linux. I log emessi oggi:

- `session_start`, `session_end`
- `commit_created`
- `skill_invoked`
- `pr_merged`
- `repair_needed` (nuovo, vedi §5 — unico event aggiunto, riutilizza lo schema esistente)

Tutti gli event atterrano in `~/.claude/devforge-state/<sid>/outbox/*.json` → upload S3 `siae-devforge-telemetry/devforge-logs/` → consumo via skill `siae-dev-analytics` esistente.

### 1.2. Root cause Windows

`hooks/run-hook.cmd:37-39` esce con `exit /b 0` **silenziosamente** quando bash non è trovato. Conseguenze a cascata:

- Plugin si installa ma zero hook eseguono
- Zero telemetria emessa → dev **invisibile** nei log
- Il dev consuma seat Anthropic (98 seat SIAE) senza apparire nei dati
- Il dev stesso non riceve segnale di malfunzionamento

Dipendenza secondaria: anche con bash presente, `lib/logger.sh:48-70` cade in modalità **degraded** se `python3` manca (perdita garanzie zero-loss di PR-A: no lock, no fsync). Git for Windows include bash+curl ma **non** python3 né jq.

### 1.3. Goal

Ogni dev Windows SIAE emette gli stessi log telemetria che emette un dev Mac/Linux — nessuna divergenza di schema, pipeline, storage. L'enforcement avviene a livello di **dipendenze runtime**, non a livello di nuovi stream.

### 1.4. Non-goal (esplicitamente fuori scope)

- **Nuovi event type proprietari** (canary_alive, heartbeat, ecc.) — scartato. Usiamo i log esistenti come segnale di vita: "dev vivo" = "ha emesso `session_start` negli ultimi 7gg".
- **Lambda report dedicato silent-users** — la query va fatta in skill `siae-dev-analytics` esistente. Nessuna nuova infra.
- **Notifiche push (Slack/email)** — pattern SIAE è drop file su S3, consumo via skill analytics.
- **MDM/Intune** — no accesso IT SIAE attuale.
- **Port PowerShell dei hook** — duplicato non mantenibile.
- **Fix API key hardcoded** — tech debt pre-esistente, non aggravato.

### 1.5. Anti-scope creep

Principio guida: **"enforcement di quello che abbiamo, non una cosa in più"**. Ogni aggiunta di codice che non serve a far partire i log esistenti su Windows va respinta dal design review.

---

## 2. Stakeholder e vincoli

### 2.1. Stakeholder

- **Lorenzo De Tomasi** (owner, approvatore)
- **Owner SIAE** (Carlo Stoppani, Alberto Perella) per escalation broken users
- **Dev Windows SIAE** — numerosità da mappare post-rollout via log esistenti
- **IT SIAE** — fuori scope ora

### 2.2. Vincoli

- **C1:** No admin rights required (user-scope install)
- **C2:** Offline/air-gapped install supportato via asset embedded in GitHub release
- **C3:** No dipendenza da winget/choco/scoop abilitati
- **C4:** Feature parity 100% pipeline telemetria Mac/Linux
- **C5:** Zero regression Mac/Linux (CI matrix obbligatoria)
- **C6:** Rollback automatico in caso di install fallita (transazionale)
- **C7:** SHA256 pin per ogni binario scaricato (supply chain)
- **C8:** Zero nuovi event type diversi da quelli già in uso

---

## 3. Architettura target

```
                          ┌─────────────────────────────────────┐
                          │  GitHub Release itsiae/siae-dev-forge    │
                          │  assets:                            │
                          │   - plugin.tar.gz                   │
                          │   - install.ps1                     │
                          │   - PortableGit-x64.7z.exe   (~50MB)│
                          │   - PortableGit-arm64.7z.exe (~60MB)│
                          │   - python-standalone-x64.tar.gz (~30MB)
                          │   - python-standalone-arm64.tar.gz (~30MB)
                          │   - jq-win64.exe, jq-arm64.exe      │
                          │   - SHA256SUMS                      │
                          └─────────────────────────────────────┘
                                          │
                          ┌───────────────┴──────────────┐
                          ▼                              ▼
          ┌───────────────────────────────┐   ┌─────────────────────┐
          │   Windows dev laptop          │   │  Mac/Linux laptop   │
          │   install.ps1 (entry)         │   │  install.sh         │
          │     │                         │   │   (invariato)       │
          │     ├─ Ensure-Bash            │   └─────────────────────┘
          │     │   ├─ winget Git.Git     │
          │     │   ├─ choco / scoop      │
          │     │   ├─ direct download    │
          │     │   └─ PortableGit asset  │
          │     │                         │
          │     ├─ Ensure-Python3         │
          │     │   ├─ winget Python      │
          │     │   ├─ direct python.org  │
          │     │   └─ Python-Standalone  │
          │     │       asset (embedded)  │
          │     │                         │
          │     ├─ Ensure-Jq              │
          │     │   └─ jq-win64.exe asset │
          │     │                         │
          │     ├─ claude plugin install  │
          │     └─ Invoke-HealthCheck     │
          │         (dry-run session-start│
          │          hook + verify log)   │
          │                               │
          │   Runtime (100% parity Mac):  │
          │    Claude Code                │
          │      └─ hooks.json            │
          │           └─ run-hook.cmd     │
          │                ├─ bash OK ──▶ exec bash hook (pipeline standard)
          │                │                                             │
          │                └─ bash KO ──▶ fail LOUD + flag +            │
          │                              emit-repair-event.ps1         │
          │                                     │                       │
          │                                     ▼                       ▼
          │                            ~/.claude/devforge-state/<sid>/outbox/ (schema identico Mac/Linux)
          │                                                             │
          └─────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
                     S3 siae-devforge-telemetry/devforge-logs/
                                          │
                                          ▼
                  (Query esistenti via skill siae-dev-analytics —
                   nessun Lambda nuovo, nessun report dedicato)
```

**Principio guida:** `install.ps1` garantisce che le 3 dipendenze runtime (bash, python3, jq) siano presenti. Tutto il resto del plugin gira invariato. Nessun duplicato PowerShell, nessun nuovo event type (eccetto `repair_needed` minimale di cui al §5), nessun Lambda nuovo.

---

## 4. ADR — Architectural Decision Records

### ADR-01. Enforcement-only: no nuovi stream

**Decisione:** l'iniziativa **non introduce** nuovi event type, stream, Lambda, dashboard. Si limita a garantire bash+python3+jq su Windows. I log telemetria esistenti forniscono già ogni segnale di cui abbiamo bisogno (vita, attività, anomalie).

**Alternativa scartata:** canary statusline JS + Lambda silent-users dedicato + EventBridge + drop Excel. Ridondante rispetto ai log esistenti, aumenta superficie di maintenance, test, e infra cost senza benefit informativo.

**Conseguenza:** codebase di questa iniziativa è concentrato in `install.ps1` + 3 file runtime minori. Zero aggiunte a `lib/`, zero Lambda, zero IaC.

### ADR-02. Bash-guaranteed (no PS duplicato)

**Decisione:** garantiamo bash+python3+jq su Windows tramite install chain. I hook restano bash, la pipeline telemetria resta identica.

**Alternativa scartata:** port PS completo di hook+logger+uploader. Maintenance drift, test doppi.

### ADR-03. PortableGit + Python-Standalone embedded nel release asset

**Decisione:** GitHub release del plugin include:
- `PortableGit-x64.7z.exe` + variant `arm64`
- `python-standalone-x64.tar.gz` + variant `arm64` (da `indygreg/python-build-standalone`, binari portable che funzionano senza installer)
- `jq-win64.exe` + `jq-arm64.exe`
- `SHA256SUMS` con hash di tutti

L'installer li scarica solo se i metodi preferiti (winget/choco/direct-from-upstream) falliscono. Fornisce il fallback per ambienti air-gapped o con policy corp restrittive.

**Dimensione totale release:** ~180MB (ok per GitHub release 2GB limit).

### ADR-04. `emit-repair-event.ps1` riusa schema esistente (1 event type `repair_needed`)

**Decisione:** UN singolo event type nuovo, minimale, che riutilizza lo schema standard del logger (`event`, `schema_version`, `ts`, `user_raw`, `hostname`, `os`). Scritto nell'outbox esistente, consumato dalla pipeline S3 esistente, deduplicato dalla Lambda esistente.

**Alternativa scartata:** zero nuovi event type. Impossibile — senza qualche segnale dal lato Windows quando bash manca, il problema resta invisibile. Un singolo event type è il minimo indispensabile, ed è strettamente allineato alla tipologia già esistente (event in outbox JSONL).

### ADR-05. Self-healing runtime con flag file

**Decisione:** `run-hook.cmd` se bash mancante scrive flag `%APPDATA%\Claude\devforge-needs-repair` + emette `repair_needed` event + fallisce con `exit /b 1`. Al prossimo SessionStart (se bash ripristinato nel frattempo), il hook `session-start` bash detecta il flag e mostra messaggio repair nel context del model.

### ADR-06. Rollback automatico

**Decisione:** `install.ps1` registra snapshot pre-install (file creati, registry key, scheduled task); su health-check failure ripristina stato precedente.

### ADR-07. Rollout opt-in → GA dopo 7gg

**Decisione:** v1.45.0 in opt-in install manuale → monitoring 7gg → promozione GA auto-update. Panic button `DEVFORGE_DISABLE_REPAIR_EVENT=1`.

### ADR-08. Verifica silent users via log esistenti

**Decisione:** per mappare dev Windows broken/silent usiamo una query ad-hoc sui log esistenti (skill `siae-dev-analytics`), **non** costruiamo Lambda/dashboard dedicato.

Query logica:
```
silent  = seat_list - {users with session_start in last 7d}
broken  = {users with repair_needed event in last 7d}
healthy = {users with session_start AND os=windows AND no repair_needed}
```

Output: Excel prodotto da `siae-dev-analytics` esistente (estensione minore della skill, eventualmente PR separata). Non è parte di questa iniziativa.

---

## 5. Component breakdown

### 5.1. `install.ps1` (PR-1, 5 SP-U / 2 SP-A)

Entry point Windows. Struttura:

```powershell
[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$NoPortableFallback,
    [switch]$Force
)

# Detection
function Find-Bash { ... }    # 8-path detection chain
function Find-Python3 { ... } # py.exe launcher + python.exe PATH + embedded cache
function Find-Jq { ... }      # PATH + PortableGit\usr\bin + embedded cache

# Install chain - BASH
function Install-GitViaWinget { ... }
function Install-GitViaChoco { ... }
function Install-GitViaScoop { ... }
function Install-GitViaDirectDownload { ... }     # GitHub release git-for-windows
function Install-GitViaPortableEmbedded { ... }   # asset PortableGit dal release plugin

# Install chain - PYTHON3
function Install-PythonViaWinget { ... }
function Install-PythonViaDirectDownload { ... }  # python.org installer embedded
function Install-PythonViaStandaloneEmbedded { ... }  # indygreg/python-build-standalone

# Install chain - JQ
function Install-JqFromAsset { ... }              # copia jq.exe in PortableGit\usr\bin\

# Plugin + health
function Install-ClaudePlugin { ... }
function Invoke-HealthCheck { ... }  # dry-run session-start hook + verify event in outbox

# Transactional
function New-InstallSnapshot { ... }
function Invoke-Rollback { ... }
function Write-InstallLog { ... }

try {
    $snapshot = New-InstallSnapshot
    $bash    = Find-Bash    ; if (-not $bash)    { $bash    = Install-GitViaCascade }
    $python  = Find-Python3 ; if (-not $python)  { $python  = Install-PythonViaCascade }
    $jq      = Find-Jq      ; if (-not $jq)      { $jq      = Install-JqFromAsset }
    Install-ClaudePlugin
    if (-not (Invoke-HealthCheck -BashPath $bash -PythonPath $python)) {
        throw "Health check failed - telemetry not reaching outbox"
    }
    # Clear repair flag if set
    Remove-Item "$env:APPDATA\Claude\devforge-needs-repair" -ErrorAction SilentlyContinue
} catch {
    Write-InstallLog "Install failed: $_" -Level Error
    Invoke-Rollback -Snapshot $snapshot
    exit 1
}
```

**One-liner install (documentato nel README):**

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
iwr https://github.com/itsiae/siae-dev-forge/releases/latest/download/install.ps1 -UseBasicParsing | iex
```

**Health-check dettagliato:** esegue `hooks/session-start` in dry-run (env `DEVFORGE_HEALTH_CHECK=1`), verifica che un event `session_start` appaia in `~/.claude/devforge-activity.jsonl` entro 5s. Se no → fallimento → rollback.

### 5.2. `hooks/run-hook.cmd` update (PR-2, parte di 1 SP-U / 0.5 SP-A)

Modifica del fallback silent:

```cmd
REM ... detection chain bash invariata (8 path) ...

REM No bash found - fail LOUD (precedentemente exit /b 0 silent)
echo. >&2
echo [DevForge] bash not found - DevForge hooks disabled. >&2
echo [DevForge] Ripara con: >&2
echo   Set-ExecutionPolicy -Scope Process Bypass -Force >&2
echo   iwr https://github.com/itsiae/siae-dev-forge/releases/latest/download/install.ps1 ^| iex >&2
echo. >&2
if not exist "%APPDATA%\Claude" mkdir "%APPDATA%\Claude" 2>nul
type NUL > "%APPDATA%\Claude\devforge-needs-repair" 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%HOOK_DIR%emit-repair-event.ps1" >nul 2>&1
exit /b 1
```

Cambio critico: `exit /b 1` visibile a Claude Code invece di `exit /b 0` silent.

### 5.3. `hooks/emit-repair-event.ps1` (PR-2, parte di 1 SP-U / 0.5 SP-A)

~20 righe, emette 1 event nell'outbox esistente, schema standard:

```powershell
# emit-repair-event.ps1 — emergency signal path (no bash needed)
# Emette 1 event `repair_needed` nell'outbox standard, schema identico
# a logger.sh output. Consumato dalla pipeline S3 esistente.
$ErrorActionPreference = 'SilentlyContinue'
if ($env:DEVFORGE_DISABLE_REPAIR_EVENT -eq "1") { exit 0 }

$stateDir = Join-Path $env:USERPROFILE ".claude\devforge-state\emergency"
$outbox   = Join-Path $stateDir "outbox"
New-Item -ItemType Directory -Path $outbox -Force | Out-Null

$epoch = [int][double]::Parse((Get-Date -UFormat %s))
$guid  = [guid]::NewGuid().ToString()
$event = @{
    event          = "repair_needed"
    schema_version = 2
    event_id       = $guid
    ts             = $epoch
    user_raw       = $env:USERNAME
    hostname       = $env:COMPUTERNAME
    os             = "windows"
    os_release     = [System.Environment]::OSVersion.VersionString
    arch           = $env:PROCESSOR_ARCHITECTURE
    reason         = "no-bash"
    plugin_version = (Get-Content "$env:USERPROFILE\.claude\plugins\cache\siae-devforge\*\plugin.json" -ErrorAction SilentlyContinue | ConvertFrom-Json).version
    hook_name      = "run-hook-cmd"
} | ConvertTo-Json -Compress

$file = Join-Path $outbox "$guid.json"
[System.IO.File]::WriteAllText($file, $event, [System.Text.UTF8Encoding]::new($false))
```

Upload: avviene quando bash viene ripristinato e il prossimo `session-start` esegue drain del directory `emergency/outbox`. Il drain è aggiunto in `session-start` esistente (§5.4).

### 5.4. `hooks/session-start` addition (PR-2, parte di 1 SP-U / 0.5 SP-A)

Aggiunta minima in bash esistente:

```bash
# hooks/session-start — addition at top of script
# Self-healing: drain emergency outbox se bash è tornato disponibile
# e mostra repair banner se flag presente.
REPAIR_FLAG="${APPDATA:-$HOME/.config}/Claude/devforge-needs-repair"
EMERGENCY_OUTBOX="${HOME}/.claude/devforge-state/emergency/outbox"

if [[ -d "$EMERGENCY_OUTBOX" ]]; then
    # Move emergency events into current session outbox for normal upload
    mkdir -p "${DEVFORGE_SESSION_DIR}/outbox"
    mv "${EMERGENCY_OUTBOX}"/*.json "${DEVFORGE_SESSION_DIR}/outbox/" 2>/dev/null || true
fi

if [[ -f "$REPAIR_FLAG" ]]; then
    cat <<EOF
[DevForge Repair Banner]
Una sessione precedente ha rilevato bash mancante.
Per ripristinare (PowerShell):
  Set-ExecutionPolicy -Scope Process Bypass -Force
  iwr https://github.com/itsiae/siae-dev-forge/releases/latest/download/install.ps1 | iex
EOF
    rm -f "$REPAIR_FLAG"
fi
```

---

## 6. Data model

**Nessuna modifica retrocompatibile a schema esistenti.**

**Un nuovo event type aggiunto** (`repair_needed`), schema identico ai log esistenti — riutilizza i campi `event`, `schema_version`, `event_id`, `ts`, `user_raw`, `hostname`, `os`, `os_release`, `arch`, `plugin_version`, `hook_name` già in uso. Campo nuovo: `reason` (string, enum: `no-bash`). La Lambda dedup esistente gestisce `event_id` correttamente (S3 key deterministica).

---

## 7. Security considerations

| Rischio | Mitigazione |
|---|---|
| Supply chain installer PS | URL GitHub release pinnato + HSTS + checksum verificabile |
| Download Git/Python/jq da URL | SHA256 pin in `SHA256SUMS`, verify prima di exec |
| PortableGit/Python embedded | SHA256 pin + sorgenti ufficiali (git-for-windows project, indygreg python-build-standalone, jq-project) |
| PS `-ExecutionPolicy Bypass` | Scope process-only, file-specific per script plugin-interni, mai scaricati runtime |
| Winget/choco user-scope | Safe, no admin |
| AV quarantine bash.exe/python.exe | Health-check post-install detecta, rollback + event `repair_needed` con reason esteso (enum futuro) |
| Proxy MITM cert self-signed | Documentato in README: `$env:GIT_SSL_CAINFO` |
| API key hardcoded upload | **Tech debt pre-esistente**, NON aggravato, flaggato |
| Path UNC/OneDrive Unicode | `Set-Location -LiteralPath`, quoting rigoroso |
| LongPath > 260 char | `\\?\` prefix, registry HKLM LongPathsEnabled |

---

## 8. Test strategy

### 8.1. Layer 1 — Unit

| Target | Framework | Coverage goal |
|---|---|---|
| `install.ps1` funzioni isolate | Pester 5 + mock winget/choco/Invoke-WebRequest/Expand-Archive | ≥ 90% |
| `emit-repair-event.ps1` | Pester 5 | ≥ 90% |
| `session-start` addition (drain + banner) | bats | ≥ 90% del nuovo codice |

### 8.2. Layer 2 — Integration (GitHub Actions matrix)

Matrix OS: `windows-latest`, `windows-2019`, `ubuntu-latest`, `macos-latest`.

| Scenario | Win | Unix |
|---|---|---|
| Install su runner clean (no Git, no Python) | ✅ | — |
| Install con bash+python già presenti | ✅ (fast-path) | ✅ (no-op verify) |
| Simulazione no-bash runtime (`DEVFORGE_TEST_HIDE_BASH=1`) → run-hook.cmd fail-loud | ✅ | — |
| Simulazione no-python (degraded logger path) | ✅ | ✅ |
| Session-start drain emergency outbox → event atterra in activity.jsonl | ✅ | ✅ |
| Path OneDrive Unicode/spazi | ✅ | ✅ |
| Path > 260 char | ✅ | — |
| No admin (demote shell) | ✅ | — |
| Proxy simulato (mitmproxy) blocca winget → cascade a asset embedded | ✅ | — |
| Idempotenza (install.ps1 2x) | ✅ | — |
| Rollback automatico su health-check inject failure | ✅ | — |
| `-DryRun` flag coverage | ✅ | — |
| Air-gapped (no outbound) → PortableGit+Python-Standalone embedded | ✅ | — |
| SHA256 pin mismatch → abort | ✅ | — |

### 8.3. Layer 3 — Chaos/adversarial (pre-release manual)

- AV quarantine bash.exe/python.exe
- winget+choco+scoop+direct-download tutti bloccati → asset embedded parte
- Anche asset embedded fallisce (disk full) → hard-fail visibile con URL istruzioni
- Kill processo durante install → rollback al riavvio
- Concurrent Claude session (laptop+desktop) → outbox isolation verified

### 8.4. Layer 4 — E2E canary production

- 3-5 volontari Windows SIAE installano v1.45.0-rc1 da URL staging
- Monitoring **sui log esistenti** (`session_start` events da user_canonical volontario) per 7gg
- Go/No-Go: 100% volontari emettono `session_start` regolari per 7gg consecutivi → promote GA opt-in

### 8.5. Zero-regression guards

1. CI matrix 4-OS obbligatoria, block merge se uno rosso
2. Tutti i `tests/**/*.bats` esistenti restano verdi
3. `hooks.json` diff snapshot pre/post PR
4. Schema telemetria backward-compat (solo 1 add: `repair_needed` event)
5. `DEVFORGE_DISABLE_REPAIR_EVENT=1` panic button
6. `run-hook.cmd` testato in polyglot mode

### 8.6. Security review dedicata

Checklist:
- [ ] SHA256 pin presente per ogni binario
- [ ] Nessun `Invoke-Expression` su input non-trusted
- [ ] Nessuno script scaricato eseguito con Bypass
- [ ] Rollback non perde dati utente
- [ ] Tech debt API key pre-esistente NON aggravato

---

## 9. Rollout plan

| Fase | Durata | Gate di promozione |
|---|---|---|
| 1. PR review + CI | 2-3 giorni | Test matrix 4-OS verde + spec-reviewer PASS + security-review PASS + code-review PASS |
| 2. RC staging (opt-in manuale) | 3-5 giorni | 3+ volontari Windows, zero issue critical, log `session_start` regolari |
| 3. GA opt-in | 7 giorni | Mapping dev Windows broken/silent (via query log esistenti) mostra calo vs baseline |
| 4. GA auto-update | permanent | Nessun regression Mac/Linux dopo 7gg GA opt-in |

**Rollback plan di emergenza:** se post-GA emerge regression critical, rollback marketplace a v1.44.x via `claude plugin update --version 1.44.2`, documentato in `docs/ops/windows-rollback.md`.

---

## 10. Acceptance criteria

- [ ] AC-1: `install.ps1` porta una Windows 10/11 clean (no Git, no Python) a stato bash+python3+jq-funzionanti in < 5 minuti via winget path
- [ ] AC-2: Con winget bloccato, installer usa choco/scoop/direct download senza intervento utente
- [ ] AC-3: Su macchina offline, installer usa asset embedded (PortableGit + Python-Standalone + jq) e completa
- [ ] AC-4: Post-install, `hooks/session-start` emette event **byte-identical** (su campi comuni) a Mac/Linux — diff JSON zero
- [ ] AC-5: `hooks/run-hook.cmd` senza bash **non** esce silent: stderr visibile + flag file + event `repair_needed` in outbox
- [ ] AC-6: `emit-repair-event.ps1` produce JSON parseable con schema identico ai log esistenti
- [ ] AC-7: Al ripristino bash, `session-start` drena `emergency/outbox` → event `repair_needed` atterra in S3 `devforge-logs/`
- [ ] AC-8: Test matrix CI 4-OS verde (zero regression)
- [ ] AC-9: `install.ps1 -DryRun` logga tutti i path senza side-effect
- [ ] AC-10: Rollback automatico ripristina stato pre-install su failure iniettato
- [ ] AC-11: SHA256 pin verificato per ogni binario; mismatch → abort
- [ ] AC-12: 3+ volontari Windows SIAE emettono `session_start` events regolari per 7gg RC
- [ ] AC-13: Verifica silent users via query su `siae-dev-analytics` (o script ad-hoc) produce Excel atteso — nessun Lambda dedicato costruito in questa iniziativa
- [ ] AC-14: Zero nuovo Lambda, zero nuova dashboard, zero nuovo Athena table aggiunti in questa PR

---

## 11. Decomposizione in PR

| PR | Scope | SP-U / SP-A | Dipendenze |
|---|---|---|---|
| PR-1 | `install.ps1` + detection + install chain (bash+python3+jq) + health-check + rollback + release asset packaging CI (SHA256SUMS, PortableGit, Python-Standalone, jq) | 5 / 2 | Nessuna |
| PR-2 | `hooks/run-hook.cmd` fail-loud + `hooks/emit-repair-event.ps1` + `hooks/session-start` drain emergency + banner | 1 / 0.5 | PR-1 merged (asset release necessario per one-liner repair) |
| **Totale** | — | **6 / 2.5** | — |

**Test strategy:** ogni PR ha test suite dedicata (Pester/bats), integrati nella matrix 4-OS CI. Nessuna PR merge senza verde.

---

## 12. Riferimenti

- `hooks/run-hook.cmd:37-39` — root cause silent fallback
- `hooks/hooks.json` — hook registration
- `install.sh` — installer bash esistente Mac/Linux (invariato)
- `lib/telemetry-upload.sh` — uploader bash esistente (invariato)
- `lib/logger.sh:48-70` — degraded path se python3 mancante
- `lib/atomic_write.py` — zero-loss PR-A
- `project_telemetry_v2.md` (memoria) — stato PR1/PR2/PR3
- `project_telemetry_zero_loss.md` (memoria) — silent users noti
- `project_anthropic_seats.md` (memoria) — 98 seat ground truth
- `skills/siae-dev-analytics/` — skill esistente per report/query telemetria
- Git for Windows release: https://github.com/git-for-windows/git/releases
- Python-Standalone release: https://github.com/indygreg/python-build-standalone/releases
- jq release: https://github.com/jqlang/jq/releases

---

## 13. Open questions

- **OQ-1:** Superficie dev Windows SIAE (numerosità, OS mix, policy corp) — mappabile via log esistenti dopo rollout.
- **OQ-2:** Cert code-signing `install.ps1` — deferred post-rollout se serve reduzione fricton SmartScreen.
- **OQ-3:** Seat list ground truth — già in memoria `project_anthropic_seats.md`, da spostare in YAML committato quando integriamo la query silent-users in `siae-dev-analytics` (non parte di questa iniziativa).

---

## 14. Log decisioni design review (per tracciabilità brainstorming)

- **v1** (scartata): approccio con canary statusline + Lambda silent-users + PS fallback uploader. Troppa nuova superficie, drift implementativo.
- **v2** (scartata): bash-guaranteed + canary statusline + Lambda silent-users. Feature parity ok ma ancora "cosa in più".
- **v3**: enforcement-only — garantiamo bash+python3+jq su Windows. Approved da feedback utente "non è una cosa in più è un enforcement di quello che abbiamo".
- **v4 (questa, finale)**: confermata **Opzione B — Livello 1+2 completo**: installer garantisce Git for Windows (bash+curl+flock) **E** python3 (zero-loss + token stats) **E** jq (parsing JSON robusto). Feature parity 100% con Mac/Linux. Scartata Opzione A (solo Git for Windows → telemetria degraded) e Opzione C (incremental follow-up). Approved da feedback utente "la cosa migliore che copre piu' di tutto".

### Deep-dive dipendenze runtime (verified code, 2026-04-21)

Da analisi `hooks/*` e `lib/*`:

| Tool | Impact se manca | In Git for Windows bundle? | Fallback nel codice? |
|---|---|---|---|
| bash | 🔴 Zero telemetria (silent exit in `run-hook.cmd:39`) | È lui | Nessun fallback — root cause del problema |
| curl | 🔴 Upload S3 fallisce, NTP skip | ✅ Incluso (MSYS2) | Nessuno nel codice esistente |
| flock | 🟢 Degraded no-lock mode | ✅ Incluso | Sì (telemetry-upload.sh:37-38) |
| python3 | 🟡 Zero-loss degraded (no lock/fsync), token stats skip, user.json skip | ❌ NON incluso | Sì (logger.sh:48-70 printf) ma degraded |
| jq | 🟢 Fallback grep in 5 hook | ❌ NON incluso | Sì ma parsing fragile |
| gh, node | 🟢 Feature opzionali | ❌ NON incluso | Sì |

**Conclusione:** con solo Git for Windows, telemetria arriva ma è degradata (no zero-loss, no token stats). Opzione B elimina anche questa degradazione installando python3+jq come parte dell'enforcement.
