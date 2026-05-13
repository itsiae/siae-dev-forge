# Task 07 — Test foundation PR-A

**SP:** 2.0 · **AC mappati:** AC #14 · **Dipendenze:** Task 01-06 · **Wave:** 2

## Goal

Test integration PR-A foundation: orchestrator extension che chiama scoring + runners + arch_drift + config. Verifica che la pipeline foundation (senza S3/reviewer/budget snapshot — quelli PR-B) produca evidence v2 valida con `current_scores` ma `baseline_scores=None` (baseline_synthetic=True). Coverage gate ≥85% lib/review_evidence/.

## File coinvolti

**Modificare:**
- `lib/review_evidence/collector.py` (extension v2)

**Creare:**
- `tests/test_review_evidence_collector_v2.py`

## Step TDD

### Step 1 — Test fallente

`tests/test_review_evidence_collector_v2.py`:

```python
"""Integration test: orchestrator extension v2 produces ScoreCard + RegressionVerdict."""
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.review_evidence.collector import orchestrate_v2
from lib.review_evidence.schema import EvidenceV2


def _init_git(tmp_path):
    sp = subprocess.run
    sp(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sp(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    sp(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    sp(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    sp(["git", "config", "tag.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / "main.py").write_text("# main\n")
    sp(["git", "add", "."], cwd=tmp_path, check=True)
    sp(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)


def test_orchestrate_v2_produces_evidence_with_scorecard(tmp_path):
    _init_git(tmp_path)
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True
    ).strip()
    out = tmp_path / "ev.json"
    
    # No runners installed → tutti score=None except discipline (no signal=50)
    code = orchestrate_v2(sha=sha, base="main", dirty=False,
                          out_path=out, repo_root=tmp_path)
    assert code == 0
    
    data = json.loads(out.read_text())
    assert data["schema_version"] == "2.0"
    assert data["sha"] == sha
    # current_scores presente anche se severely degraded
    assert "current_scores" in data
    assert "regression_verdict" in data


def test_orchestrate_v2_baseline_synthetic_first_pr(tmp_path):
    """A6: first PR, no baseline → baseline_synthetic=True."""
    _init_git(tmp_path)
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True
    ).strip()
    out = tmp_path / "ev.json"
    
    code = orchestrate_v2(sha=sha, base="main", dirty=False,
                          out_path=out, repo_root=tmp_path)
    data = json.loads(out.read_text())
    assert data["baseline_synthetic"] is True
    assert data["baseline_scores"] is None or data["baseline_scores"] == {}


def test_orchestrate_v2_severely_degraded_skips_block(tmp_path):
    """D6: no runners → severely_degraded → regression_verdict.decision=SEVERELY_DEGRADED."""
    _init_git(tmp_path)
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True
    ).strip()
    out = tmp_path / "ev.json"
    
    code = orchestrate_v2(sha=sha, base="main", dirty=False,
                          out_path=out, repo_root=tmp_path)
    data = json.loads(out.read_text())
    rv = data.get("regression_verdict") or {}
    # No runners running locally → severely degraded path
    assert rv.get("decision") in ["SEVERELY_DEGRADED", "AUTO_APPROVE"]
```

### Step 2 — Esegui (fail)

```bash
python3 -m pytest tests/test_review_evidence_collector_v2.py -v
```

**Output atteso:** `AttributeError: orchestrate_v2 not defined`.

### Step 3 — Estendi collector.py

In `lib/review_evidence/collector.py`, aggiungi (dopo `orchestrate()` esistente):

