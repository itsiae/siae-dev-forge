# Task 04 — Collector framework orchestrator

**SP:** 2.0 · **AC mappati:** AC #2 + AC #6 + R3 · **Dipendenze:** Task 01, 02, 03 · **Wave:** 2

## Goal

Sostituire lo stub `lib/review_evidence/collector.py` (creato in Task 03) con l'orchestrator vero: stack detect, dispatch ai collector per-stack (registry-based, plug-in), invocazione ci_fetch + spec_drift, calcolo `verdict` da soglie env, atomic write.

## File coinvolti

**Modificare/sostituire:**
- `lib/review_evidence/collector.py` (sostituisce stub)

**Creare:**
- `lib/review_evidence/registry.py` (collector registry pattern)
- `lib/review_evidence/thresholds.py` (env var → soglie)
- `tests/test_review_evidence_orchestrator.py`
- `tests/test_review_evidence_thresholds.py`

## Step TDD

### Step 1 — Test thresholds

`tests/test_review_evidence_thresholds.py`:

```python
"""Tests for lib/review_evidence/thresholds.py — env-driven hard-block thresholds."""
import pytest
from lib.review_evidence.thresholds import (
    load_thresholds,
    compute_verdict,
    Thresholds,
)


def test_load_thresholds_defaults(monkeypatch):
    for v in [
        "DEVFORGE_EVIDENCE_MIN_COVERAGE",
        "DEVFORGE_EVIDENCE_MAX_COVERAGE_DELTA",
        "DEVFORGE_EVIDENCE_MAX_LINT_ERRORS",
        "DEVFORGE_EVIDENCE_MAX_COMPLEXITY",
        "DEVFORGE_EVIDENCE_CI_SARIF_BLOCK_LEVEL",
        "DEVFORGE_EVIDENCE_SPEC_DRIFT_BLOCK",
    ]:
        monkeypatch.delenv(v, raising=False)
    t = load_thresholds()
    assert t.min_coverage == 60.0
    assert t.max_coverage_delta == -5.0
    assert t.max_lint_errors == 0
    assert t.max_complexity == 15
    assert t.ci_sarif_block_level == "critical"
    assert t.spec_drift_block is True


def test_load_thresholds_env_override(monkeypatch):
    monkeypatch.setenv("DEVFORGE_EVIDENCE_MIN_COVERAGE", "75")
    monkeypatch.setenv("DEVFORGE_EVIDENCE_MAX_LINT_ERRORS", "3")
    monkeypatch.setenv("DEVFORGE_EVIDENCE_CI_SARIF_BLOCK_LEVEL", "off")
    t = load_thresholds()
    assert t.min_coverage == 75.0
    assert t.max_lint_errors == 3
    assert t.ci_sarif_block_level == "off"


def test_verdict_clean():
    t = Thresholds()
    metrics = {
        "coverage": {"overall_pct": 85.0, "delta_vs_base": 0.5},
        "lint": {"errors": 0, "warnings": 2},
        "complexity": {"max_cyclomatic": 8},
        "ci_quality": {"available": False, "problems_critical": 0, "problems_high": 0},
    }
    v = compute_verdict(metrics, spec_drift=None, t=t)
    assert v["block"] is False
    assert v["block_reasons"] == []


def test_verdict_coverage_block():
    t = Thresholds()
    metrics = {
        "coverage": {"overall_pct": 45.0, "delta_vs_base": -8.0},
        "lint": {"errors": 0, "warnings": 0},
        "complexity": {"max_cyclomatic": 5},
        "ci_quality": {"available": False, "problems_critical": 0, "problems_high": 0},
    }
    v = compute_verdict(metrics, spec_drift=None, t=t)
    assert v["block"] is True
    assert any("coverage" in r for r in v["block_reasons"])
    assert any("delta" in r for r in v["block_reasons"])


def test_verdict_lint_complexity_block():
    t = Thresholds()
    metrics = {
        "coverage": {"overall_pct": 80.0, "delta_vs_base": 0.0},
        "lint": {"errors": 5, "warnings": 0},
        "complexity": {"max_cyclomatic": 22},
        "ci_quality": {"available": False, "problems_critical": 0, "problems_high": 0},
    }
    v = compute_verdict(metrics, spec_drift=None, t=t)
    assert v["block"] is True
    assert any("lint_errors" in r for r in v["block_reasons"])
    assert any("complexity" in r for r in v["block_reasons"])


def test_verdict_ci_critical_block():
    t = Thresholds()
    metrics = {
        "coverage": {"overall_pct": 80.0, "delta_vs_base": 0.0},
        "lint": {"errors": 0, "warnings": 0},
        "complexity": {"max_cyclomatic": 5},
        "ci_quality": {"available": True, "problems_critical": 2, "problems_high": 0},
    }
    v = compute_verdict(metrics, spec_drift=None, t=t)
    assert v["block"] is True
    assert any("ci_critical" in r for r in v["block_reasons"])


def test_verdict_spec_drift_high_block():
    t = Thresholds()
    metrics = {
        "coverage": {"overall_pct": 80.0, "delta_vs_base": 0.0},
        "lint": {"errors": 0, "warnings": 0},
        "complexity": {"max_cyclomatic": 5},
        "ci_quality": {"available": False, "problems_critical": 0, "problems_high": 0},
    }
    drift = {"drift_severity": "high"}
    v = compute_verdict(metrics, spec_drift=drift, t=t)
    assert v["block"] is True
    assert any("drift" in r for r in v["block_reasons"])


def test_verdict_ci_block_level_off(monkeypatch):
    monkeypatch.setenv("DEVFORGE_EVIDENCE_CI_SARIF_BLOCK_LEVEL", "off")
    t = load_thresholds()
    metrics = {
        "coverage": {"overall_pct": 80.0, "delta_vs_base": 0.0},
        "lint": {"errors": 0, "warnings": 0},
        "complexity": {"max_cyclomatic": 5},
        "ci_quality": {"available": True, "problems_critical": 10, "problems_high": 50},
    }
    v = compute_verdict(metrics, spec_drift=None, t=t)
    assert v["block"] is False
```

