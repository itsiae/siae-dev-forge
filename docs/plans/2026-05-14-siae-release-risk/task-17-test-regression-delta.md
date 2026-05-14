# Task 17 — [TDD] test regression_delta.py

**Stato:** [PENDING]
**SP:** 1.5 Human / 0.5 Augmented
**Dipendenze:** task-16

## Goal

Test 6 scenari + mock baseline_cache.

## File coinvolti

- Create: `tests/test_release_risk_regression_delta.py`

## Step

### Step 1 — Scrivi test

Write `tests/test_release_risk_regression_delta.py`:
```python
from unittest.mock import MagicMock, patch
from pathlib import Path
import pytest
from lib.release_risk.regression_delta import (
    evaluate_criterion_16, resolve_prev_release_main_sha, count_test_disabled_deleted,
    COVERAGE_DELTA_THRESHOLD_PP,
)


@pytest.fixture
def fake_baseline_with_coverage():
    def fetcher(sha: str):
        sc = MagicMock()
        sc.coverage = 80.0
        return sc
    return fetcher


def test_first_release_no_baseline(tmp_path):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = ""  # no release branches
        r = evaluate_criterion_16(tmp_path, "release/1.0.0", 75.0, baseline_fetcher=None)
        assert r.status == "TOOL_UNAVAILABLE"
        assert "first release" in r.evidence[0]


def test_no_baseline_fetcher_provided(tmp_path):
    with patch("lib.release_risk.regression_delta.resolve_prev_release_main_sha",
               return_value="abc123def456"):
        r = evaluate_criterion_16(tmp_path, "release/2.0.0", 75.0, baseline_fetcher=None)
        assert r.status == "TOOL_UNAVAILABLE"
        assert "baseline_fetcher not provided" in r.evidence[0]


def test_coverage_delta_below_threshold_triggers_yes(tmp_path, fake_baseline_with_coverage):
    with patch("lib.release_risk.regression_delta.resolve_prev_release_main_sha",
               return_value="abc123def456"), \
         patch("lib.release_risk.regression_delta.count_test_disabled_deleted",
               return_value=(0, 0)):
        r = evaluate_criterion_16(tmp_path, "release/2.0.0", 75.0,
                                   baseline_fetcher=fake_baseline_with_coverage)
        # 75 - 80 = -5pp, below threshold -2pp → YES
        assert r.status == "YES"
        assert r.weight == 2
        assert "coverage_delta=-5.00pp" in r.evidence[1]


def test_coverage_delta_above_threshold_test_clean_no(tmp_path, fake_baseline_with_coverage):
    with patch("lib.release_risk.regression_delta.resolve_prev_release_main_sha",
               return_value="abc123def456"), \
         patch("lib.release_risk.regression_delta.count_test_disabled_deleted",
               return_value=(0, 0)):
        r = evaluate_criterion_16(tmp_path, "release/2.0.0", 79.5,
                                   baseline_fetcher=fake_baseline_with_coverage)
        # 79.5 - 80 = -0.5pp, above threshold -2 → no coverage trigger
        # 0 disabled, 0 deleted → no test trigger
        assert r.status == "NO"


def test_test_disabled_triggers_yes(tmp_path, fake_baseline_with_coverage):
    with patch("lib.release_risk.regression_delta.resolve_prev_release_main_sha",
               return_value="abc123def456"), \
         patch("lib.release_risk.regression_delta.count_test_disabled_deleted",
               return_value=(2, 0)):
        r = evaluate_criterion_16(tmp_path, "release/2.0.0", 80.0,
                                   baseline_fetcher=fake_baseline_with_coverage)
        assert r.status == "YES"
        assert "test_disabled_added=2" in r.evidence[2]


def test_test_deleted_triggers_yes(tmp_path, fake_baseline_with_coverage):
    with patch("lib.release_risk.regression_delta.resolve_prev_release_main_sha",
               return_value="abc123def456"), \
         patch("lib.release_risk.regression_delta.count_test_disabled_deleted",
               return_value=(0, 1)):
        r = evaluate_criterion_16(tmp_path, "release/2.0.0", 80.0,
                                   baseline_fetcher=fake_baseline_with_coverage)
        assert r.status == "YES"
        assert "test_deleted=1" in r.evidence[3]


def test_resolve_prev_release_subprocess_error(tmp_path):
    import subprocess
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")):
        r = resolve_prev_release_main_sha("release/2.0.0", tmp_path)
        assert r is None
```

### Step 2 — Esegui

Run:
```bash
pytest tests/test_release_risk_regression_delta.py -v
```
Output atteso: 7 PASSED.

### Step 3 — Commit

```bash
git add tests/test_release_risk_regression_delta.py
git commit -m "test(release-risk): regression_delta (6 scenarios + subprocess error)"
```

## Criteri di accettazione

- [ ] 7 test PASSED
- [ ] Mock baseline_fetcher
- [ ] Mock subprocess.run per git commands
- [ ] Test first release fallback
- [ ] Test trigger condition multi-path (coverage, disabled, deleted)
- [ ] Commit eseguito