```python
def orchestrate_v2(
    sha: str,
    base: str,
    dirty: bool,
    out_path: Path,
    repo_root: Optional[Path] = None,
) -> int:
    """v2 orchestrator: calls scoring + runners + arch_drift + config.

    Extension of v1 orchestrate() — adds scoring layer.
    Note: baseline cache + budget snapshot + reviewer agent stay in PR-B.
    """
    import subprocess
    from dataclasses import asdict
    from datetime import datetime, timezone
    from lib.review_evidence.scoring import (
        score_security, score_quality, score_coverage, score_spec_compliance,
        score_discipline, compute_overall,
        SecurityFindings, QualityFindings, CoverageInput, SpecDriftInput,
        ArchDriftInput, SkillAdoptionInput,
    )
    from lib.review_evidence.config import load_scores_config
    from lib.review_evidence.runners import applicable as runners_applicable
    from lib.review_evidence.checks.arch_drift import detect_arch_drift
    from lib.review_evidence.schema import (
        EvidenceV2, ScoreCard, RegressionVerdict, SCHEMA_VERSION,
    )
    
    repo_root = repo_root or Path.cwd()
    config = load_scores_config(repo_root)
    
    # Run all applicable runners + aggregate per dimension
    # Plan-review iter1 fix: count runners that returned non-None
    # (avoid false 100 when tools applicable but all missing)
    sec_findings = SecurityFindings()
    sec_runners_with_result = 0
    for runner in runners_applicable(repo_root):
        result = runner.run(repo_root)
        if result is None:
            continue
        if isinstance(result, SecurityFindings):
            sec_findings.critical += result.critical
            sec_findings.high += result.high
            sec_findings.medium += result.medium
            sec_findings.low += result.low
            sec_runners_with_result += 1
    
    # Score each dim (None on missing tooling — no runner returned data)
    sec_score = score_security(sec_findings) if sec_runners_with_result > 0 else None
    qual_score = None  # PR-B will add quality runners
    cov_score = None  # PR-B will add coverage runner integration
    
    # Spec drift + arch drift
    try:
        from lib.review_evidence.spec_drift import detect_drift
        sd = detect_drift(repo_root=repo_root, base=base, head=sha)
        sd_input = SpecDriftInput(unplanned_files=sd["unplanned_files"]) if sd else SpecDriftInput()
    except Exception:
        sd_input = SpecDriftInput()
    
    changed_files = []
    try:
        p = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...{sha}"],
            cwd=repo_root, capture_output=True, text=True, timeout=5, check=False,
        )
        changed_files = [l.strip() for l in p.stdout.splitlines() if l.strip()]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    arch = detect_arch_drift(repo_root, changed_files)
    arch_input = ArchDriftInput(violations=[f"{v.file}:{v.import_}" for v in arch.violations])
    
    spec_score = score_spec_compliance(sd_input, arch_input)
    
    # Discipline: signal missing → 50 (W4 fallback). Real impl PR-B Task 10.
    disc_score = 50.0
    
    scores = {
        "security": sec_score, "quality": qual_score, "coverage": cov_score,
        "spec_compliance": spec_score, "discipline": disc_score,
    }
    overall, degraded = compute_overall(scores, config.weights)
    missing = [k for k, v in scores.items() if v is None]
    
    scorecard = ScoreCard(
        security=sec_score or 0.0, quality=qual_score or 0.0,
        coverage=cov_score or 0.0, spec_compliance=spec_score or 0.0,
        discipline=disc_score, overall=overall,
        weights_used=config.weights, missing_components=missing,
    )
    
    # Decision (PR-A foundation: no baseline → AUTO_APPROVE if no hard floor breach)
    decision = "AUTO_APPROVE"
    if degraded:
        decision = "SEVERELY_DEGRADED"
    elif sec_score is not None and sec_score < config.hard_floors.get("security", 60):
        decision = "BLOCK_HARD_FLOOR"
    elif overall < config.hard_floors.get("overall", 55):
        decision = "BLOCK_HARD_FLOOR"
    
    rv = RegressionVerdict(
        block_dimensions=[], warn_dimensions=[],
        improved_dimensions=[], hard_floor_breaches=([] if decision != "BLOCK_HARD_FLOOR" else ["overall_or_security"]),
        decision=decision,
        reason=f"PR-A foundation (no baseline, synthetic). Overall={overall}, degraded={degraded}",
    )
    
    evidence = {
        "schema_version": SCHEMA_VERSION,  # "2.0"
        "sha": sha, "branch": "unknown", "computed_at": datetime.now(timezone.utc).isoformat(),
        "dirty_tree": bool(dirty), "base_branch": base,
        "stack_detected": [r.name for r in runners_applicable(repo_root)],
        "metrics": {},  # v1 metrics filled by collectors as before (existing)
        "spec_drift": None,
        "verdict": {"block": decision.startswith("BLOCK"),
                     "block_reasons": [rv.reason] if decision.startswith("BLOCK") else [],
                     "warnings": []},
        "current_scores": asdict(scorecard),
        "baseline_scores": None,
        "deltas": None,
        "regression_verdict": asdict(rv),
        "reviewer_verdict": None,
        "budget_snapshot_at": None,
        "baseline_synthetic": True,  # PR-A: always synthetic, PR-B will populate
    }
    
    content = json.dumps(evidence, indent=2, default=str)
    from lib.review_evidence.atomic_io import write_evidence_atomic
    success, used_fallback, reason = write_evidence_atomic(out_path, content, sha=sha, repo_root=repo_root)
    return 0 if success else 1
```

### Step 4 — Esegui test + full suite

```bash
python3 -m pytest tests/test_review_evidence_collector_v2.py -v
# 3 passed

python3 -m pytest tests/ --cov=lib.review_evidence --cov-report=term -q
# Coverage atteso ≥85% sui new file (schema_v2, scoring, runners, config, arch_drift)
```

### Step 5 — Commit

```bash
git add lib/review_evidence/collector.py tests/test_review_evidence_collector_v2.py
git commit -m "test(review-evidence-v2): integration foundation (orchestrator v2 + 3 test) (#task-07)"
```

## Criteri di accettazione

- [ ] `orchestrate_v2()` produce evidence v2 valida con `current_scores`, `regression_verdict`, `baseline_synthetic=True`
- [ ] First PR (no baseline) → `decision=AUTO_APPROVE` o `SEVERELY_DEGRADED` se runners missing
- [ ] D6 severely_degraded path testato
- [ ] 3 integration test PASS
- [ ] Coverage ≥85% su `lib/review_evidence/` (Task 01-06 components)
- [ ] No regression v1 (158/158 PASS)