### Step 2 — Implementa thresholds.py

```python
"""Env-driven hard-block thresholds for review-evidence."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Thresholds:
    min_coverage: float = 60.0
    max_coverage_delta: float = -5.0
    max_lint_errors: int = 0
    max_complexity: int = 15
    ci_sarif_block_level: str = "critical"  # critical | high | off
    spec_drift_block: bool = True


def load_thresholds() -> Thresholds:
    return Thresholds(
        min_coverage=float(os.environ.get("DEVFORGE_EVIDENCE_MIN_COVERAGE", "60")),
        max_coverage_delta=float(os.environ.get("DEVFORGE_EVIDENCE_MAX_COVERAGE_DELTA", "-5")),
        max_lint_errors=int(os.environ.get("DEVFORGE_EVIDENCE_MAX_LINT_ERRORS", "0")),
        max_complexity=int(os.environ.get("DEVFORGE_EVIDENCE_MAX_COMPLEXITY", "15")),
        ci_sarif_block_level=os.environ.get("DEVFORGE_EVIDENCE_CI_SARIF_BLOCK_LEVEL", "critical"),
        spec_drift_block=os.environ.get("DEVFORGE_EVIDENCE_SPEC_DRIFT_BLOCK", "1") == "1",
    )


def compute_verdict(metrics: dict, spec_drift: dict | None, t: Thresholds) -> dict:
    reasons: list[str] = []
    warnings: list[str] = []

    cov = metrics.get("coverage", {})
    if isinstance(cov, dict) and cov.get("overall_pct") is not None:
        if cov["overall_pct"] < t.min_coverage:
            reasons.append(f"coverage_below_threshold:{cov['overall_pct']}<{t.min_coverage}")
        if cov.get("delta_vs_base") is not None and cov["delta_vs_base"] < t.max_coverage_delta:
            reasons.append(f"coverage_delta:{cov['delta_vs_base']}<{t.max_coverage_delta}")

    lint = metrics.get("lint", {})
    if isinstance(lint, dict) and lint.get("errors", 0) > t.max_lint_errors:
        reasons.append(f"lint_errors:{lint['errors']}>{t.max_lint_errors}")

    cx = metrics.get("complexity", {})
    if isinstance(cx, dict) and cx.get("max_cyclomatic", 0) > t.max_complexity:
        reasons.append(f"complexity_max:{cx['max_cyclomatic']}>{t.max_complexity}")

    ci = metrics.get("ci_quality", {})
    if isinstance(ci, dict) and ci.get("available"):
        if t.ci_sarif_block_level == "critical" and ci.get("problems_critical", 0) > 0:
            reasons.append(f"ci_critical:{ci['problems_critical']}>0")
        elif t.ci_sarif_block_level == "high" and (
            ci.get("problems_critical", 0) > 0 or ci.get("problems_high", 0) > 0
        ):
            reasons.append(f"ci_high:critical={ci.get('problems_critical',0)},high={ci.get('problems_high',0)}")

    if spec_drift and t.spec_drift_block and spec_drift.get("drift_severity") == "high":
        reasons.append("drift_severity_high")

    return {"block": bool(reasons), "block_reasons": reasons, "warnings": warnings}
```

### Step 3 — Test orchestrator (registry + flow)

`tests/test_review_evidence_orchestrator.py`:

