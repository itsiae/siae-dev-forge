# Task 01 — Schema v2 dataclass + forward-compat

**SP:** 1.5 · **AC mappati:** AC #9 · **Dipendenze:** nessuna · **Wave:** 1

## Goal

Estendere `lib/review_evidence/schema.py` con 3 nuovi dataclass (`ScoreCard`, `RegressionVerdict`, `ReviewerVerdict`) + classe `EvidenceV2(Evidence)` con field Optional additive. Schema_version bump `"1.0"` → `"2.0"`. Forward-compat con v1: `_safe_kwargs` esistente filtra campi sconosciuti (PR #241 fix CRITICAL-1).

## File coinvolti

**Modificare:**
- `lib/review_evidence/schema.py`

**Creare:**
- `tests/test_review_evidence_schema_v2.py`
- `tests/fixtures/review-evidence/evidence_v2_clean.json`
- `tests/fixtures/review-evidence/evidence_v2_with_unknown_fields.json`

## Step TDD

### Step 1 — Scrivi test fallente

`tests/test_review_evidence_schema_v2.py`:

```python
"""Tests for v2 schema extensions — ScoreCard, RegressionVerdict, ReviewerVerdict."""
import json
from pathlib import Path

import pytest

from lib.review_evidence.schema import (
    EvidenceV2,
    ScoreCard,
    RegressionVerdict,
    ReviewerVerdict,
    evidence_from_json,
    evidence_to_json,
)

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_schema_version_2_0_supported():
    """v2 deserialize OK."""
    raw = json.loads((FIX / "evidence_v2_clean.json").read_text())
    ev = evidence_from_json(raw)
    assert ev.schema_version == "2.0"
    assert isinstance(ev, EvidenceV2)
    assert ev.current_scores.security == 85.0


def test_scorecard_fields():
    sc = ScoreCard(
        security=85.0, quality=72.0, coverage=68.0,
        spec_compliance=90.0, discipline=80.0, overall=79.0,
        weights_used={"security": 0.30, "quality": 0.20, "coverage": 0.20,
                       "spec_compliance": 0.15, "discipline": 0.15},
        missing_components=[],
    )
    assert sc.overall == 79.0
    assert sum(sc.weights_used.values()) == pytest.approx(1.0, abs=0.01)


def test_regression_verdict_5_decision_values():
    """F2 iter2 fix: 5 decision branch enum (no 4)."""
    valid = {"AUTO_APPROVE", "REVIEWER_HANDOFF", "BLOCK_HARD_FLOOR",
             "BLOCK_REGRESSION", "SEVERELY_DEGRADED"}
    for decision in valid:
        rv = RegressionVerdict(
            block_dimensions=[], warn_dimensions=[],
            improved_dimensions=[], hard_floor_breaches=[],
            decision=decision, reason="test",
        )
        assert rv.decision == decision


def test_reviewer_verdict_status():
    rv = ReviewerVerdict(
        status="APPROVED", reason="all good", invoked_at="2026-05-13T10:00:00Z",
        block=False,
    )
    assert rv.status == "APPROVED"
    assert rv.block is False


def test_forward_compat_unknown_fields_stripped():
    """Schema 1.5 (future minor) con UNKNOWN_FIELD non rompe."""
    raw = json.loads((FIX / "evidence_v2_with_unknown_fields.json").read_text())
    ev = evidence_from_json(raw)
    assert ev.schema_version == "1.5"
    # Unknown fields silently filtered (CRITICAL-1 fix from PR #241)
    assert ev.verdict.block is False


def test_v1_evidence_still_deserialize_as_v2():
    """v1 fixture (existing tests/fixtures/review-evidence/evidence_clean.json) must work."""
    raw = json.loads((FIX / "evidence_clean.json").read_text())
    ev = evidence_from_json(raw)
    assert ev.schema_version == "1.0"
    # v2-only fields are None on v1 deserialize
    assert ev.current_scores is None or not hasattr(ev, "current_scores")


def test_v2_roundtrip():
    raw = json.loads((FIX / "evidence_v2_clean.json").read_text())
    ev = evidence_from_json(raw)
    rebuilt = json.loads(evidence_to_json(ev))
    assert rebuilt["schema_version"] == "2.0"
    assert rebuilt["current_scores"]["security"] == 85.0
```

Crea fixture `evidence_v2_clean.json`:

```json
{
  "schema_version": "2.0",
  "sha": "abc123",
  "base_sha": "def456",
  "branch": "feature/test",
  "computed_at": "2026-05-13T10:00:00Z",
  "dirty_tree": false,
  "base_branch": "main",
  "stack_detected": ["python"],
  "metrics": {},
  "spec_drift": null,
  "verdict": {"block": false, "block_reasons": [], "warnings": []},
  "current_scores": {
    "security": 85.0, "quality": 72.0, "coverage": 68.0,
    "spec_compliance": 90.0, "discipline": 80.0, "overall": 79.0,
    "weights_used": {"security": 0.30, "quality": 0.20, "coverage": 0.20,
                      "spec_compliance": 0.15, "discipline": 0.15},
    "missing_components": []
  },
  "baseline_scores": null,
  "deltas": null,
  "regression_verdict": null,
  "reviewer_verdict": null,
  "budget_snapshot_at": null,
  "baseline_synthetic": true
}
```

Crea fixture `evidence_v2_with_unknown_fields.json`:

```json
{
  "schema_version": "1.5",
  "sha": "x", "branch": "x", "computed_at": "x",
  "dirty_tree": false, "base_branch": "main", "stack_detected": [],
  "metrics": {},
  "spec_drift": null,
  "verdict": {"block": false, "block_reasons": [], "warnings": [], "UNKNOWN_NEW_FIELD": "future"},
  "FUTURE_TOP_LEVEL": "experimental"
}
```

### Step 2 — Esegui (fail)

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge"
python3 -m pytest tests/test_review_evidence_schema_v2.py -v
```

**Output atteso:** `ImportError: cannot import name 'EvidenceV2'` (o simile).

### Step 3 — Implementa

Aggiungi a `lib/review_evidence/schema.py`:

```python
# At top, bump SUPPORTED_VERSIONS
SUPPORTED_VERSIONS = {"1.0", "1.1", "2.0"}  # minor 1.x forward-compat
SCHEMA_VERSION = "2.0"  # current writer version


@dataclass
class ScoreCard:
    security: float
    quality: float
    coverage: float
    spec_compliance: float
    discipline: float
    overall: float
    weights_used: dict[str, float]
    missing_components: list[str] = field(default_factory=list)


@dataclass
class RegressionVerdict:
    block_dimensions: list[str]
    warn_dimensions: list[str]
    improved_dimensions: list[str]
    hard_floor_breaches: list[str]
    decision: str  # 5 valori: AUTO_APPROVE|REVIEWER_HANDOFF|BLOCK_HARD_FLOOR|BLOCK_REGRESSION|SEVERELY_DEGRADED
    reason: str


@dataclass
class ReviewerVerdict:
    status: str  # APPROVED|REJECTED|PENDING|NOT_INVOKED
    reason: str
    invoked_at: Optional[str] = None
    block: bool = False


@dataclass
class EvidenceV2(Evidence):
    """Extension v1 → v2 — additive Optional fields only.

    v1 clients ignore these fields (CRITICAL-1 forward-compat from PR #241).
    """
    base_sha: Optional[str] = None
    baseline_scores: Optional[ScoreCard] = None
    current_scores: Optional[ScoreCard] = None
    deltas: Optional[dict[str, float]] = None
    regression_verdict: Optional[RegressionVerdict] = None
    reviewer_verdict: Optional[ReviewerVerdict] = None
    budget_snapshot_at: Optional[str] = None
    baseline_synthetic: bool = False
```

Aggiorna `evidence_from_json`:

```python
def evidence_from_json(raw: dict[str, Any]) -> Evidence:
    version = raw["schema_version"]
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(f"unsupported schema_version: {version}")

    # ... existing parsing for v1 fields ...

    # v2 extension (Optional, only if schema_version >= "2.0")
    if version >= "2.0":
        current_scores = ScoreCard(**_safe_kwargs(ScoreCard, raw.get("current_scores") or {})) if raw.get("current_scores") else None
        baseline_scores = ScoreCard(**_safe_kwargs(ScoreCard, raw.get("baseline_scores") or {})) if raw.get("baseline_scores") else None
        regression_verdict = RegressionVerdict(**_safe_kwargs(RegressionVerdict, raw.get("regression_verdict") or {})) if raw.get("regression_verdict") else None
        reviewer_verdict = ReviewerVerdict(**_safe_kwargs(ReviewerVerdict, raw.get("reviewer_verdict") or {})) if raw.get("reviewer_verdict") else None
        return EvidenceV2(
            # ... all v1 fields ...
            base_sha=raw.get("base_sha"),
            baseline_scores=baseline_scores,
            current_scores=current_scores,
            deltas=raw.get("deltas"),
            regression_verdict=regression_verdict,
            reviewer_verdict=reviewer_verdict,
            budget_snapshot_at=raw.get("budget_snapshot_at"),
            baseline_synthetic=raw.get("baseline_synthetic", False),
        )
    # v1.x — existing return path unchanged
    return Evidence(...)
```

### Step 4 — Esegui test (pass)

```bash
python3 -m pytest tests/test_review_evidence_schema_v2.py -v
```

**Output atteso:** 7 passed in <1s.

### Step 5 — Commit

```bash
git add lib/review_evidence/schema.py \
        tests/test_review_evidence_schema_v2.py \
        tests/fixtures/review-evidence/evidence_v2_clean.json \
        tests/fixtures/review-evidence/evidence_v2_with_unknown_fields.json
git commit -m "feat(review-evidence-v2): schema v2 dataclass + forward-compat (#task-01)"
```

## Criteri di accettazione

- [ ] 3 nuovi dataclass: `ScoreCard`, `RegressionVerdict` (5 decision values), `ReviewerVerdict`
- [ ] `EvidenceV2(Evidence)` extension con field Optional additive
- [ ] `schema_version="2.0"` supported + forward-compat 1.1+
- [ ] `_safe_kwargs` filtra campi sconosciuti (riusa PR #241 helper)
- [ ] 7 test passano
- [ ] v1 fixture esistente (`evidence_clean.json`) continua a deserialize correttamente
- [ ] No regression: full suite v1 (158/158) PASS
