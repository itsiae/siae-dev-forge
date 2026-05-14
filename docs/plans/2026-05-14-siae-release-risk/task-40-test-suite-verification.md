# Task 40 — Full test suite + mutation testing + coverage verification

**Stato:** [DONE-PARTIAL] — 134/134 test PASS, coverage 89% (escl. cli.py e2e). Mutation/lint DEFERRED a CI (tooling non in PATH locale). Vedi mutation-report.md.
**SP:** 1 Human / 0.5 Augmented
**Dipendenze:** task-29 (cli test ultima), task-39 (docs done)

## Goal

Eseguire full test suite, mutation testing (target ≥60%), coverage report (target ≥85% su `lib/release_risk/`), lint (ruff + shellcheck).

## File coinvolti

- Edit (se necessario): `.devforge-scores.yml` (aggiungi `lib/release_risk/` a scope mutation)

## Step

### Step 1 — Pytest full suite

Run:
```bash
pytest tests/test_release_risk_*.py -v --tb=short
```
Output atteso: TUTTI PASS. Documenta count totale (es. `80 passed in 12.34s`).

### Step 2 — Coverage report

Run:
```bash
pytest tests/test_release_risk_*.py --cov=lib/release_risk --cov-report=term-missing --cov-fail-under=85
```
Output atteso: coverage ≥85% per `lib/release_risk/*`. Se sotto soglia → aggiungi test mancanti.

### Step 3 — Mutation testing

Run (via mutmut o stryker, allineato a PR mutation runners corrente):
```bash
python3 -m lib.review_evidence.runners.mutmut --target lib/release_risk/ --threshold 60
# OR equivalent invocation via existing runners
```
Output atteso: mutation score ≥60%. Documenta surviving mutants in `docs/plans/2026-05-14-siae-release-risk/mutation-report.md`.

### Step 4 — Lint Python

Run:
```bash
ruff check lib/release_risk/ tests/test_release_risk_*.py
ruff format --check lib/release_risk/ tests/test_release_risk_*.py
```
Output atteso: 0 errors.

### Step 5 — Lint Bash hook

Run:
```bash
shellcheck hooks/pr-release-gate
```
Output atteso: 0 errors (warning ok).

### Step 6 — Eval set run

Run:
```bash
python3 -m lib.evals.runner evals/release-risk/disambiguation.yaml
```
Output atteso: 10/10 PASS.

### Step 7 — review-evidence v2 self-check

Run:
```bash
bash hooks/review-evidence
python3 -m lib.review_evidence.cli score
```
Output atteso: PASS (non BLOCK). AUTO_APPROVE o REVIEWER_HANDOFF ok.

### Step 8 — Aggiorna mutation-report.md

Write `docs/plans/2026-05-14-siae-release-risk/mutation-report.md`:
```markdown
# Mutation Testing Report — release_risk

**Data:** YYYY-MM-DD
**Target:** lib/release_risk/
**Threshold:** 60%

| File | Mutation Score | Surviving Mutants | Notes |
|---|---|---|---|
| detector.py | NN% | N | ... |
| ... | | | |

**Overall:** NN%
**Verdict:** PASS / FAIL
```

### Step 9 — Commit

```bash
git add docs/plans/2026-05-14-siae-release-risk/mutation-report.md
git commit -m "test(release-risk): full suite verification (coverage ≥85%, mutation ≥60%, eval 10/10)"
```

## Criteri di accettazione

- [ ] Pytest TUTTI PASS
- [ ] Coverage ≥85% per lib/release_risk/
- [ ] Mutation score ≥60%
- [ ] Ruff 0 errors
- [ ] Shellcheck pr-release-gate 0 errors
- [ ] Eval 10/10 PASS
- [ ] review-evidence v2 non BLOCK
- [ ] mutation-report.md committed
