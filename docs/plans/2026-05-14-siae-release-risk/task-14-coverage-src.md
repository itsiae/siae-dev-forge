# Task 14 — coverage_src.py chain fallback — Criterion 11

**Stato:** [DONE]
**SP:** 1.5 Human / 0.5 Augmented
**Dipendenze:** task-04, task-01

## Goal

Implementare `lib/release_risk/coverage_src.py` con chain fallback: `.claude/review-evidence/<sha>.json` → CI artifact (`coverage/jacoco.xml` o `coverage/lcov.info`) → AskUserQuestion. Threshold 70% per Criterion 11.

## File coinvolti

- Create: `lib/release_risk/coverage_src.py`

## Step

### Step 1 — Scrivi coverage_src.py

Write `lib/release_risk/coverage_src.py`:
```python
"""Criterion 11: coverage source con chain fallback."""
import json
import os
import re
from pathlib import Path
from typing import Optional
from lib.release_risk.schema import CriterionResult

COVERAGE_THRESHOLD_PCT = 70.0


def _from_evidence_file(repo_root: Path, sha: str) -> Optional[float]:
    """Read overall_pct da .claude/review-evidence/<sha>.json."""
    p = repo_root / ".claude" / "review-evidence" / f"{sha}.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        return float(data.get("metrics", {}).get("coverage", {}).get("overall_pct", -1))
    except (json.JSONDecodeError, ValueError, KeyError):
        return None


def _from_jacoco_xml(repo_root: Path) -> Optional[float]:
    """Parse coverage/jacoco.xml. Return overall_pct (covered/total * 100)."""
    p = repo_root / "coverage" / "jacoco.xml"
    if not p.exists():
        p = repo_root / "target" / "site" / "jacoco" / "jacoco.xml"
        if not p.exists():
            return None
    try:
        content = p.read_text()
        m = re.search(r'<counter type="LINE" missed="(\d+)" covered="(\d+)"', content)
        if m:
            missed, covered = int(m.group(1)), int(m.group(2))
            total = missed + covered
            return (covered / total * 100) if total > 0 else 0.0
    except Exception:
        return None
    return None


def _from_lcov_info(repo_root: Path) -> Optional[float]:
    """Parse coverage/lcov.info. Return overall_pct (LH/LF * 100 aggregated)."""
    p = repo_root / "coverage" / "lcov.info"
    if not p.exists():
        return None
    try:
        content = p.read_text()
        lh_total, lf_total = 0, 0
        for line in content.splitlines():
            if line.startswith("LH:"):
                lh_total += int(line[3:])
            elif line.startswith("LF:"):
                lf_total += int(line[3:])
        return (lh_total / lf_total * 100) if lf_total > 0 else None
    except Exception:
        return None


def get_coverage(repo_root: Path, sha: str) -> CriterionResult:
    """Criterion 11 entry. Chain fallback: evidence → jacoco → lcov → REQUIRES_INPUT."""
    for source_name, fn in [
        ("evidence:coverage", lambda: _from_evidence_file(repo_root, sha)),
        ("ci:jacoco", lambda: _from_jacoco_xml(repo_root)),
        ("ci:lcov", lambda: _from_lcov_info(repo_root)),
    ]:
        pct = fn()
        if pct is not None and pct >= 0:
            below = pct < COVERAGE_THRESHOLD_PCT
            return CriterionResult(
                id=11, name="Coverage < 70%",
                status="YES" if below else "NO", weight=2,
                evidence=[f"overall_pct={pct:.1f}", f"threshold={COVERAGE_THRESHOLD_PCT}"],
                source=source_name,
            )
    return CriterionResult(
        id=11, name="Coverage < 70%", status="REQUIRES_INPUT", weight=2,
        evidence=["no evidence file, no CI artifact"], source="ask:user",
    )
```

### Step 2 — Verifica

Run:
```bash
python3 -c "from lib.release_risk.coverage_src import get_coverage, COVERAGE_THRESHOLD_PCT; print(COVERAGE_THRESHOLD_PCT)"
```
Output atteso: `70.0`

### Step 3 — Commit

```bash
git add lib/release_risk/coverage_src.py
git commit -m "feat(release-risk): coverage_src chain fallback (evidence → jacoco → lcov → ask)"
```

## Criteri di accettazione

- [ ] 4 funzioni: `_from_evidence_file`, `_from_jacoco_xml`, `_from_lcov_info`, `get_coverage`
- [ ] Chain priority: evidence → jacoco → lcov → REQUIRES_INPUT
- [ ] Threshold 70% configurabile (constant)
- [ ] Path discovery jacoco: `coverage/jacoco.xml` o `target/site/jacoco/jacoco.xml`
- [ ] Commit eseguito
