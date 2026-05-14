# Task 23 — [TDD] test scoring boundaries

**Stato:** [PENDING]
**SP:** 1 Human / 0.5 Augmented
**Dipendenze:** task-22

## Goal

Test 9 scenari: boundaries 0/4/5/9/10/14/15, negative weights, suggested followup, partial flag.

## File coinvolti

- Create: `tests/test_release_risk_scoring.py`

## Step

### Step 1 — Write test

Write `tests/test_release_risk_scoring.py`:
```python
import pytest
from lib.release_risk.scoring import compute_score, MAX_SCORE
from lib.release_risk.schema import CriterionResult


def _cr(id_, status, weight, evidence=None):
    return CriterionResult(id=id_, name=f"c{id_}", status=status, weight=weight,
                            evidence=evidence or [])


def test_empty_score_low():
    sc = compute_score([])
    assert sc.total_score == 0
    assert sc.level == "LOW"
    assert sc.decision == "GO"


def test_score_4_boundary_low():
    crs = [_cr(1, "YES", 3), _cr(15, "YES", 1)]  # 3+1=4
    sc = compute_score(crs)
    assert sc.total_score == 4
    assert sc.level == "LOW"


def test_score_5_boundary_medium():
    crs = [_cr(1, "YES", 3), _cr(2, "YES", 2)]  # 5
    sc = compute_score(crs)
    assert sc.total_score == 5
    assert sc.level == "MEDIUM"


def test_score_9_boundary_medium():
    crs = [_cr(1, "YES", 3), _cr(3, "YES", 3), _cr(2, "YES", 2), _cr(15, "YES", 1)]  # 9
    sc = compute_score(crs)
    assert sc.level == "MEDIUM"


def test_score_10_boundary_high():
    crs = [_cr(1, "YES", 3), _cr(3, "YES", 3), _cr(2, "YES", 2), _cr(4, "YES", 2)]  # 10
    sc = compute_score(crs)
    assert sc.total_score == 10
    assert sc.level == "HIGH"
    assert sc.decision == "POSTPONE_WITHOUT_TL"


def test_score_15_critical():
    crs = [_cr(1, "YES", 3), _cr(3, "YES", 3), _cr(5, "YES", 3), _cr(8, "YES", 3),
           _cr(9, "YES", 3)]  # 15
    sc = compute_score(crs)
    assert sc.level == "CRITICAL"
    assert sc.decision == "NO_GO_WITHOUT_CAB"


def test_negative_weight_clamped_to_zero():
    crs = [_cr(10, "YES", -1), _cr(13, "YES", -1)]  # -2 clamp 0
    sc = compute_score(crs)
    assert sc.total_score == 0


def test_partial_flag_set_on_requires_input():
    crs = [_cr(1, "YES", 3), _cr(5, "REQUIRES_INPUT", 3)]
    sc = compute_score(crs)
    assert sc.partial is True


def test_suggested_followup_security_on_c17_flag():
    crs = [_cr(17, "YES", 2, evidence=["suggested_followup_security=True"])]
    sc = compute_score(crs)
    assert "siae-security" in sc.suggested_followups


def test_max_score_constant():
    assert MAX_SCORE == 36
```

### Step 2 — Esegui

```bash
pytest tests/test_release_risk_scoring.py -v
```
Output atteso: 10 PASSED.

### Step 3 — Commit

```bash
git add tests/test_release_risk_scoring.py
git commit -m "test(release-risk): scoring boundaries 0-4/5-9/10-14/15+ + partial + followup"
```

## Criteri di accettazione

- [ ] 10 test PASSED
- [ ] Test ogni boundary level
- [ ] Test negative clamp
- [ ] Test followup trigger
- [ ] Commit eseguito
