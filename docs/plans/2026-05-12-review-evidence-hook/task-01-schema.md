# Task 01 — Schema JSON v1 + dataclass + serialization

**SP:** 1.5 · **AC mappati:** AC #2 · **Dipendenze:** nessuna · **Wave:** 1

## Goal

Creare `lib/review_evidence/schema.py` con dataclass Python che rappresentano lo schema JSON v1 dell'evidence file, più funzioni di serializzazione/deserializzazione e validazione contro lo schema versioned.

## File coinvolti

**Creare:**
- `lib/review_evidence/__init__.py` (file vuoto, `# Review evidence framework`)
- `lib/review_evidence/schema.py`
- `tests/test_review_evidence_schema.py`
- `tests/fixtures/review-evidence/evidence_clean.json`
- `tests/fixtures/review-evidence/evidence_full_block.json`

## Step TDD

### Step 1 — Scrivi test fallente

Crea `tests/test_review_evidence_schema.py`:

```python
"""Tests for lib/review_evidence/schema.py — JSON schema v1."""
import json
from pathlib import Path

import pytest

from lib.review_evidence.schema import (
    Evidence,
    CoverageMetric,
    LintMetric,
    ComplexityMetric,
    CiQualityMetric,
    SpecDrift,
    Verdict,
    SCHEMA_VERSION,
    evidence_from_json,
    evidence_to_json,
)

FIXTURES = Path(__file__).parent / "fixtures" / "review-evidence"


def test_schema_version_is_1_0():
    assert SCHEMA_VERSION == "1.0"


def test_evidence_clean_roundtrip():
    raw = json.loads((FIXTURES / "evidence_clean.json").read_text())
    ev = evidence_from_json(raw)
    assert ev.sha == "abc123"
    assert ev.verdict.block is False
    assert ev.verdict.block_reasons == []
    assert ev.dirty_tree is False
    roundtrip = json.loads(evidence_to_json(ev))
    assert roundtrip == raw


def test_evidence_full_block_has_reasons():
    raw = json.loads((FIXTURES / "evidence_full_block.json").read_text())
    ev = evidence_from_json(raw)
    assert ev.verdict.block is True
    assert len(ev.verdict.block_reasons) >= 1
    assert ev.metrics["coverage"].overall_pct < 60.0


def test_missing_required_field_raises():
    with pytest.raises(KeyError):
        evidence_from_json({"sha": "abc"})  # manca schema_version


def test_unknown_schema_version_raises():
    bad = {"schema_version": "99.0", "sha": "x", "branch": "x", "computed_at": "x",
            "dirty_tree": False, "base_branch": "main", "stack_detected": [],
            "metrics": {}, "spec_drift": None, "verdict": {"block": False, "block_reasons": [], "warnings": []}}
    with pytest.raises(ValueError, match="unsupported schema_version"):
        evidence_from_json(bad)
```

Crea fixture `tests/fixtures/review-evidence/evidence_clean.json`:

```json
{
  "schema_version": "1.0",
  "sha": "abc123",
  "branch": "feature/x",
  "computed_at": "2026-05-12T16:00:00Z",
  "dirty_tree": false,
  "base_branch": "main",
  "stack_detected": ["python"],
  "metrics": {
    "coverage": {"overall_pct": 85.0, "delta_vs_base": 0.5, "per_file": [], "source": "local:coverage.py"},
    "lint": {"errors": 0, "warnings": 2, "findings": [], "source": "local:ruff"},
    "complexity": {"max_cyclomatic": 8, "files_over_threshold": [], "source": "local:radon"},
    "ci_quality": {"available": false, "ci_run_id": null, "problems_critical": 0, "problems_high": 0, "findings": [], "source": null}
  },
  "spec_drift": null,
  "verdict": {"block": false, "block_reasons": [], "warnings": []}
}
```

Crea fixture `tests/fixtures/review-evidence/evidence_full_block.json`:

```json
{
  "schema_version": "1.0",
  "sha": "def456",
  "branch": "feature/y",
  "computed_at": "2026-05-12T17:00:00Z",
  "dirty_tree": false,
  "base_branch": "main",
  "stack_detected": ["python"],
  "metrics": {
    "coverage": {"overall_pct": 45.0, "delta_vs_base": -8.0, "per_file": [], "source": "local:coverage.py"},
    "lint": {"errors": 5, "warnings": 12, "findings": [], "source": "local:ruff"},
    "complexity": {"max_cyclomatic": 22, "files_over_threshold": [], "source": "local:radon"},
    "ci_quality": {"available": true, "ci_run_id": "9876", "problems_critical": 3, "problems_high": 8, "findings": [], "source": "ci:sarif:qodana"}
  },
  "spec_drift": {"design_doc_path": "docs/plans/x-design.md", "files_in_plan": ["src/foo.py"], "files_changed": ["src/foo.py", "src/bar.py"], "unplanned_files": ["src/bar.py"], "drift_severity": "high"},
  "verdict": {"block": true, "block_reasons": ["coverage_below_threshold:45<60", "lint_errors:5>0", "complexity_max:22>15", "ci_critical:3>0", "drift_severity_high"], "warnings": []}
}
```

