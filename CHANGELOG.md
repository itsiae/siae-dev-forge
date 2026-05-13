# Changelog

Tutte le modifiche notabili a questo progetto sono documentate in questo file.

Il formato e' basato su [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
