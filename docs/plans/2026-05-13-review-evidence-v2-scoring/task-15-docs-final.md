# Task 15 — Docs final PR-B (forge-score skill + README + CHANGELOG)

**SP:** 1.0 · **AC mappati:** AC #11, AC #15, AC #16, AC #18, AC #19 · **Dipendenze:** Task 14 · **Wave:** 4

## Goal

Finalizza doc PR-B:
- `commands/forge-score.md` — skill on-demand per generare score card umano-leggibile
- `hooks/ENV_VARS.md` — aggiunge env PR-B (S3 + break-glass)
- `README.md` — sezione "Review Evidence v2 Scoring"
- `CHANGELOG.md` v1.55.0 — completa entry con PR-B
- `.devforge-scores.yml` template + JSON Schema

## File coinvolti

**Modificare:**
- `hooks/ENV_VARS.md`
- `README.md`
- `CHANGELOG.md`

**Creare:**
- `commands/forge-score.md`
- `docs/templates/.devforge-scores.yml`
- `docs/schemas/devforge-scores.schema.json`
- `tests/test_forge_score_command.py`

## Step

### Step 1 — `commands/forge-score.md`

```markdown
---
name: forge-score
description: On-demand: compute review-evidence v2 score card for current SHA + display human-readable markdown. No block, advisory only.
allowed-tools: Bash, Read
---

# /forge-score — Review Evidence v2 Score Card on-demand

Calcola lo score card v2 per il SHA corrente (5 dim + overall) e stampa il
risultato in markdown copy-paste pronto per `gh pr comment`.

## Cosa fa

1. Detect SHA corrente
2. Carica `.claude/review-evidence/<sha>.json` (se esiste) OR triggera compute
3. Stampa score card 5 dim + overall + decision + warnings
4. Stampa `BREAK-GLASS:` instructions se score sotto hard floor

## Quando usarlo

- **Prima di `gh pr create`** per anticipare il verdict
- **Debug:** capire perché un PR è stato bloccato
- **Post-merge:** baseline visibility

## Output esempio

```
review-evidence v2 — SHA abc12345

| Dim | Score | Delta vs baseline |
|---|---|---|
| Security  | 85 | +2 |
| Quality   | 72 | -3 (warn) |
| Coverage  | 68 | -5 (block) |
| Spec      | 90 | +0 |
| Discipline| 80 | +0 |
| **Overall** | **78** | **-1** |

Decision: BLOCK_REGRESSION
Reason: coverage regressed -5pp (budget: -5).
Override: touch ~/.claude/.devforge-skip-evidence (tracked, abuse 5/day).
```
```

### Step 2 — Aggiorna ENV_VARS.md

Aggiungi sezione PR-B vars (extends "Review Evidence v2 — Scoring"):

```markdown
### PR-B vars (Baseline cache + Break-glass)

| Env var | Default | Note |
|---|---|---|
| `DEVFORGE_BASELINE_S3_BUCKET` | `itsiae-review-evidence-baseline-prod` | S3 cache baseline |
| `DEVFORGE_BASELINE_S3_REGION` | `eu-west-1` | AWS region |
| `DEVFORGE_BASELINE_LOCAL_DIR` | `~/.claude/review-evidence-baseline-local` | Local fallback path |
| `DEVFORGE_BREAK_GLASS_REGEX` | `BREAK-GLASS:\s+\w+-\d+` | Pattern commit msg per override hard floor |
| `DEVFORGE_ACTIVITY_PROJECT` | (auto) | Project name per `~/.claude/projects/<X>/devforge-state/activity.jsonl` lookup |
```

### Step 3 — README.md sezione

Aggiungi (vicino a "Review Evidence Hook" v1):

```markdown
### Review Evidence v2 — Scoring (v1.55+)

Estensione di Review Evidence v1 con **scoring deterministico regression-based**.
5 dimensioni (security/quality/coverage/spec/discipline) → overall 0-100.

**Decisione:** 5 branch — AUTO_APPROVE / REVIEWER_HANDOFF / BLOCK_HARD_FLOOR /
BLOCK_REGRESSION / SEVERELY_DEGRADED.

**Tool stack OSS** (zero licenze): bandit + gitleaks + pip-audit + npm-audit + eslint-security
+ 2 check unique DevForge (arch_drift, skill_adoption).

**Baseline cache S3** (`itsiae-review-evidence-baseline-prod`, eu-west-1)
con local fallback per dev offline.

**Hard floor NON-OVERRIDABLE** da reviewer agent (solo admin BREAK-GLASS).

**Config:** `.devforge-scores.yml` (weights, hard_floors, regression_budget) +
`.devforge-arch.yml` (forbidden_paths).

**Skill on-demand:** `/forge-score`

**Design:** `docs/plans/2026-05-13-review-evidence-v2-scoring-design.md`
**Plan:** `docs/plans/2026-05-13-review-evidence-v2-scoring/`
```

