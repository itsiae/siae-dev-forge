# Changelog

Tutte le modifiche notabili a questo progetto sono documentate in questo file.

Il formato e' basato su [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.62.4] - 2026-05-20

### Added/Fixed — Anti-dilution gap closure

Audit anti-dilution su 9 backbone skill ha rilevato **4 gap di evidence contract** e **5 menzioni ADR fantasma** nel README. Il backbone enforcement è efficace solo se ogni skill backbone dichiara `validates_via` nel frontmatter — altrimenti i gate hook non possono verificare il completamento e l'utente può claimare "fatto" senza evidence concreta.

**1. validates_via aggiunto a 4 backbone skill (closure gap):**

| Skill | predicate | evidence_type | check |
|---|---|---|---|
| `siae-writing-plans` | `plan_produced` | `file_exists` | `docs/plans/<topic>/overview.md` con task-NN files + marker `[PENDING]`/`[DONE]` |
| `siae-debugging` | `root_cause_identified` | `log_event` | `debugging_root_cause` event con `hypothesis_validated=true` |
| `siae-security` | `security_review_run` | `log_event` | `security_check` event per current task_id |
| `siae-finishing-branch` | `pre_flight_passed` | `log_event` | `finishing_branch_verdict` event con `verdict=PASS` |

Coverage backbone evidence contract: 5/9 (56%) → **9/9 (100%)**.

**2. README ADR fantasma rimossi (5 occorrenze):**

Il README v1.62.3 citava `docs/adr/ADR-001…ADR-009`, `### Evidence contract (ADR-002)`, `### Task-scoped enforcement (ADR-001)`, `ADR-2 MCP bridge`. La directory `docs/adr/` non esiste e nessun ADR è mai stato creato. Promesse non mantenute = dilute trust nel catalog. Rimosse:
- Riferimento alla directory `docs/adr/` nel file tree
- `ADR-001`/`ADR-002` dalle section headers Evidence contract / Task-scoped enforcement
- `ADR-2` dalla tabella release recenti (v1.57.0)

**Rationale**: il principio anti-dilution è che ogni promessa del catalog deve essere verificabile. Documentazione che cita strutture inesistenti è anti-dilution debt che si accumula nel tempo.

**Follow-up identificati (NON in questa release):**
- **8 escape hatches attivi** (`DEVFORGE_SKIP_*` × 6 + `DEVFORGE_FORCE_*` × 2): proporre consolidamento in singolo `DEVFORGE_SKIP=<feature>` con allowlist temporanea (3 usi/giorno tracked).
- **10+ piani vecchi orfani** in `docs/plans/` con marker `[PENDING]` ≥60 giorni (best-practices-alignment 12/12 PENDING, session-aware-enforcement, superpowers-improvements): archiviare in `docs/plans/archived/` con marker `[ABANDONED]`.
- **57 file dup iCloud untracked** (`X 2.py`, `X 3.sh`): aggiungere pattern `* [0-9].*` a `.gitignore`.

## [1.62.3] - 2026-05-20

### Removed/Fixed — Contraddizioni catalog (allineamento)

Audit sistematico del catalog DevForge ha rilevato 16 contraddizioni interne fra ciò che le SKILL.md prometteono e ciò che esiste:

**1. 14 `/forge-X` fantasma rimossi dalle SKILL.md description.** Citati come trigger ma il file `commands/` non esisteva (mai creato oppure eliminato in 1.62.2). Le skill restano invocabili tramite trigger sentence naturali (presenti nel description).

| Fantasma rimosso | Skill | Sostituzione |
|---|---|---|
| `/forge-automate` | siae-automation | "automatizza test", "setup Playwright/Cypress" |
| `/forge-autoresearch` | siae-autoresearch | "ottimizza skill", "analizza performance skill" |
| `/forge-blind-review` | siae-blind-review | "blind review", "audit spec-vs-codice" |
| `/forge-cost` | siae-finops | "stima costi PR", "Infracost" |
| `/forge-doc` | siae-documentation | "richiesta documentazione" |
| `/forge-finops` | siae-finops | "review costi AWS" |
| `/forge-flows` | siae-nr-test-flows | "NRT suite", "mappa flussi" |
| `/forge-jasper` | siae-jasper-from-pdf | "jrxml da pdf" |
| `/forge-logic-build` | siae-service-logic-map | "build catalogo L1/L2/L3" |
| `/forge-logic-search` | siae-service-logic-map | "cerca workflow di X" |
| `/forge-map` | siae-codebase-map | "mappa codebase" |
| `/forge-qa` | siae-qa | "genera test plan Xray" |
| `/forge-retro` | siae-retrospective | "retrospettiva", "lezioni apprese" |
| `/forge-sysmap` | siae-microservices-map | "mappa sistema", "topologia distribuita" |

