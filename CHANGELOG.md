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

### Docs

- `hooks/ENV_VARS.md`: sezione "Review Evidence v2 — Scoring (v1.55+)".

### Pending (PR-B follow-up)

- baseline cache S3 + reviewer agent Step 0.6 + budget snapshot + skill_adoption + E2E test.

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