### Step 2 — Esegui e verifica che fallisce

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge"
pytest tests/test_review_evidence_schema.py -v
```

**Output atteso:** `ModuleNotFoundError: No module named 'lib.review_evidence'` (o ImportError equivalente).

### Step 3 — Implementa il codice minimo

Crea `lib/review_evidence/__init__.py` (vuoto, una sola riga commento).

Crea `lib/review_evidence/schema.py`:

```python
"""JSON schema v1 for review-evidence framework.

Dataclass + serialization. Versioned schema with explicit upgrade path.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

SCHEMA_VERSION = "1.0"
SUPPORTED_VERSIONS = {"1.0"}


@dataclass
class CoverageMetric:
    overall_pct: float
    delta_vs_base: float
    per_file: list[dict[str, Any]] = field(default_factory=list)
    source: str = "local:unknown"


@dataclass
class LintMetric:
    errors: int
    warnings: int
    findings: list[dict[str, Any]] = field(default_factory=list)
    source: str = "local:unknown"


@dataclass
class ComplexityMetric:
    max_cyclomatic: int
    files_over_threshold: list[dict[str, Any]] = field(default_factory=list)
    source: str = "local:unknown"


@dataclass
class CiQualityMetric:
    available: bool
    ci_run_id: Optional[str] = None
    problems_critical: int = 0
    problems_high: int = 0
    findings: list[dict[str, Any]] = field(default_factory=list)
    source: Optional[str] = None


@dataclass
class SpecDrift:
    design_doc_path: str
    files_in_plan: list[str]
    files_changed: list[str]
    unplanned_files: list[str]
    drift_severity: str  # none|low|medium|high


@dataclass
class Verdict:
    block: bool
    block_reasons: list[str]
    warnings: list[str]


@dataclass
class Evidence:
    sha: str
    branch: str
    computed_at: str
    dirty_tree: bool
    base_branch: str
    stack_detected: list[str]
    metrics: dict[str, Any]  # keys: coverage, lint, complexity, ci_quality
    spec_drift: Optional[SpecDrift]
    verdict: Verdict
    schema_version: str = SCHEMA_VERSION


def evidence_from_json(raw: dict[str, Any]) -> Evidence:
    version = raw["schema_version"]
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(f"unsupported schema_version: {version}")

    metrics = {}
    raw_metrics = raw.get("metrics", {})
    if "coverage" in raw_metrics:
        metrics["coverage"] = CoverageMetric(**raw_metrics["coverage"])
    if "lint" in raw_metrics:
        metrics["lint"] = LintMetric(**raw_metrics["lint"])
    if "complexity" in raw_metrics:
        metrics["complexity"] = ComplexityMetric(**raw_metrics["complexity"])
    if "ci_quality" in raw_metrics:
        metrics["ci_quality"] = CiQualityMetric(**raw_metrics["ci_quality"])

    spec_drift = None
    if raw.get("spec_drift"):
        spec_drift = SpecDrift(**raw["spec_drift"])

    return Evidence(
        schema_version=version,
        sha=raw["sha"],
        branch=raw["branch"],
        computed_at=raw["computed_at"],
        dirty_tree=raw["dirty_tree"],
        base_branch=raw["base_branch"],
        stack_detected=raw["stack_detected"],
        metrics=metrics,
        spec_drift=spec_drift,
        verdict=Verdict(**raw["verdict"]),
    )


def evidence_to_json(ev: Evidence) -> str:
    out: dict[str, Any] = {
        "schema_version": ev.schema_version,
        "sha": ev.sha,
        "branch": ev.branch,
        "computed_at": ev.computed_at,
        "dirty_tree": ev.dirty_tree,
        "base_branch": ev.base_branch,
        "stack_detected": ev.stack_detected,
        "metrics": {k: asdict(v) for k, v in ev.metrics.items()},
        "spec_drift": asdict(ev.spec_drift) if ev.spec_drift else None,
        "verdict": asdict(ev.verdict),
    }
    return json.dumps(out, indent=2, sort_keys=False)
```

Nota: il nome modulo è `lib/review_evidence/` (con dash) ma Python import vuole `review_evidence` (underscore). Risolvi creando un alias in `conftest.py` o spostando i sorgenti sotto `lib/review_evidence/`. Scelta: **usa underscore** per il modulo Python (`lib/review_evidence/`), mantieni docs/path coerenti. Aggiorna tutti i riferimenti in tasks successivi.

**File reali creati:**
- `lib/review_evidence/__init__.py`
- `lib/review_evidence/schema.py`

### Step 4 — Esegui e verifica che passa

```bash
pytest tests/test_review_evidence_schema.py -v
```

**Output atteso:** `5 passed in <1s`.

### Step 5 — Commit

```bash
git add lib/review_evidence/__init__.py lib/review_evidence/schema.py \
        tests/test_review_evidence_schema.py \
        tests/fixtures/review-evidence/evidence_clean.json \
        tests/fixtures/review-evidence/evidence_full_block.json
git commit -m "feat(review-evidence): add schema v1 dataclass + serialization (#task-01)"
```

## Criteri di accettazione

- [ ] `lib/review_evidence/schema.py` esiste e definisce `Evidence`, `CoverageMetric`, `LintMetric`, `ComplexityMetric`, `CiQualityMetric`, `SpecDrift`, `Verdict`, `SCHEMA_VERSION`
- [ ] `evidence_from_json` e `evidence_to_json` sono symmetric (roundtrip preserva il JSON)
- [ ] `evidence_from_json` solleva `ValueError` su `schema_version` non supportata
- [ ] 5 test passano in `tests/test_review_evidence_schema.py`
- [ ] 2 fixture JSON create (clean + full_block)