Mantenuto solo `/forge-spec-review` come **anti-esempio intenzionale** in `siae-subagent-development` Permission Denied ("NON inventare slash command", documentazione difensiva).

**2. Count hook drift fixed.** `plugin.json` / `marketplace.json` dichiaravano "25 hook" ma quelli reali sono **30**. Aggiornato.

**Rationale**: zero false promesse, catalog onesto. Un utente che digita un comando inesistente prima vedeva "command not found"; ora trova solo trigger sentence naturali che il modello sa interpretare.

**Trade-off accettato**: ridotta discoverability slash per i 14 comandi mai esistiti. Le skill restano scoperte via descrizione + skill catalog injection.

## [1.62.2] - 2026-05-20

### Removed — Slash command thin-wrapper

Elimina 8 slash command che erano "thin wrapper" di una singola skill (testo unico: "Invoca la skill X e seguila esattamente") senza logica propria, allowed-tools speciali, argomenti, o multi-step. Le skill restano pienamente invocabili via **trigger sentence** (frase naturale: es. "scrivi test prima del codice" → `siae-tdd`).

**Eliminati (8):**
| Slash command rimosso | Skill backing | Come invocare ora |
|---|---|---|
| `/forge-automate` | `siae-automation` | "automatizza test", "setup Playwright", "setup Cypress" |
| `/forge-cost` | `siae-finops` | "stima costi PR", "Infracost", "shift-left FinOps" |
| `/forge-doc` | `siae-documentation` | "genera HLD", "genera LLD", "documentazione tecnica" |
| `/forge-finops` | `siae-finops` | "review costi AWS", "ottimizzazione risorse", "tag compliance" |
| `/forge-flows` | `siae-nr-test-flows` | "NRT suite", "flow map test", "test list per sezione" |
| `/forge-jasper` | `siae-jasper-from-pdf` | "jrxml da pdf", "ricostruisci jasper" |
| `/forge-test` | `siae-tdd` | "TDD per feature", "Red-Green-Refactor", "scrivo test prima" |
| `/forge-mcp-snapshot` | (utility, no skill) | invocare manualmente lo script (raramente usato, 0 ext-refs) |

**Mantenuti (10):** comandi con logica/argomenti propri o allowed-tools speciali — `code-coverage`, `forge-adoption`, `forge-analytics`, `forge-evidence`, `forge-execute`, `forge-fix-evidence`, `forge-implement`, `forge-mcp-preflight`, `forge-release-risk`, `forge-score`.

**Rationale:** la skill catalog è la fonte primaria di discovery; gli slash command devono essere un'optimization, non un duplicato. Il count 18→10 riduce friction discovery, allinea con principio anti-bloat e con la regola "comando esiste = ha logica oltre a invocare la skill".

**Trade-off accettato:** ridotta discoverability per gli 8 comandi rimossi. Le menzioni `/forge-<nome>` residue nelle SKILL.md description restano come trigger sentence colloquiale (il modello le interpreta in chat), ma l'autocompletion slash sparisce.

## [1.62.1] - 2026-05-20

### Fixed — Execution handoff slash command mancante

Quando `siae-writing-plans` completava il piano e proponeva l'Opzione 2 ("sessione separata"), il modello inventava per simmetria con `/forge-implement` uno slash command `/forge-execute` che non esisteva — l'utente apriva la nuova sessione, digitava il comando suggerito e otteneva "command not found". Cause: (a) `/forge-execute` mai registrato in `commands/`, (b) `writing-plans-execution-handoff.md` istruiva un handoff in prosa libera ("Carica il piano con: cat docs/plans/...") senza ancorare il modello a uno slash command esistente, (c) `siae-subagent-development` permission-denied path emetteva istruzioni "Apri una nuova sessione ... e incolla questo prompt" senza nominare un comando concreto.

**Aggiunte:**
- Nuovo slash command `/forge-execute` → invoca `siae-executing-plans` (pendant di `/forge-implement` per la sessione separata)

