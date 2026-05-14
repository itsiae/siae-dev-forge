# Changelog

Tutte le modifiche notabili a questo progetto sono documentate in questo file.

Il formato e' basato su [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
