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
        metrics["coverage"] = {
            "overall_pct": round(avg, 2),
            "delta_vs_base": round(delta_avg, 2),
            "per_file": per_file,
            "source": ",".join(sources),
        }

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
    ci_quality = {
        "available": False,
        "ci_run_id": None,
        "problems_critical": 0,
        "problems_high": 0,
        "findings": [],
        "source": None,
    }
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