```python
"""Tests for collector orchestrator."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from lib.review_evidence.collector import orchestrate
from lib.review_evidence.registry import Collector, register, registry


class _FakeCollector(Collector):
    name = "fake"

    def is_applicable(self, repo_root):
        return True

    def collect(self, repo_root, base_ref, head_ref):
        return {
            "stack": "fake",
            "coverage": {"overall_pct": 90.0, "delta_vs_base": 0.0, "per_file": [], "source": "local:fake"},
            "lint": {"errors": 0, "warnings": 0, "findings": [], "source": "local:fake"},
            "complexity": {"max_cyclomatic": 3, "files_over_threshold": [], "source": "local:fake"},
        }


def test_orchestrate_writes_valid_evidence(tmp_path, monkeypatch):
    # Set _AUTOLOADED so autoload does not re-import real collectors and wipe our fake
    import lib.review_evidence.collector as _coll_mod
    _coll_mod._AUTOLOADED = True
    registry.clear()
    register(_FakeCollector())
    out = tmp_path / "ev.json"
    monkeypatch.chdir(tmp_path)
    # init a fake git repo
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)

    code = orchestrate(sha="abc", base="main", dirty=False, out_path=out, repo_root=tmp_path)
    assert code == 0
    data = json.loads(out.read_text())
    assert data["schema_version"] == "1.0"
    assert data["sha"] == "abc"
    assert "fake" in data["stack_detected"]
    assert data["metrics"]["coverage"]["overall_pct"] == 90.0
    assert data["verdict"]["block"] is False


def test_orchestrate_aggregates_block_verdict(tmp_path, monkeypatch):
    class _BadCollector(_FakeCollector):
        def collect(self, *a, **kw):
            d = super().collect(*a, **kw)
            d["lint"] = {"errors": 5, "warnings": 0, "findings": [], "source": "local:fake"}
            return d

    import lib.review_evidence.collector as _coll_mod
    _coll_mod._AUTOLOADED = True
    registry.clear()
    register(_BadCollector())
    out = tmp_path / "ev.json"
    monkeypatch.chdir(tmp_path)
    import subprocess
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)

    code = orchestrate(sha="def", base="main", dirty=False, out_path=out, repo_root=tmp_path)
    assert code == 0
    data = json.loads(out.read_text())
    assert data["verdict"]["block"] is True
    assert any("lint_errors" in r for r in data["verdict"]["block_reasons"])
```

### Step 4 — Implementa registry.py + collector.py

`lib/review_evidence/registry.py`:

```python
"""Plug-in registry for per-stack collectors."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class Collector(Protocol):
    name: str

    def is_applicable(self, repo_root: Path) -> bool: ...
    def collect(self, repo_root: Path, base_ref: str, head_ref: str) -> dict[str, Any]: ...


registry: list[Collector] = []


def register(collector: Collector) -> None:
    registry.append(collector)


def applicable(repo_root: Path) -> list[Collector]:
    return [c for c in registry if c.is_applicable(repo_root)]
```

`lib/review_evidence/collector.py` (sostituisce stub):

