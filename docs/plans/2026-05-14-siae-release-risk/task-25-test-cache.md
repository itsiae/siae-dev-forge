# Task 25 — [TDD] test cache.py

**Stato:** [PENDING]
**SP:** 1 Human / 0.5 Augmented
**Dipendenze:** task-24

## Goal

Test hit/miss/baseline drift/corruption/idempotency.

## File coinvolti

- Create: `tests/test_release_risk_cache.py`

## Step

### Step 1 — Write test

Write `tests/test_release_risk_cache.py`:
```python
from unittest.mock import patch
from pathlib import Path
import pytest
from lib.release_risk.cache import (
    compute_diff_hash, cache_key, get, put,
    idempotency_marker, already_posted_in_pr,
)
from lib.release_risk.schema import (
    ReleaseRiskReport, ScoreCard, GenesisInfo, CriterionResult,
)


@pytest.fixture
def fake_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("lib.release_risk.cache.CACHE_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def sample_report():
    return ReleaseRiskReport(
        service="svc", release_branch="release/1.0", target_branch="main",
        diff_hash="abc123", baseline_main_sha="1a2b3c4d",
        diff_summary={}, identification={},
        genesis=GenesisInfo(merge_commits=[]),
        criteria=[CriterionResult(id=1, name="c1", status="YES", weight=3)],
        scorecard=ScoreCard(total_score=3, level="LOW", decision="GO", decision_rationale="r"),
        generated_at="2026-05-14T10:00:00Z",
        output_path="docs/releases/x.md",
    )


def test_compute_diff_hash_deterministic():
    h1 = compute_diff_hash(["a.py", "b.py"], "content")
    h2 = compute_diff_hash(["b.py", "a.py"], "content")  # different order
    assert h1 == h2  # files sorted
    assert len(h1) == 12


def test_compute_diff_hash_differs_on_content():
    h1 = compute_diff_hash(["a.py"], "v1")
    h2 = compute_diff_hash(["a.py"], "v2")
    assert h1 != h2


def test_get_miss_returns_none(fake_cache_dir):
    r = get("release/1.0", "deadbeef0000", "1a2b3c4d5e6f")
    assert r is None


def test_put_then_get_roundtrip(fake_cache_dir, sample_report):
    ok = put("release/1.0", "deadbeef0000", "1a2b3c4d5e6f", sample_report)
    assert ok
    r = get("release/1.0", "deadbeef0000", "1a2b3c4d5e6f")
    assert r is not None
    assert r.service == "svc"


def test_baseline_drift_different_cache_key(fake_cache_dir, sample_report):
    put("release/1.0", "deadbeef0000", "OLDMAIN1", sample_report)
    # cambio baseline-main-sha simula nuova release mergiata in main
    r = get("release/1.0", "deadbeef0000", "NEWMAIN2")
    assert r is None  # different baseline → different cache key → miss


def test_corrupted_cache_treated_as_miss(fake_cache_dir):
    p = cache_key("release/1.0", "deadbeef0000", "1a2b3c4d")
    p.write_text("not json {{{")
    r = get("release/1.0", "deadbeef0000", "1a2b3c4d")
    assert r is None


def test_idempotency_marker_format():
    m = idempotency_marker("abc123")
    assert m == "<!-- release-risk:abc123 -->"


def test_already_posted_detects_marker():
    bodies = ["# Header", "<!-- release-risk:abc123 -->\nScorecard content"]
    assert already_posted_in_pr(bodies, "abc123")


def test_already_posted_marker_mismatch():
    bodies = ["<!-- release-risk:OTHER123 -->"]
    assert not already_posted_in_pr(bodies, "abc123")
```

### Step 2 — Esegui

```bash
pytest tests/test_release_risk_cache.py -v
```
Output atteso: 9 PASSED.

### Step 3 — Commit

```bash
git add tests/test_release_risk_cache.py
git commit -m "test(release-risk): cache 3-key + baseline drift + idempotency"
```

## Criteri di accettazione

- [ ] 9 test PASSED
- [ ] Test baseline drift critico (diff stesso, baseline diverso → miss)
- [ ] Test corruption handling
- [ ] Test idempotency marker match/mismatch
- [ ] Commit eseguito
