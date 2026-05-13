# Task 08 — Docs partial PR-A (ENV_VARS draft + CHANGELOG entry)

**SP:** 0.5 · **AC mappati:** AC #15 (parz), AC #16 · **Dipendenze:** Task 01-07 · **Wave:** 2

## Goal

Aggiornare `hooks/ENV_VARS.md` con env var nuove PR-A + entry CHANGELOG.md "Unreleased — v1.55.0" preliminare (sarà completata in Task 15).

## File coinvolti

**Modificare:**
- `hooks/ENV_VARS.md`
- `CHANGELOG.md`

**Creare:**
- `tests/test_env_vars_doc_sync_v2.py` (estende test existente)

## Step

### Step 1 — Aggiorna `hooks/ENV_VARS.md`

Aggiungi sezione dopo "## Review Evidence (v1.54+)":

```markdown
## Review Evidence v2 — Scoring (v1.55+)

Estensione di Review Evidence v1 con scoring deterministico regression-based.
Tutte le env var v1 (`DEVFORGE_EVIDENCE_*`) restano valide.

### Config file paths

| Env var | Default | Note |
|---|---|---|
| `DEVFORGE_SCORES_CONFIG_PATH` | `.devforge-scores.yml` | Override path config (testing) |
| `DEVFORGE_ARCH_CONFIG_PATH` | `.devforge-arch.yml` | Override path arch rules |

### Behavior toggles (PR-A foundation)

| Env var | Default | Note |
|---|---|---|
| `DEVFORGE_SCORING_V2_ENABLED` | `0` (PR-A rollout phase) → `1` (PR-B GA) | Master kill-switch v2 scoring (fallback v1) |

PR-B aggiungerà:
- `DEVFORGE_BASELINE_S3_BUCKET` (default `itsiae-review-evidence-baseline-prod`)
- `DEVFORGE_BASELINE_S3_REGION` (default `eu-west-1`)
- `DEVFORGE_BASELINE_LOCAL_FALLBACK` (default `1`)
- `DEVFORGE_BREAK_GLASS_REGEX` (default `BREAK-GLASS: \w+-\d+`)
```

### Step 2 — Aggiungi entry CHANGELOG.md

In testa al file (subito sopra entry v1.54.x più recente):

```markdown
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
  validation sum ≈ 1.0 (E4 fix). Config change detection in PR (CRITICAL B3 fix).
- **Hook bash v2 extension** (`hooks/review-evidence`): 5 decision branch case
  per gestire `regression_verdict.decision`. v1 fallback preservato.

### Changed

- `lib/review_evidence/collector.py`: extension `orchestrate_v2()` per scoring
  layer. v1 `orchestrate()` stays for back-compat.

### Docs

- `hooks/ENV_VARS.md`: sezione "Review Evidence v2 — Scoring (v1.55+)".

### Pending (PR-B follow-up)

- baseline cache S3 + reviewer agent Step 0.6 + budget snapshot + skill_adoption + E2E test.
```

### Step 3 — Test doc-sync

```python
"""Verify ENV_VARS.md doc-sync per nuove env v2."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

V2_EXPECTED_VARS = {
    "DEVFORGE_SCORES_CONFIG_PATH",
    "DEVFORGE_ARCH_CONFIG_PATH",
    "DEVFORGE_SCORING_V2_ENABLED",
    # PR-B vars saranno aggiunte in Task 15
}


def test_env_vars_md_documents_v2():
    content = (REPO_ROOT / "hooks" / "ENV_VARS.md").read_text()
    missing = [v for v in V2_EXPECTED_VARS if v not in content]
    assert not missing, f"V2 env vars missing from ENV_VARS.md: {missing}"


def test_changelog_has_v1_55_entry():
    cl = (REPO_ROOT / "CHANGELOG.md").read_text()
    assert "v1.55.0" in cl
    assert "review-evidence v2" in cl.lower() or "scoring v2" in cl.lower()
```

### Step 4 — Commit

```bash
python3 -m pytest tests/test_env_vars_doc_sync_v2.py -v
# 2 passed

git add hooks/ENV_VARS.md CHANGELOG.md tests/test_env_vars_doc_sync_v2.py
git commit -m "docs(review-evidence-v2): ENV_VARS draft + CHANGELOG v1.55.0 entry (#task-08)"
```

## Criteri di accettazione

- [ ] 3 nuove env var documentate in ENV_VARS.md ("v1.55+ Review Evidence v2 — Scoring")
- [ ] CHANGELOG.md ha entry "[Unreleased] — v1.55.0" con sezioni Added/Changed/Docs/Pending
- [ ] Doc-sync test PASS (2 test)
- [ ] No regression v1