```python
"""Review-evidence orchestrator."""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.review_evidence.atomic_io import write_evidence_atomic
from lib.review_evidence.registry import applicable, register, registry
from lib.review_evidence.schema import SCHEMA_VERSION
from lib.review_evidence.thresholds import compute_verdict, load_thresholds


def _git(args: list[str], cwd: Path) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()
    except subprocess.CalledProcessError:
        return ""


_AUTOLOADED = False


def _autoload_collectors() -> None:
    """Import collectors lazily so plug-in modules self-register.

    Idempotent: runs at most once per process. We use a module-level flag
    (NOT `if registry: return`) so that tests can `registry.clear()` and
    insert a fake collector without triggering a re-autoload that would
    re-register the real ones (caught by plan-reviewer iter 1, F-Task04).
    """
    global _AUTOLOADED
    if _AUTOLOADED:
        return
    _AUTOLOADED = True
    try:
        from lib.review_evidence.collectors import python as _p  # noqa: F401
    except Exception:
        pass
    try:
        from lib.review_evidence.collectors import typescript as _t  # noqa: F401
    except Exception:
        pass
    try:
        from lib.review_evidence.collectors import java as _j  # noqa: F401
    except Exception:
        pass
    try:
        from lib.review_evidence.collectors import hcl as _h  # noqa: F401
    except Exception:
        pass


def _merge_metrics(stack_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-stack results. If multiple stacks, average coverage; concat findings."""
    if not stack_results:
        return {}
    metrics: dict[str, Any] = {"coverage": None, "lint": None, "complexity": None, "ci_quality": None}

    # Coverage: weighted simple average if multiple
    cov_records = [r["coverage"] for r in stack_results if r.get("coverage")]
    if cov_records:
        avg = sum(c["overall_pct"] for c in cov_records) / len(cov_records)
        delta_avg = sum(c.get("delta_vs_base", 0.0) for c in cov_records) / len(cov_records)
        per_file = [pf for c in cov_records for pf in c.get("per_file", [])]
        sources = sorted({c.get("source", "local:unknown") for c in cov_records})
        metrics["coverage"] = {"overall_pct": round(avg, 2), "delta_vs_base": round(delta_avg, 2),
                                "per_file": per_file, "source": ",".join(sources)}

    lint_records = [r["lint"] for r in stack_results if r.get("lint")]
    if lint_records:
        metrics["lint"] = {
            "errors": sum(l.get("errors", 0) for l in lint_records),
            "warnings": sum(l.get("warnings", 0) for l in lint_records),
            "findings": [f for l in lint_records for f in l.get("findings", [])],
            "source": ",".join(sorted({l.get("source", "local:unknown") for l in lint_records})),
        }

    cx_records = [r["complexity"] for r in stack_results if r.get("complexity")]
    if cx_records:
        metrics["complexity"] = {
            "max_cyclomatic": max(c.get("max_cyclomatic", 0) for c in cx_records),
            "files_over_threshold": [f for c in cx_records for f in c.get("files_over_threshold", [])],
            "source": ",".join(sorted({c.get("source", "local:unknown") for c in cx_records})),
        }

    return {k: v for k, v in metrics.items() if v is not None}


def orchestrate(sha: str, base: str, dirty: bool, out_path: Path, repo_root: Path | None = None) -> int:
    repo_root = repo_root or Path.cwd()
    _autoload_collectors()
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root) or "unknown"

    stack_results: list[dict[str, Any]] = []
    stack_detected: list[str] = []
    for c in applicable(repo_root):
        try:
            res = c.collect(repo_root, base, sha)
            stack_results.append(res)
            stack_detected.append(c.name)
        except Exception as e:
            # Non-fatal: emit collector failure as warning, continue
            stack_results.append({"stack": c.name, "_error": str(e)})

    metrics = _merge_metrics(stack_results)

    # Try to invoke optional ci_fetch + spec_drift modules (Task 10, 11)
    ci_quality = {"available": False, "ci_run_id": None, "problems_critical": 0, "problems_high": 0,
                  "findings": [], "source": None}
    try:
        from lib.review_evidence.ci_fetch import fetch_ci_sarif
        ci_quality = fetch_ci_sarif(sha=sha, repo_root=repo_root)
    except Exception:
        pass
    metrics["ci_quality"] = ci_quality

    spec_drift = None
    try:
        from lib.review_evidence.spec_drift import detect_drift
        spec_drift = detect_drift(repo_root=repo_root, base=base, head=sha)
    except Exception:
        pass

    t = load_thresholds()
    verdict = compute_verdict(metrics, spec_drift=spec_drift, t=t)

    evidence = {
        "schema_version": SCHEMA_VERSION,
        "sha": sha,
        "branch": branch,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "dirty_tree": bool(dirty),
        "base_branch": base,
        "stack_detected": stack_detected,
        "metrics": metrics,
        "spec_drift": spec_drift,
        "verdict": verdict,
    }
    import json as _json
    content = _json.dumps(evidence, indent=2, default=str)
    success, used_fallback, reason = write_evidence_atomic(out_path, content, sha=sha, repo_root=repo_root)
    if not success:
        return 1
    if used_fallback:
        sys.stderr.write(f"review-evidence: used fallback path ({reason})\n")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sha", required=True)
    p.add_argument("--base", required=True)
    p.add_argument("--dirty", default="0")
    p.add_argument("--out", required=True)
    args = p.parse_args()
    return orchestrate(sha=args.sha, base=args.base, dirty=args.dirty == "1", out_path=Path(args.out))


if __name__ == "__main__":
    sys.exit(main())
```

### Step 5 — Esegui test

```bash
pytest tests/test_review_evidence_thresholds.py tests/test_review_evidence_orchestrator.py -v
```

**Output atteso:** 8+2 = 10 test passano.

### Step 6 — Commit

```bash
git add lib/review_evidence/thresholds.py lib/review_evidence/registry.py \
        lib/review_evidence/collector.py \
        tests/test_review_evidence_thresholds.py \
        tests/test_review_evidence_orchestrator.py
git commit -m "feat(review-evidence): orchestrator + registry + thresholds (#task-04)"
```

## Criteri di accettazione

- [ ] `lib/review_evidence/thresholds.py` carica soglie da env con default corretti
- [ ] `compute_verdict()` produce reasons strutturati per ogni soglia violata
- [ ] `lib/review_evidence/registry.py` espone `register()`, `applicable()`, lista `registry`
- [ ] `lib/review_evidence/collector.py` orchestra detect+collect+merge+ci_fetch+spec_drift+verdict
- [ ] Stub collector di test passa e produce evidence valida vs schema
- [ ] Tutti i test (10) passano
