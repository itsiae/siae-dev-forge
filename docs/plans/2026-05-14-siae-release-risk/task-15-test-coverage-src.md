# Task 15 — [TDD] test coverage_src.py

**Stato:** [PENDING]
**SP:** 1 Human / 0.5 Augmented
**Dipendenze:** task-14

## Goal

Test fallback chain con fixture evidence + jacoco + lcov.

## File coinvolti

- Create: `tests/test_release_risk_coverage_src.py`

## Step

### Step 1 — Scrivi test

Write `tests/test_release_risk_coverage_src.py`:
```python
import json
from pathlib import Path
import pytest
from lib.release_risk.coverage_src import get_coverage, COVERAGE_THRESHOLD_PCT


@pytest.fixture
def fake_repo(tmp_path):
    (tmp_path / ".claude" / "review-evidence").mkdir(parents=True)
    (tmp_path / "coverage").mkdir()
    return tmp_path


def test_coverage_from_evidence_below_threshold(fake_repo):
    sha = "abc123"
    p = fake_repo / ".claude" / "review-evidence" / f"{sha}.json"
    p.write_text(json.dumps({"metrics": {"coverage": {"overall_pct": 65.5}}}))
    r = get_coverage(fake_repo, sha)
    assert r.status == "YES"  # 65.5 < 70
    assert r.source == "evidence:coverage"


def test_coverage_from_evidence_above_threshold(fake_repo):
    sha = "abc123"
    p = fake_repo / ".claude" / "review-evidence" / f"{sha}.json"
    p.write_text(json.dumps({"metrics": {"coverage": {"overall_pct": 85.0}}}))
    r = get_coverage(fake_repo, sha)
    assert r.status == "NO"
    assert r.source == "evidence:coverage"


def test_coverage_from_jacoco_xml(fake_repo):
    p = fake_repo / "coverage" / "jacoco.xml"
    p.write_text('<counter type="LINE" missed="30" covered="70"/>')
    r = get_coverage(fake_repo, "no-evidence-sha")
    assert r.status == "NO"  # 70/(70+30) = 70% NOT below (threshold inclusive)
    assert r.source == "ci:jacoco"


def test_coverage_from_lcov_info(fake_repo):
    p = fake_repo / "coverage" / "lcov.info"
    p.write_text("LF:100\nLH:60\nLF:50\nLH:30\n")  # totale 90/150 = 60%
    r = get_coverage(fake_repo, "no-evidence")
    assert r.status == "YES"
    assert r.source == "ci:lcov"


def test_coverage_requires_input_when_all_fallback_fail(fake_repo):
    r = get_coverage(fake_repo, "no-sha")
    assert r.status == "REQUIRES_INPUT"
    assert r.source == "ask:user"


def test_coverage_chain_evidence_priority_over_jacoco(fake_repo):
    sha = "abc"
    p = fake_repo / ".claude" / "review-evidence" / f"{sha}.json"
    p.write_text(json.dumps({"metrics": {"coverage": {"overall_pct": 85.0}}}))
    p2 = fake_repo / "coverage" / "jacoco.xml"
    p2.write_text('<counter type="LINE" missed="50" covered="50"/>')  # 50% < 70
    r = get_coverage(fake_repo, sha)
    assert r.source == "evidence:coverage"  # evidence wins
    assert r.status == "NO"
```

### Step 2 — Esegui

Run:
```bash
pytest tests/test_release_risk_coverage_src.py -v
```
Output atteso: 6 PASSED.

### Step 3 — Commit

```bash
git add tests/test_release_risk_coverage_src.py
git commit -m "test(release-risk): coverage_src chain fallback (6 scenarios)"
```

## Criteri di accettazione

- [ ] 6 test PASSED (evidence below, evidence above, jacoco, lcov, all fail, chain priority)
- [ ] Tmp_path fixture isolation
- [ ] Chain priority verificato (evidence > jacoco > lcov)
- [ ] Commit eseguito