**Modifiche:**
- `skills/siae-writing-plans/reference/writing-plans-execution-handoff.md` — Opzione 2 emette ora un blocco prompt esatto con `/forge-execute docs/plans/<topic>/overview.md`, con anti-pattern documentato ("NON dire 'incolla il prompt qui sopra fino a Procedi'")
- `skills/siae-subagent-development/SKILL.md` Permission Denied — vieta esplicitamente l'invenzione di slash command, distingue Implementer (`/forge-execute`) da reviewer (trigger sentence + blocco prompt copy-paste)

**Memoria correlata:** `feedback_verify_code_before_documenting` (grep nomi prima di referenziarli)

## [1.62.0] - 2026-05-19

### Added — Tiered CLAUDE.md generation

Implementa best practice Anthropic post [How Claude Code works in large codebases](https://claude.com/blog/how-claude-code-works-in-large-codebases-best-practices-and-where-to-start) (14 mag 2026): generazione automatica gerarchia `CLAUDE.md` (L1 root + L2 package + L3 child on-demand) con import `@` chain e anti-bloat.

**Nuova sub-skill `siae-codebase-map-tiered`**
- Invocata da `siae-codebase-map` Step 7a quando flag `--tiered` presente
- Genera L1 root (`./CLAUDE.md`, <200 righe big picture)
- Genera L2 per ogni Maven module / TS package (`./<module>/CLAUDE.md` con import `@../CLAUDE.md`)
- Genera L3 child on-demand solo se subdir >=10 file AND pattern locale distintivo (anti-bloat)

**Nuovo hook `session-start-tiered-advisor`**
- Async, non-bloccante (exit 0 sempre — memory `feedback_session_start_hook_invariants`)
- Matcher `startup|resume` (escluso `clear|compact`)
- Rileva CLAUDE.md mancante → suggerimento via `additionalContext`
- Rileva stale (>=30 commit OR >14 giorni dal `last_mapped`) → suggerimento update
- Timeout 3s hard cap, errori silent

**Script Python (stdlib only, Python 3.9+):**
- `scripts/emit-claude-md.py`: frammenta `docs/CODEBASE_MAP.md` → CLAUDE.md gerarchici (90% coverage, 6/6 test PASS)
- `scripts/anti-bloat-lint.py`: lint advisory exit-0 (line_count, parent_overlap, placeholder, missing_import, empty_sections — 94% coverage, 18/18 test PASS)

**Modifiche `siae-codebase-map`**
- Step 7 split: 7a (tiered mode opt-in) + 7b (mono-file default, comportamento invariato)
- Zero-regression: `/forge-map` senza `--tiered` produce CODEBASE_MAP.md identico a prima

**Test:**
- 32 nuovi test (6 emit + 18 anti-bloat + 8 hook tiered-advisor) — TUTTI PASS
- Test no-regression hook count bumped 25 → 26

**Design e piano:**
- Design doc: `docs/plans/2026-05-19-tiered-claude-md-design.md`
- Piano implementativo: `docs/plans/2026-05-19-tiered-claude-md/` (overview + 8 task)

**Note operative:**
- Per attivare: `/forge-map --tiered` su repo Maven multi-module o monorepo TS
- L'hook advisory è async, non blocca boot
- Anti-bloat lint mostra warning su stdout, exit code 0

## [1.60.0] - 2026-05-19

### Added — Security Hook Vulnerability Prevention Library (Wave 1)

Estensione DevForge per intercettare automaticamente codice con vulnerability pattern OWASP/JWT/XSS + 5 SIAE-specific famiglie dal pentest 2026-05-18 broadcasting.

**5 Semgrep custom rules SIAE attive in `rules/semgrep/siae/`:**
- F1 `siae.formula-injection.ts.csv-row-join-naive` + sibling `csv-rows-join-newline-naive` (CWE-1236 + CWE-93)
- F2 `siae.authz-tenant.ts.dao-missing-tenant-filter` (CWE-639 IDOR)
- F4 `siae.soft-delete.sql.view-only-state-filter` (CWE-639 soft-delete bypass)
- F6 `siae.authz-tenant.ts.query-param-tenant-override` (CWE-639)
- F26 `siae.jwt.ts.jwt-in-localstorage` (CWE-1004 + CWE-79)

**Architettura layered (5 layer):**
- L1 community Semgrep `auto` ruleset (preserved)
- L2 SIAE custom YAML rules con DIR auto-discovery
- L3 structured suppression engine + PR-gate schema validation (ADR-009)
- L4 balanced severity (ADR-005) — ERROR+HIGH = critical (block); WARNING = high bucket (visible, no block default)
- L5 performance: `--diff-aware` env-driven, `--jobs` parallel, `--timeout=10` per-file (ReDoS protection)

**Componenti aggiunti:**
- `lib/review_evidence/suppression.py` + `suppression_validator.py` (parse + apply + ADR-009 schema validation hard)
- `lib/review_evidence/drools_check.py` (ADR-007 Form A label + Form B header)
- `lib/review_evidence/tools/fp_rate.py` (ADR-005a FP measurement, thresholds 5%/10%)
- `rules/semgrep/siae/` con MANIFEST.md + README.md + suppressions.yaml + version.lock
- 14 fixture sintetiche in `tests/fixtures/semgrep_siae/synthetic/` (ADR-004 no broadcasting reale)

**Componenti modificati:**
- `lib/review_evidence/runners/semgrep.py` — version check ≥1.50, layered config DIR, by_family parsing, EVIDENCE_TOOL_MISSING distinct exit
- `lib/review_evidence/scoring.py` — `SecurityFindings.tool_unavailable` factory + `by_family` field
- `hooks/pr-gate` — suppressions schema validation + Drools `.drl` review check
- `skills/siae-security/SKILL.md` — Rule Reference section con 5 rule documentate

**Test coverage:** 56/56 PASS (19 regression + 17 SIAE MVP + 8 perf + 14 suppression + 10 FP/Drools).

**Riferimenti:**
- Design v2.1: `docs/plans/2026-05-18-security-hook-vulnerability-prevention-design.md` (9 ADR, 23 AC, 46 edge-case CRITICAL chiusi)
- Pentest: `pentest-broadcasting/PENTEST_REPORT.md` (2026-05-18 itsiae/broadcasting-*)
- North Star: zero-bug-jul-2026
- PR: [#255](https://github.com/itsiae/siae-dev-forge/pull/255)

**Breaking changes:** nessuno. Backward-compatible via env `DEVFORGE_SEMGREP_CONFIG`.

## [1.57.0] - 2026-05-14

### Added — Release Risk Assessment
- **siae-release-risk** skill: pre-deploy risk assessment per release branch (18 criteri, score 0-36, level LOW/MEDIUM/HIGH/CRITICAL, decision GO/POSTPONE/NO_GO)
- **/forge-release-risk** slash command on-demand
- **hooks/pr-release-gate** PostToolUse Bash hook automatic su `gh pr create --base main` con head `release/**` (advisory-only)
- 3 controlli aggiuntivi vs skill esterna originale:
  - Criterion 16: Functional regression delta vs precedente release (coverage + test disabled/deleted)
  - Criterion 17: Security vulnerability state (MVP HEAD-only via pip-audit + npm-audit)
  - Criterion 18: Unexpected feature in release (genesis confirmation Step 4b)
- Integrazione MCP sport-kg per critical service detection (Criterion 5) via JSON prefetch bridge
- Cache `(branch, diff-hash, baseline-main-sha)` per skip re-run idempotenti
- Output versionato `docs/releases/<date>-<service>-<branch>.md` + PR comment auto con idempotency marker
- Activity ledger event `release-risk` via `devforge_log`

### Changed
- Plugin manifest: bump 1.56.0 → 1.57.0
- Plugin description: count audit accurato (42 skill, 17 comandi, 5 agent, 24 hook)

### Reference
- Design doc: `docs/plans/2026-05-14-siae-release-risk-design.md` (13 ADR)
- Plan: `docs/plans/2026-05-14-siae-release-risk/` (42 task bite-sized)

### Out of scope (backlog futuro)
- CVE per-ID identification (v3.x)
- Criterion 17 delta vs baseline (v2.x — richiede extension EvidenceV2 schema)
- Maven security runner (estensione runners/)
- 4 controlli aggiuntivi: data migration delta, perf regression, contract breaking, OCP drift
- Auto-calibrazione weight via incident correlation
- CAB ticket auto-creation
- Dashboard release-risk in siae-dev-analytics
- Tag-creation hook + auto-block evolution

## [Unreleased] — v1.55.0 (review-evidence v2 scoring)

### Added

- **Schema v2** (`lib/review_evidence/schema.py`): `ScoreCard`, `RegressionVerdict`
  (5 decision branch: AUTO_APPROVE / REVIEWER_HANDOFF / BLOCK_HARD_FLOOR /
  BLOCK_REGRESSION / SEVERELY_DEGRADED), `ReviewerVerdict`, `EvidenceV2` extension
  additive con forward-compat v1.
- **Score algorithm** (`lib/review_evidence/scoring.py`): 5 score functions
  (security/quality/coverage/spec/discipline) + `compute_overall` con D6
  severely_degraded handling. Coverage anti-gaming via `lines_covered` drop
  penalty (CRITICAL B1+B7+C5).
- **5 OSS runner MVP** (`lib/review_evidence/runners/`): bandit, gitleaks,
  pip-audit, npm-audit, eslint-security. Zero costo licenza, no Qodana
  commercial dependency.
- **`arch_drift` check** (`lib/review_evidence/checks/arch_drift.py`): detect
  violazioni `forbidden_paths` configurate in `.devforge-arch.yml`.
- **Config parsers** (`lib/review_evidence/config.py`): `.devforge-scores.yml`
  (weights + hard_floors + regression_budget) + `.devforge-arch.yml`. Weights
  validation sum ~= 1.0 (E4 fix). Config change detection in PR (CRITICAL B3 fix).
- **Hook bash v2 extension** (`hooks/review-evidence`): 5 decision branch case
  per gestire `regression_verdict.decision`. v1 fallback preservato.

### Changed

- `lib/review_evidence/collector.py`: extension `orchestrate_v2()` per scoring
  layer. v1 `orchestrate()` stays for back-compat.

### Added (PR-B advanced)

- **Baseline cache S3** (`lib/review_evidence/baseline_cache.py`): S3 backend
  via boto3 + local fallback (`~/.claude/review-evidence-baseline-local`).
  Cache key = main HEAD SHA, **NO TTL** (A1 CRITICAL fix). Force-push
  invalidation via `git cat-file -e` (A2 fix). OIDC IAM trust provisioned per
  `itsiae/*` repos (Task 16 Terraform).
- **`skill_adoption` check** (`lib/review_evidence/checks/skill_adoption.py`):
  4-tier fallback signal (activity.jsonl -> design doc -> git log -> neutral)
  per discipline score. Bot PR detection (Dependabot, Renovate) -> discipline
  skip (no false negatives su auto-bumps).
- **Regression analyzer** (`lib/review_evidence/regression.py`): budget
  snapshot at PR_OPEN_TIME (E1 CRITICAL fix — admin change budget post-PR non
  sposta snapshot), 5 decision branch enforcement, hard floor **NON-overridable**
  da reviewer agent (F1+E5 CRITICAL fix).
- **Reviewer agent Step 0.6** (`agents/code-reviewer.md`): 5 decision branch
  gatekeeper logic. AUTO_APPROVE emette comunque review summary advisory
  (W2 fix). BLOCK_HARD_FLOOR ignora reviewer APPROVED (solo admin BREAK-GLASS).
- **Skill `/forge-score`** (`commands/forge-score.md`): on-demand score card
  markdown 5-dim copy-paste pronto per `gh pr comment`. Advisory only.
- **40 edge case** (8 CRITICAL + 17 HIGH + 9 LOW) mitigati con chaos test
  suite v2 (15+ test failure-injection): cache S3 unreachable, force-push
  baseline, budget tampering, severely_degraded fallback, hard floor F1+E5.
- **Terraform module** (`infra/terraform/review-evidence-baseline/`):
  S3 bucket `itsiae-review-evidence-baseline-prod` (eu-west-1, versioning
  on, encryption SSE-S3) + IAM role OIDC trust per `repo:itsiae/*`.
- **E2E test full pipeline** (`tests/test_review_evidence_e2e.py` v2 extension):
  hook bash -> collector -> S3 baseline -> reviewer agent contract.

### Added (siae-fix-evidence skill)

- **Skill `siae-fix-evidence`** (`skills/siae-fix-evidence/SKILL.md`): auto-fix
  loop hook-driven per `BLOCK_REGRESSION` review-evidence v2. Skill composer
  che legge `block_reasons` atomici e dispatcha `siae-tdd` o
  `siae-code-standards` via Skill tool (ADR-7 dynamic prompt) fino ad
  `AUTO_APPROVE` o escalation. Max 5 iter, token budget 200k, oscillation
  guard (stesso `frozenset(block_reasons)` 2 iter consecutivi -> escalate).
- **Fix parser** (`lib/review_evidence/fix_parser.py`): `parse_block_reasons`
  riusa `evidence_from_json` (forward-compat 1.x/2.x). MVP 2 atomic patterns:
  `coverage_below_threshold:X<Y` -> `siae-tdd` (priority 2), `lint_errors:N>M`
  -> `siae-code-standards` (priority 1, applied first per minimizzare blast
  radius). Unknown reasons -> `FixAction(kind="unknown", sub_skill=None)`
  per escalation safety vs crash. 3 pattern follow-up MVP (complexity, drift,
  ci_critical) marcati TODO in-code.
- **Test unit** (`tests/test_fix_parser.py`): 5 test (coverage match, lint
  match, both sorted by priority, unknown reason, empty reasons). E2E loop
  test deferred a follow-up PR-D.
- **Command `/forge-fix-evidence`** (`commands/forge-fix-evidence.md`):
  espone la skill con `allowed-tools: Read, Bash, Skill`. Pre-flight check
  documentato (working tree pulito + evidence presente + decision ==
  BLOCK_REGRESSION + hard_floor_breaches vuoto).
- **Env vars** (`hooks/ENV_VARS.md`): `DEVFORGE_FIX_EVIDENCE_TOKEN_BUDGET`
  (default 200000), `DEVFORGE_FIX_EVIDENCE_MAX_ITER` (default 5).

### Added (auto-trigger fully-autonomous, follow-up PR #244)

- **Auto-trigger pattern fully-autonomous** (`hooks/review-evidence` +
  `skills/siae-fix-evidence/SKILL.md`): chiude il loop "zero bug usando
  DevForge" senza azione utente manuale. Quando `DEVFORGE_FIX_EVIDENCE_AUTO=1`
  e il hook emette `BLOCK_REGRESSION` (no hard floor, no bot, not degraded),
  il campo `additional_context` include signal canonico grep-friendly
  `AUTO_FIX_TRIGGER:/forge-fix-evidence:sha=<SHA>`. L'agent (Claude Code)
  intercept signal PRIMA di propagare il block all'utente, auto-invoca
  `siae-fix-evidence` skill, e ri-prova action originale su `AUTO_APPROVE`.
- **Env var** `DEVFORGE_FIX_EVIDENCE_AUTO` (default `0`, opt-in): attiva il
  pattern auto-trigger. `0` = no behaviour change vs MVP manuale
  `/forge-fix-evidence`.
- **Signal additivo** (NOT replace block): `decision:block` resta per safety,
  signal in `additional_context` per intercept agent. Hook resta single-file
  (B3 PR #243 fix preserved).
- **Skip conditions hook-level** identiche alla skill: `hard_floor_breaches`
  non vuoto, `GITHUB_ACTOR` matches bot pattern (`dependabot[bot]`,
  `renovate[bot]`, `github-actions[bot]`), decision SEVERELY_DEGRADED /
  BLOCK_HARD_FLOOR (case branch separati). Telemetry log
  `evidence_auto_fix_trigger_emitted` / `_skipped`.
- **Test** (`tests/test_review_evidence_auto_trigger.py`): verifica signal
  emitted on AUTO=1 + clean BLOCK_REGRESSION, no signal on AUTO=0,
  no signal su hard_floor_breaches non vuoto / bot actor.

### BREAKING (default behavior change, follow-up `feat/fix-evidence-auto-trigger`)

- **`DEVFORGE_FIX_EVIDENCE_AUTO` default flipped `0` -> `1`.** L'auto-trigger
  fully-autonomous e' ora il comportamento **default** invece di opt-in.
  Motivazione: DevForge default opinionato verso "zero bug usando DevForge"
  — ogni `BLOCK_REGRESSION` clean (no hard floor, no bot, not degraded)
  tenta un auto-fix loop prima di propagare il block all'utente.
- **Opt-out kill-switch:** `export DEVFORGE_FIX_EVIDENCE_AUTO=0` disabilita
  globalmente l'auto-trigger (comportamento pre-flip). Skip conditions
  semantic (hard floor / bot PR / SEVERELY_DEGRADED) restano invariate come
  safety net e non emettono mai il marker, indipendentemente dal valore env.
- **Test updates** (`tests/test_review_evidence_auto_trigger.py`): il caso
  `test_block_regression_without_auto_emits_no_signal` (AUTO=0 esplicito)
  resta verde — opt-out funziona. Il caso
  `test_block_regression_auto_unset_emits_no_signal` rinominato e invertito
  (`test_block_regression_auto_unset_emits_signal_by_default`) — default
  ON, signal ora emesso quando env unset.
- **Hook bash** (`hooks/review-evidence`): `${DEVFORGE_FIX_EVIDENCE_AUTO:-0}`
  -> `${DEVFORGE_FIX_EVIDENCE_AUTO:-1}`. Tutto il resto invariato
  (skip conditions, telemetry log `evidence_auto_fix_trigger_emitted` /
  `_skipped`, single-file architecture B3).

### Configuration

- `.devforge-scores.yml` template: `docs/templates/.devforge-scores.yml`
- `.devforge-arch.yml` template (esistente)
- JSON Schema draft-07: `docs/schemas/devforge-scores.schema.json`

### Docs

- `hooks/ENV_VARS.md`: sezione "Review Evidence v2 — Scoring (v1.55+)" estesa
  con PR-B vars (`DEVFORGE_BASELINE_S3_*`, `DEVFORGE_BREAK_GLASS_REGEX`,
  `DEVFORGE_ACTIVITY_PROJECT`).
- `README.md`: sezione "Review Evidence v2 — Scoring (v1.55+)" con 5 decision
  branch, tool stack OSS, baseline cache S3, hard floor non-overridable,
  config + skill `/forge-score`.

## [Unreleased] — 2026-05-12

### Added

- **Review Evidence Hook (`hooks/review-evidence`)** — pre-calcola in modo
  deterministico coverage, lint, complessita' ciclomatica, CI quality
  reports SARIF e spec-drift per ogni SHA. Scrive evidence cacheable in
  `.claude/review-evidence/<sha>.json`. Consumato come renderer da
  `code-reviewer` e `spec-reviewer` (nuovo Step 0.5 evidence-loading) per
  verdetti riproducibili allineati a CI.
- **Multi-stack collector framework** (`lib/review_evidence/`): Java
  (jacoco + checkstyle + pmd), TypeScript (lcov + eslint +
  complexity-report), Python (coverage.py + ruff + radon), HCL (tflint +
  terraform validate).
- **CI-fetch SARIF parser** tool-agnostic (Qodana, SonarQube, CodeQL —
  qualsiasi tool che emetta SARIF 2.1.0).
- **Spec-drift detector** con code-fence robustness (estrae path solo da
  sezioni allowlist del design doc, ignora code-fence / inline code /
  blockquote).
- **Hard-block soglie** configurabili via env var (`DEVFORGE_EVIDENCE_*`)
  + bypass primario via state file `~/.claude/.devforge-skip-evidence`.
- Skill `/forge-evidence` (`commands/forge-evidence.md`) per invocazione
  on-demand.

### Changed

- `agents/code-reviewer.md`, `agents/spec-reviewer.md`: aggiunto Step 0.5
  evidence-loading prima del 6-punti / spec analysis.
- `hooks/hooks.json`: `review-evidence` registrato in PreToolUse Bash (su
  `gh pr create|edit`) e PostToolUse Bash (async cache warm su commit).

### Docs

- `hooks/ENV_VARS.md`: documentate 9 nuove env var `DEVFORGE_EVIDENCE_*`.
- `.gitignore`: aggiunto `.claude/review-evidence/`.
- `README.md`: nuova sezione "Review Evidence Hook".

## [Previous] — 2026-05-03

### Changed
- `siae-tdd` description trigger keyword ridotti da 12+ a 6 mirate
  (anti-dilution PR-6). Pattern Anthropic "Use when X".

### Removed
- `siae-tdd` trigger keyword: "implementa", "codifica", "sviluppa", "scrivi
  funzione", "aggiungi metodo", "crea classe", "modifica logica", "nuovo
  endpoint", "implementazione feature", "bug fix", "refactoring", "qualsiasi
  scrittura di codice".

### Migration path

Se invocavi `siae-tdd` con prompt come "implementa la funzione X" -> ora il
prompt attivera' `siae-brainstorming` (design first per memory backbone). Per
forzare TDD direttamente: usa "TDD per implementare X" o "Red-Green-Refactor
sulla funzione X". Comunque siae-brainstorming -> siae-writing-plans ->
siae-tdd e' il flusso canonico.