### Step 4 — CHANGELOG.md PR-B completion

Estendi entry v1.55.0 con sezione "Added (PR-B)":

```markdown
### Added (PR-B advanced)

- **Baseline cache S3** (`lib/review_evidence/baseline_cache.py`): S3 backed
  via boto3 + local fallback. Key = main HEAD SHA, no TTL (A1 CRITICAL fix).
  Force-push invalidation via `git cat-file -e` (A2 fix).
- **`skill_adoption` check** (`lib/review_evidence/checks/skill_adoption.py`):
  4-tier fallback signal (activity.jsonl → design doc → git log → neutral).
  Bot PR detection (Dependabot, Renovate) → discipline skip.
- **Regression analyzer** (`lib/review_evidence/regression.py`): budget snapshot
  at PR_OPEN_TIME (E1 CRITICAL fix), 5 decision branch enforcement, hard floor
  NON-overridable da reviewer agent (F1+E5 CRITICAL fix).
- **Reviewer agent Step 0.6** (`agents/code-reviewer.md`): 5 decision branch
  gatekeeper logic. AUTO_APPROVE emette comunque review summary advisory (W2 fix).
- **Skill `/forge-score`** (`commands/forge-score.md`): on-demand score card.
- **40 edge case** (8 CRITICAL + 17 HIGH + 9 LOW) mitigati con chaos test suite v2
  (15+ test failure-injection).
- **Terraform module** (`infra/terraform/review-evidence-baseline/`): S3 bucket
  + IAM OIDC trust per `itsiae/*`.

### Configuration

- `.devforge-scores.yml` template in `docs/templates/`
- `.devforge-arch.yml` template
- JSON Schema `docs/schemas/devforge-scores.schema.json`
```

### Step 5 — Template + Schema

`docs/templates/.devforge-scores.yml` (esempio completo).

`docs/schemas/devforge-scores.schema.json` (JSON Schema draft-07 per validation IDE/CI).

### Step 6 — Test

```python
"""Tests for forge-score command + doc-sync v2 final."""
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_forge_score_command_exists():
    p = REPO_ROOT / "commands" / "forge-score.md"
    assert p.exists()
    content = p.read_text()
    assert re.search(r"^name:\s*forge-score", content, re.MULTILINE)


def test_readme_has_v2_section():
    rm = REPO_ROOT / "README.md"
    content = rm.read_text()
    assert "Review Evidence v2" in content or "v1.55" in content


def test_changelog_pr_b_complete():
    cl = (REPO_ROOT / "CHANGELOG.md").read_text()
    for keyword in ["baseline_cache", "skill_adoption", "regression", "forge-score", "Terraform"]:
        assert keyword in cl, f"Missing CHANGELOG keyword: {keyword}"


def test_template_devforge_scores_exists():
    p = REPO_ROOT / "docs" / "templates" / ".devforge-scores.yml"
    assert p.exists()


def test_schema_devforge_scores_valid_json():
    import json
    p = REPO_ROOT / "docs" / "schemas" / "devforge-scores.schema.json"
    assert p.exists()
    data = json.loads(p.read_text())
    assert "$schema" in data
```

### Step 7 — Commit

```bash
python3 -m pytest tests/test_forge_score_command.py -v
# 5 passed

git add commands/forge-score.md docs/templates/.devforge-scores.yml \
        docs/schemas/devforge-scores.schema.json \
        hooks/ENV_VARS.md README.md CHANGELOG.md \
        tests/test_forge_score_command.py
git commit -m "docs(review-evidence-v2): forge-score skill + ENV_VARS + README + CHANGELOG v1.55.0 (#task-15)"
```

## Criteri di accettazione

- [ ] `commands/forge-score.md` exists, frontmatter valido (name + description)
- [ ] ENV_VARS.md sezione "PR-B vars" (5 nuove env documentate)
- [ ] README.md sezione "Review Evidence v2 — Scoring"
- [ ] CHANGELOG.md v1.55.0 con sezioni PR-A + PR-B complete
- [ ] `docs/templates/.devforge-scores.yml` template valido
- [ ] `docs/schemas/devforge-scores.schema.json` JSON Schema valido
- [ ] 5 doc-sync test PASS
