# siae-devforge

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨 DevForge · AI Competence Center                  ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Plugin Claude Code per lo sviluppo software conforme agli standard SIAE.**
> Copre l'intero SDLC (Software Development Life Cycle) con un backbone deterministico
> a 4 fasi e un catalog specialistico di **43 skill, 10 comandi, 5 agent, 25 hook**.

| Metadato | Valore |
|---|---|
| Versione | `1.63.7` |
| Autore | SIAE AI Competence Center · `ai-cc@siae.it` |
| Licenza | Proprietary |
| Target | Claude Code CLI ≥ 0.x, Anthropic SDK |
| Stack supportati | Java/Spring · TypeScript/Node · Python · Flutter/Dart · HCL/Terraform · Vue/React/Angular · Robot Framework |

---

## TL;DR

DevForge **impone un workflow** (brainstorming → plan → TDD → verification) attraverso
**hook deterministici** e **gate task-scoped**, e offre **skill specialistiche** per
ogni stack tecnologico SIAE. La filosofia: l'AI accelera, ma il rigore non si negozia.
Nessuna feature, nessun bug fix, nessun refactor entra in produzione senza passare per
design esplicito, test scritti prima del codice, e verifica evidence-based.

---

## Indice

1. [Installazione](#installazione)
2. [SDLC Backbone — Le 4 fasi obbligatorie](#sdlc-backbone--le-4-fasi-obbligatorie)
3. [Catalog skill (43)](#catalog-skill-43)
4. [Slash command (10)](#slash-command-10)
5. [Agent (5)](#agent-5)
6. [Hook (25)](#hook-25)
7. [Architettura del plugin](#architettura-del-plugin)
8. [Telemetria & enforcement evidence-based](#telemetria--enforcement-evidence-based)
9. [Integrazione MCP](#integrazione-mcp)
10. [Versioning & changelog](#versioning--changelog)
11. [Contributing](#contributing)
12. [Licenza](#licenza)

---

## Installazione

DevForge è un plugin Claude Code distribuito tramite marketplace privato SIAE.

```bash
# In Claude Code, aggiungi il marketplace e installa
/plugin marketplace add itsiae/siae-dev-forge
/plugin install siae-devforge
```

A primo avvio il hook `session-start` esegue `siae-onboarding` e mostra il welcome message
con il catalog delle skill disponibili. Verifica installazione:

```bash
ls ~/.claude/plugins/cache/siae-devforge/  # plugin.json, skills/, commands/, agents/, hooks/
```

**Aggiornamenti**: il marketplace usa `plugin.json` + `marketplace.json` come dual-source
versione. Dopo `git pull` su un clone locale, esegui `/plugin reload` per sync della cache.

---

## SDLC Backbone — Le 4 fasi obbligatorie

Il backbone è la **catena minima** che ogni task implementativo deve attraversare.
Saltare un anello produce regressioni che le skill specialistiche non possono recuperare.

```
┌─────────────────────────────────────────────────────────────┐
│  1. BRAINSTORMING   →  7-step design intake → opzioni → doc │
│  2. WRITING-PLANS   →  piano bite-sized in docs/plans/<X>/  │
│  3. TDD             →  RED → GREEN → REFACTOR (test first)  │
│  4. VERIFICATION    →  evidence-based completion gate       │
└─────────────────────────────────────────────────────────────┘
```

**Fase 1 — `siae-brainstorming`** *(Rigid)*. Intake → scope → options → design →
review → approval → handoff. Mandatory per qualsiasi modifica codice. Produce design doc
in `docs/plans/<topic>-design.md`.

**Fase 2 — `siae-writing-plans`** *(Rigid)*. Decompone il design in task bite-sized in
`docs/plans/<topic>/`: `overview.md` + `task-NN-<nome>.md`. Hand-off a `siae-subagent-development`
(stessa sessione, `/forge-implement`) o `siae-executing-plans` (sessione separata, `/forge-execute`).

**Fase 3 — `siae-tdd`** *(Rigid)*. RED-GREEN-REFACTOR per ogni task implementativo. Test scritti
**prima** del codice di produzione. Hook `tdd-gate` blocca commit di codice senza test corrispondenti
(file taxonomy in `lib/file-taxonomy.sh`).

**Fase 4 — `siae-verification`** *(Rigid)*. Hard-gate 5-step prima di dichiarare un task completato:
test eseguiti, output catturato, behaviour confermato, regression check, evidence loggata. Hook
`stop-gate` blocca dichiarazioni di "fatto" senza evidence.

**Best-after pattern**: ogni skill specialistica (es. `siae-frontend`, `siae-iac`, `siae-finops`)
si aggancia al backbone — non lo sostituisce. Esempio: design feature frontend = `siae-frontend` +
`siae-brainstorming` (sempre) → `siae-writing-plans` → `siae-tdd` con `siae-frontend` + `siae-security` →
`siae-verification`.

---

## Catalog skill (43)

Tabella organizzata per fase SDLC. **Rigid** = backbone non-bypassabile;
**Flexible** = specialistica con stile cooperativo; **Auto** = invocata da hook senza prompt utente.

### Fase 1 — Init & Onboarding

| Skill | Tipo | Quando invocarla |
|---|---|---|
| `siae-onboarding` | Auto | Inizio sessione, cambio progetto |
| `siae-codebase-map` | Flexible | Mappa struttura singolo repo → `docs/CODEBASE_MAP.md` |
| `siae-codebase-map-tiered` | Rigid sub | Gerarchia CLAUDE.md (L1 root + L2 package + L3 child) |
| `siae-microservices-map` | Flexible | Mappa sistema distribuito multi-repo (10+ servizi) |
| `siae-service-logic-map` | Flexible | Profilazione microservizi per documentazione o impact analysis |
| `siae-git-worktrees` | Rigid | Setup workspace isolato pre-implementazione |

### Fase 2 — Design

| Skill | Tipo | Quando invocarla |
|---|---|---|
| `siae-brainstorming` | **Rigid** | **SEMPRE** prima di qualsiasi task implementativo |
| `siae-writing-plans` | **Rigid** | Decompone design approvato in task bite-sized |
| `siae-architecture` | Flexible | C4, HLD, bounded context, CQRS, microservizi vs monolite |

### Fase 3 — Branching & Release

| Skill | Tipo | Quando invocarla |
|---|---|---|
| `siae-git-workflow` | Rigid | Qualsiasi operazione git (checkout, commit, push, merge, tag) |
| `siae-git-env` | Rigid sub | Detect GitHub CLI availability (sub-skill di git-workflow) |
| `siae-branching-strategy-check` | Flexible | Verifica compliance branching strategy SIAE su PR/repo |
| `siae-finishing-branch` | Rigid | Pre-flight checklist prima di aprire una PR |
| `siae-blind-review` | Rigid | Review cieca spec-vs-codice (REQUIRED da finishing-branch) |
| `siae-release-risk` | Rigid | Pre-deploy assessment release branch vs main (scorecard 0-36) |

### Fase 4 — Implementation

| Skill | Tipo | Quando invocarla |
|---|---|---|
| `siae-subagent-development` | Rigid | Orchestra implementer + reviewer in stessa sessione |
| `siae-executing-plans` | Rigid | Esegue piano in sessione separata (batch + checkpoint umano) |
| `siae-code-standards` | Flexible | Standard codice Java/TS/Python/HCL |
| `siae-security` | Flexible | **SEMPRE** companion per codice/config/IAM/PII/ISWC/ISRC |
| `siae-iac` | Flexible | Terraform, Terragrunt, AWS IaC |
| `siae-data-engineering` | Flexible | AWS Glue, PySpark, ETL, Medallion |
| `siae-frontend` | Flexible | Vue/React/Angular, Vitest, S3+CloudFront, Firebase |
| `siae-flutter` | Flexible | Flutter, Riverpod, ObjectBox, Amplify |
| `siae-finops` | Flexible | Costi AWS/Azure, Infracost, tag compliance, idle resources |
| `siae-nr-test-flows` | Rigid | NRT suite per repo frontend/mobile |
| `siae-fix-evidence` | Rigid | Auto-fix loop per `BLOCK_REGRESSION` di review-evidence v2 |
| `siae-parallel-agents` | Flexible | Dispatch 2+ agent paralleli per task indipendenti |

### Fase 5 — Testing

| Skill | Tipo | Quando invocarla |
|---|---|---|
| `siae-tdd` | **Rigid** | **OBBLIGATORIO** per qualsiasi codice di produzione |
| `siae-qa` | Rigid | Test plan formale Xray (post brainstorming, post TDD) |
| `siae-automation` | Rigid | E2E Playwright/Cypress, CI/CD test pipeline |
| `siae-robot-framework` | Rigid | Test mobile Appium/BrowserStack, Robot Framework |
| `code-coverage` | Flexible | Generazione test deterministica multi-stack (≥70% coverage) |

### Fase 6 — QA Gate

| Skill | Tipo | Quando invocarla |
|---|---|---|
| `siae-debugging` | **Rigid** | Bug, errore, stacktrace, crash, "non funziona" |
| `siae-autoresearch` | Flexible | Ottimizzazione iterativa di una skill DevForge |

### Fase 7 — Release & Docs

| Skill | Tipo | Quando invocarla |
|---|---|---|
| `siae-documentation` | Flexible | Genera HLD, LLD, API doc (OpenAPI 3.x) |
| `siae-jasper-from-pdf` | Rigid | Reverse-engineering PDF → JRXML JasperReports |

### Cross-cutting

| Skill | Tipo | Quando invocarla |
|---|---|---|
| `siae-verification` | **Rigid** | **SEMPRE** prima di dichiarare completato |
| `siae-receiving-review` | Rigid | Ricezione feedback PR (CHANGES REQUESTED) |
| `siae-requesting-review` | Rigid | Richiesta review post-PR-aperta |
| `siae-retrospective` | Rigid | Fine sessione / apertura PR (REQUIRED da `post-commit-review`) |
| `siae-dev-analytics` | Rigid | Report ROI Claude Code + DevForge (11 KPI DORA + DX) |
| `using-devforge` | Discovery | Entry point catalog, invocata dal session-start hook |

### Meta

| Skill | Tipo | Quando invocarla |
|---|---|---|
| `siae-writing-skills` | Flexible | Creazione o miglioramento di una skill DevForge |

---

## Slash command (10)

I comandi sono **optimization** del catalog, non duplicati. Esistono solo quelli con
logica/argomenti propri o `allowed-tools` speciali. Per le skill senza comando dedicato,
basta la trigger sentence naturale (es. "scrivi test prima del codice" → `siae-tdd`).

| Comando | Skill / Function | Note |
|---|---|---|
| `/forge-implement` | `siae-subagent-development` | Orchestra implementer + reviewer in-session su piano `docs/plans/` |
| `/forge-execute` | `siae-executing-plans` | Esegue piano in sessione separata, batch + checkpoint umano |
| `/forge-evidence` | hook `review-evidence` | Pre-compute deterministic quality signals per il SHA corrente |
| `/forge-score` | hook `review-evidence` | Score card v2 (5 dimensioni + overall 0-100) markdown copy-paste |
| `/forge-fix-evidence` | `siae-fix-evidence` | Auto-fix loop per `BLOCK_REGRESSION` (max 5 iter, oscillation guard) |
| `/forge-release-risk` | `siae-release-risk` | Pre-deploy scorecard 18-criteri (decision GO/POSTPONE/NO_GO) |
| `/forge-mcp-preflight` | agent `mcp-impact-analyst` | Pre-flight MCP `sport-kg` (output strutturato, context-isolated) |
| `/forge-adoption` | `siae-dev-analytics` | Adoption personale 5 skill core vs media team |
| `/forge-analytics` | `siae-dev-analytics` | Report ROI Excel (11 KPI + DORA tier) |
| `/code-coverage` | `code-coverage` | Generazione test multi-stack ≥70% coverage |

---

## Agent (5)

Gli **agent** sono subagent context-isolated dispatchati via Task tool. Hanno scope
ristretto e tool whitelist; ritornano blocchi markdown standardizzati al chiamante.

| Agent | Scope | Output |
|---|---|---|
| `code-reviewer` | Review post-implementazione, framework 6-punti SIAE | Markdown structured con verdetto + issue list |
| `spec-reviewer` | Verifica conformità impl vs design doc | Verdetto PASS/FAIL + lista deviation |
| `doc-generator` | Generazione HLD/LLD/API doc da codice sorgente | Documento markdown + PlantUML diagrams |
| `mcp-impact-analyst` | Pre-flight MCP `sport-kg` (pipeline 5-step) | Blocco rischio + 3 vincoli + volumi |
| `qa-investigator` | Q&A su topology/auth/runtime SIAE | Claim CONFIRMED/PARTIAL/REFUTED + evidence_type |

---

## Hook (25)

Gli hook implementano l'**enforcement deterministico** del backbone. Sono organizzati
in 4 categorie:

### Context & Discovery

| Hook | Trigger | Scopo |
|---|---|---|
| `session-start` | startup / resume | Invoca `siae-onboarding`, mostra welcome + catalog |
| `session-start-tiered-advisor` | startup / resume | Suggerisce gerarchia CLAUDE.md se mancante o stale |
| `devforge-context` | UserPromptSubmit | Inject backbone reminder (budget hard-cap 2KB, dedup hash) |
| `skill-advisory` | PreToolUse Bash | Reminder catalog skill rilevanti per il tool corrente |
| `sport-task-detect` | UserPromptSubmit | Detect servizi sport-kg-mapped per pre-flight MCP |
| `setup-mcp-kibana` | startup | Setup MCP Kibana per ES queries |
| `setup-mcp-sport` | startup | Setup MCP sport-kg per topology queries |

### Backbone Gate (enforcement task-scoped)

| Hook | Trigger | Scopo |
|---|---|---|
| `brainstorming-gate` | PreToolUse Edit/Write | Blocca modifica codice senza design doc nel branch |
| `plan-gate` | PreToolUse Edit/Write | Blocca implementazione senza piano in `docs/plans/` |
| `plan-gate-write` | PreToolUse Write | Variante per file nuovi |
| `tdd-gate` | PreToolUse Edit/Write | Blocca codice production senza test (file taxonomy) |
| `sub-skill-gate` | PreToolUse | Enforce REQUIRED SUB-SKILL chain (prereq map autogenerata) |
| `stop-gate` | Stop | Blocca "fatto" senza evidence verification |
| `batch-checkpoint` | PostToolUse | Enforce checkpoint umano in `siae-executing-plans` (3 task) |

### Review & Quality

| Hook | Trigger | Scopo |
|---|---|---|
| `pre-commit` | PreToolUse Bash | Token parser per `git commit` (immune a substring match) |
| `post-commit-review` | PostToolUse Bash | Auto-dispatch `code-reviewer` + retrospective su PR open |
| `pr-gate` | PreToolUse Bash | Verifica plugin version sync + checks pre-PR |
| `pr-blind-review-gate` | PreToolUse Bash | Enforce blind-review prima di `gh pr create` |
| `pr-release-gate` | PreToolUse Bash | Enforce `siae-release-risk` su release branch → main |
| `review-evidence` | PostToolUse | Compute v2 score card + emit `BLOCK_REGRESSION` se < soglia |

### Telemetry & State

| Hook | Trigger | Scopo |
|---|---|---|
| `state-writer` | tutti | Persist skill activation + task_id in `~/.claude/.devforge-task-skills/` |
| `post-skill` | PostToolUse | Log skill_event in `~/.claude/devforge-activity.jsonl` |
| `capture-test-result` | PostToolUse Bash | Cattura output test (PASS/FAIL/coverage) per evidence |
| `batch-reset` | PostToolUse | Reset batch counter per `siae-executing-plans` |
| `devforge-flusher` | Stop | Flush telemetria su disk + S3 (zero-loss safe-drop) |

**Dispatcher**: `hooks/run-hook.cmd` è il single entry point che routa ai singoli hook. Config
in `hooks/hooks.json`. Helper bash condivisi in `hooks/lib/`.

---

## Architettura del plugin

```
siae-dev-forge/
├── .claude-plugin/              # plugin.json + marketplace.json (dual-source version)
├── agents/                      # 5 subagent context-isolated
├── commands/                    # 10 slash command (thin wrapper o logic-heavy)
├── design-system/               # devforge-visual.md (banner ASCII + template UI)
├── docs/
│   ├── plans/                   # docs/plans/<topic>/ piani implementativi
│   └── releases/                # Scorecard release-risk versionate
├── evals/                       # Eval set per autoresearch (skill optimization)
├── hooks/                       # 25 trigger script + dispatcher + lib/
│   └── lib/                     # cmd-parser.sh, file-taxonomy.sh, schemas/
├── infra/                       # Terraform/Terragrunt per DevForge stesso (S3 baseline, Glue)
├── lib/                         # Library Python shared (review_evidence/, autoresearch/, …)
├── reports/                     # Output report (analytics, release-risk, evidence)
├── rules/                       # Semgrep custom rules (PII, presigned URL, XSS supplement)
├── scripts/                     # CLI utility (emit-claude-md.py, anti-bloat-lint.py, …)
├── skills/                      # 43 skill (1 dir per skill, SKILL.md + reference/)
├── statusline/                  # Custom statusline Claude Code (skill count, commits)
├── tests/                       # pytest suite (test_*.py)
├── tools/                       # CLI tools (forge-score CLI, …)
├── CHANGELOG.md                 # Keep-a-Changelog format, single source of release notes
└── README.md                    # Questo file
```

### File chiave da conoscere

| Path | Funzione |
|---|---|
| `.claude-plugin/plugin.json` | Manifest plugin (versione, description, count assets) |
| `.claude-plugin/marketplace.json` | Manifest marketplace privato SIAE |
| `hooks/hooks.json` | Config dispatch hook (matcher → script) |
| `hooks/lib/file-taxonomy.sh` | Centralizza regex file extension per gate brainstorming/TDD |
| `hooks/lib/cmd-parser.sh` | Token parser bash immune a substring spoofing |
| `skills/using-devforge/SKILL.md` | Entry point discovery catalog (invocato da session-start) |
| `docs/plans/<topic>-design.md` | Design doc da `siae-brainstorming`, fonte di verità per scope task |

---

## Telemetria & enforcement evidence-based

DevForge **non si fida** delle dichiarazioni. Ogni skill backbone dichiara `validates_via` nel
frontmatter, e il completamento richiede **evidence concreta** (file output, log event, exit code).

### Evidence contract

```yaml
# skills/siae-tdd/SKILL.md frontmatter
validates_via:
  predicate: tdd_red_green_observed
  evidence_type: log_event
  evidence_check: "DEVFORGE_LOG_FILE contains tdd_red_green event for current task_id"
```

Predicati attivi:
- `tdd_red_green_observed` — sequenza RED→GREEN catturata da `capture-test-result`
- `design_doc_produced` — `docs/plans/<topic>-design.md` esiste e committed
- `conventional_commit_made` — commit message matcha `feat|fix|refactor|docs|chore:`
- `verification_run_passed` — `siae-verification` 5-step PASS in log
- `blind_review_completed` — `siae-blind-review` ha prodotto `blind_review_verdict` event

### Task-scoped enforcement

`skill_key = (task_id, skill_name)` invece di `(session_id, skill_name)`. Una sessione può coprire
N task; ogni task richiede la propria validazione. `task_id = sha256(branch | latest-design-doc |
design-mtime)[:12]`. Evidence copy-forward automatica quando il design doc viene revisionato sullo
stesso branch.

### Telemetry pipeline

Eventi skill scritti in `~/.claude/devforge-activity.jsonl` → flush periodico via `devforge-flusher`
→ S3 `itsiae-devforge-telemetry-prod/raw/` → Glue bronze/silver/gold → dashboard CloudWatch +
Athena queries. Principio **zero-loss safe-drop**: cap/quota drop solo su dati già persistiti (cursor
== size), mai blind oldest (feedback `feedback_zero_loss_safe_drop`).

---

## Integrazione MCP

DevForge integra 3 server MCP per query strutturate context-isolated:

| MCP | Tool prefix | Use case |
|---|---|---|
| `sport-kg` | `mcp__sport-kg__*` | Knowledge Graph SIAE: topology microservizi, auth chain, impact analysis |
| `elasticsearch` | `mcp__elasticsearch__*` | Query ES per log SIAE, runtime traffic, error stacktrace |
| `atlassian` | `mcp__atlassian__*` | Confluence publish (HLD/LLD/API doc), Jira ticket lookup |

**Pre-flight MCP**: per task su servizi mappati nel KG (`sport-*-service`, `pop-*-service`,
`pae-*`, `ciam-*`, `dol-be`, `digital-channels-sport-*`, `esb-sport-*`, `mag-concertini-*`,
`portal-apigateway-*`, `ttpp-*-bff-service`), il workflow brainstorming richiede `/forge-mcp-preflight`
per ottenere rischio + 3 vincoli + volumi prima di proporre opzioni.

---

## Versioning & changelog

DevForge segue **SemVer** strict. Versione single-source in `.claude-plugin/plugin.json` mirrored
in `.claude-plugin/marketplace.json` (PR Gate hook usa plugin.json come source-of-truth).

**Major (`X.0.0`)**: breaking change al backbone (es. nuovo gate obbligatorio, rimozione skill
backbone).

**Minor (`x.Y.0`)**: nuova skill, nuovo comando, nuovo agent, nuovo hook, nuova feature
significativa.

**Patch (`x.y.Z`)**: bug fix, allineamento doc, rimozione thin-wrapper, cleanup
contraddizioni catalog.

Tutte le modifiche sono tracciate in [CHANGELOG.md](./CHANGELOG.md) (Keep-a-Changelog format).

### Release recenti

| Versione | Data | Highlights |
|---|---|---|
| `1.63.7` | 2026-05-21 | **Bootstrap esteso a TUTTI i 16 runner**: di default DevForge auto-installa l'intero stack OSS (semgrep, gitleaks, eslint, ts-unused-exports, spotbugs, bandit, pip-audit, vulture, pyright, swiftlint, detekt, ktlint, tflint, tfsec, checkov, cfn-lint). Cooldown 1h, parallel 4. Cold-start su prima session, poi cache. |
| `1.63.6` | 2026-05-21 | **Runner auto-bootstrap automatico**: `scripts/runner-bootstrap.sh` invocato automaticamente da `hooks/review-evidence` in background (cooldown 1h). Auto-install dei 6 runner security primari, warning rossi non-blocking se fail. Niente più setup manuale per nuovi dev SIAE. |
| `1.63.5` | 2026-05-21 | **Runner lazy auto-install non-blocking**: `--ensure <tool>` con timeout, warning rosso ANSI su stderr se install fail, exit 0 (no block). 12/17 runner OSS installati locale (semgrep, gitleaks, bandit, ecc.). |
| `1.63.4` | 2026-05-20 | **Bypass evidence subprocess-safe (BUG A)**: marker file session-scoped `~/.claude/devforge-state/<sid>/.bypass-evidence` (env var non propagata a subprocess hook); cleanup auto a session-end |
| `1.63.3` | 2026-05-20 | **Telemetry bugs (3 critici)**: sid `no-session` fallback (44k eventi orfani), `LAST_HASH_FILE` per-repo (era globale → 103× inflazione commit_created), hardening evidence bypass (state file rimosso, solo env var session-scoped) |
| `1.63.2` | 2026-05-20 | 3 test deterministici anti-allucinazione (19 PASS): count consistency, validates_via well-formed, phantom slash commands |
| `1.63.1` | 2026-05-20 | Reconcile bot-bump 1.63.0 (count stale): description verified empirically (43/10/5/25), self-audit fix 3 MAJOR |
| `1.63.0` | 2026-05-20 | Bot auto-bump (PR #262) |
| `1.62.4` | 2026-05-20 | Anti-dilution backbone: `validates_via` 5/9→9/9, rimosse 5 ADR fantasma dal README, README rewrite -64% |
| `1.62.3` | 2026-05-20 | Allineamento catalog: rimossi 14 `/forge-X` fantasma da SKILL.md |
| `1.62.2` | 2026-05-20 | Rimossi 8 thin-wrapper command (forge-automate/cost/doc/finops/flows/jasper/test + forge-mcp-snapshot) |
| `1.62.1` | 2026-05-20 | Aggiunto `/forge-execute` per `siae-executing-plans` (pendant di `/forge-implement`) |
| `1.62.0` | 2026-05-19 | Tiered CLAUDE.md generation (L1+L2+L3 on-demand) + anti-bloat lint |
| `1.58.0` | 2026-05-16 | `siae-release-risk` skill end-to-end (CLI + hook + 18-criteri scorecard) |
| `1.57.0` | 2026-05-14 | `siae-release-risk` v1 + MCP bridge |
| `1.43.0` | precedenti | `siae-dev-analytics` skill (ROI Claude Code, 11 KPI DORA + DX) |

---

## Contributing

### Aggiungere una skill

1. Crea `skills/<nome>/SKILL.md` con frontmatter YAML (`name`, `description`, `validates_via` se backbone)
2. Includi il banner ASCII DevForge (vedi `design-system/devforge-visual.md`)
3. Per skill Rigid: aggiungi **Legge di Ferro**, **Tabella Anti-Razionalizzazione**, **HARD-GATE**
4. Aggiungi **Classificazione Rischio Operazioni** con colonna Card (Si/No)
5. Per operazioni Card=Si: includi blocco `generate-card.py` nello step corrispondente
6. Aggiungi la skill al catalog in `skills/using-devforge/SKILL.md`
7. **Solo se serve** (logica/argomenti propri, non thin wrapper): crea command in `commands/`
8. Test: `pytest tests/test_skill_<nome>.py`

### Aggiungere un hook

1. Crea script eseguibile in `hooks/<nome>` (sh/bash/python)
2. Registra dispatch in `hooks/hooks.json` con matcher esplicito
3. **Invariant**: pipefail guard + stdout>/dev/null se emette JSON (`feedback_session_start_hook_invariants`)
4. Exit 0 sempre per advisor non-blocking, exit 2 + stderr per gate bloccanti
5. Test: `pytest tests/test_hook_<nome>.py`

### Aggiungere un agent

1. Crea `agents/<nome>.md` con frontmatter (`name`, `description`, `model: inherit`)
2. Definisci framework di analisi + output atteso (preferibilmente markdown structured grep-abile)
3. Aggiungi distrust pattern se l'agent verifica lavoro altrui

### Convenzioni commit

```
feat: nuova skill, comando, agent, hook
fix: correzione bug
refactor: ristrutturazione senza cambio comportamento
docs: aggiornamento doc/template
chore: manutenzione, bump dipendenze, allineamento catalog
test: aggiunta/modifica test
```

### Plugin version dual-source

Memoria critica (`project_plugin_version_dual_source`): ogni bump deve aggiornare
**entrambi** `.claude-plugin/plugin.json` E `.claude-plugin/marketplace.json`. PR Gate hook
controlla la sync e blocca la PR se le due version divergono.

---

## Licenza

Proprietary. © SIAE AI Competence Center. Distribuzione interna SIAE.

Per domande: `ai-cc@siae.it` · per bug e feature request: aprire issue su `github.com/itsiae/siae-dev-forge`.

---

**Il codice si forgia. Il developer cresce.**
