"""Review-evidence orchestrator."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Self-bootstrap sys.path so this module works both as `pytest tests/` (root
# conftest injects REPO_ROOT) and as direct script invocation `python3 collector.py`
# from hooks/review-evidence (no parent process injects sys.path).
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.review_evidence.atomic_io import DiskFullError, write_evidence_atomic
from lib.review_evidence.registry import applicable
from lib.review_evidence.schema import SCHEMA_VERSION
from lib.review_evidence.thresholds import compute_verdict, load_thresholds

# Distinct exit codes so the hook can tell "disk full" from generic failure
# and fail-CLOSED on blocking triggers. E41 mitigation.
EXIT_OK = 0
EXIT_GENERIC = 1
EXIT_DISK_FULL = 2


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
        # MAJOR-3: propagate available/reason from per-stack records so
        # downstream consumers (renderer, verdict) can tell "no lint
        # findings" apart from "tool unavailable / config error".
        first_reason = next((l.get("reason") for l in lint_records if l.get("reason")), None)
        merged_lint: dict[str, Any] = {
            "errors": sum(l.get("errors", 0) for l in lint_records),
            "warnings": sum(l.get("warnings", 0) for l in lint_records),
            "findings": [f for l in lint_records for f in l.get("findings", [])],
            "source": ",".join(sorted({l.get("source", "local:unknown") for l in lint_records})),
            "available": all(l.get("available", True) for l in lint_records),
        }
        if first_reason is not None:
            merged_lint["reason"] = first_reason
        metrics["lint"] = merged_lint

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
    # MAJOR-2: hook detects iCloud cwd and forwards a human-readable warning
    # via env var so it surfaces in verdict.warnings without changing the
    # cli signature. Empty/unset means "no warning".
    extra_warnings: list[str] = []
    icloud_warn = os.environ.get("DEVFORGE_EVIDENCE_ICLOUD_WARNING", "").strip()
    if icloud_warn:
        extra_warnings.append(icloud_warn)
    verdict = compute_verdict(
        metrics, spec_drift=spec_drift, t=t, extra_warnings=extra_warnings
    )

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
    try:
        success, used_fallback, reason = write_evidence_atomic(
            out_path, content, sha=sha, repo_root=repo_root
        )
    except DiskFullError as e:
        # E41: explicit, distinct exit code so the bash hook can fail-CLOSED
        # on blocking triggers.
        sys.stderr.write(f"review-evidence: ENOSPC writing evidence ({e})\n")
        return EXIT_DISK_FULL
    if not success:
        return EXIT_GENERIC
    if used_fallback:
        sys.stderr.write(f"review-evidence: used fallback path ({reason})\n")
    return EXIT_OK


def orchestrate_v2(
    sha: str,
    base: str,
    dirty: bool,
    out_path: Path,
    repo_root: Path | None = None,
) -> int:
    """v2 orchestrator: scoring + runners + arch_drift + config (PR-B fully wired).

    Extends v1 ``orchestrate()`` with the scoring layer. PR-B wiring (fresh-eyes
    review iter 1 fix, post-task-15):

    - **Baseline cache**: try S3 (with local fallback) keyed by ``origin/main``
      HEAD SHA. ``baseline_scores=None`` → ``baseline_synthetic=True`` (first
      PR / fresh repo / force-push) drives the AUTO_APPROVE short-circuit in
      ``compute_regression_verdict``.
    - **Discipline via skill_adoption**: 4-tier fallback (activity.jsonl →
      design doc → git log --grep "test:" → neutral 50). Bot PRs short-circuit
      to discipline=100 (Edge C1).
    - **Regression verdict**: ``compute_regression_verdict`` is the single
      source of truth for decision branches (BLOCK_HARD_FLOOR / BLOCK_REGRESSION
      / REVIEWER_HANDOFF / AUTO_APPROVE). SEVERELY_DEGRADED is layered on top
      from ``compute_overall``'s degraded flag.

    Plan-review iter1 fixes (preserved):
    - IMPORTS espliciti al TOP della funzione (subprocess, asdict, datetime,
      timezone): mai ellipsis, niente reliance su import opzionali.
    - sec_score uses ``sec_runners_with_result`` counter to avoid false 100
      when security runners are applicable but all returned None (tool
      missing). Score stays None in that case → ``missing_components``.
    """
    import json as _json
    import subprocess
    from dataclasses import asdict
    from datetime import datetime, timezone

    from lib.review_evidence.atomic_io import write_evidence_atomic
    from lib.review_evidence.baseline_cache import fetch_baseline
    from lib.review_evidence.checks.arch_drift import detect_arch_drift
    from lib.review_evidence.checks.skill_adoption import detect_skill_adoption
    from lib.review_evidence.config import load_scores_config
    from lib.review_evidence.regression import compute_regression_verdict
    from lib.review_evidence.runners import applicable as runners_applicable
    from lib.review_evidence.schema import (
        SCHEMA_VERSION,
        RegressionVerdict,
        ScoreCard,
    )
    from lib.review_evidence.scoring import (
        ArchDriftInput,
        MutationFindings,
        SecurityFindings,
        SkillAdoptionInput,
        SpecDriftInput,
        compute_overall,
        score_discipline,
        score_security,
        score_spec_compliance,
    )

    repo_root = repo_root or Path.cwd()
    config = load_scores_config(repo_root)

    # ---- Security runners (aggregate findings + count successful runners) ----
    # ---- Mutation runner (first non-None advisory, v1.58+ opt-in) ----
    sec_findings = SecurityFindings()
    sec_runners_with_result = 0
    mutation_findings: MutationFindings | None = None
    applicable_runners = list(runners_applicable(repo_root))
    for runner in applicable_runners:
        try:
            result = runner.run(repo_root)
        except Exception:
            result = None
        if result is None:
            continue
        if isinstance(result, SecurityFindings):
            sec_findings.critical += result.critical
            sec_findings.high += result.high
            sec_findings.medium += result.medium
            sec_findings.low += result.low
            sec_runners_with_result += 1
        elif isinstance(result, MutationFindings) and mutation_findings is None:
            # First non-None wins (Java vs Python vs JS — typically only 1 stack).
            # E5 mitigation: multi-stack would otherwise mix incompatible scores.
            mutation_findings = result

    # sec_score = None if no runner produced a result (avoids false 100 when
    # tools are applicable but missing — plan-review iter1 fix).
    sec_score: float | None = (
        score_security(sec_findings) if sec_runners_with_result > 0 else None
    )
    qual_score: float | None = None  # PR-B: quality runners
    cov_score: float | None = None  # PR-B: coverage runner integration

    # ---- Spec drift (best-effort) ----
    try:
        from lib.review_evidence.spec_drift import detect_drift
        sd = detect_drift(repo_root=repo_root, base=base, head=sha)
        sd_input = (
            SpecDriftInput(unplanned_files=sd.get("unplanned_files", []))
            if sd else SpecDriftInput()
        )
    except Exception:
        sd_input = SpecDriftInput()

    # ---- Arch drift (changed files vs forbidden_paths) ----
    changed_files: list[str] = []
    try:
        p = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...{sha}"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        changed_files = [l.strip() for l in p.stdout.splitlines() if l.strip()]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    arch = detect_arch_drift(repo_root, changed_files)
    arch_input = ArchDriftInput(
        violations=[f"{v.file}:{v.import_}" for v in arch.violations]
    )

    spec_score = score_spec_compliance(sd_input, arch_input)

    # ---- Discipline via skill_adoption (W4, PR-B Task 10 wired) ----
    # 4-tier fallback: activity.jsonl → design doc → git log → neutral 50.
    # CI passes pr_open_time + pr_user via env; locally we fall back to "now"
    # + GITHUB_ACTOR or "local" so the call site stays deterministic.
    pr_open_time = datetime.now(timezone.utc)
    pr_user = os.environ.get("GITHUB_ACTOR", "local")
    adoption = detect_skill_adoption(
        repo_root=repo_root,
        pr_open_time=pr_open_time,
        pr_labels=[],  # PR labels not available at hook time; CI may extend
        pr_user=pr_user,
    )
    if adoption.discipline_signal_missing:
        # W4: no signal in any tier → neutral 50 (no false negative on non-DevForge devs)
        disc_score = 50.0
    else:
        disc_score = score_discipline(
            SkillAdoptionInput(
                is_bot_pr=adoption.is_bot_pr,
                brainstorming_done=adoption.brainstorming_done,
                tdd_cycle_seen=adoption.tdd_cycle_seen,
                verification_run=adoption.verification_run,
            )
        )

    scores = {
        "security": sec_score,
        "quality": qual_score,
        "coverage": cov_score,
        "spec_compliance": spec_score,
        "discipline": disc_score,
    }
    overall, degraded = compute_overall(scores, config.weights)
    missing = [k for k, v in scores.items() if v is None]

    scorecard = ScoreCard(
        security=sec_score if sec_score is not None else 0.0,
        quality=qual_score if qual_score is not None else 0.0,
        coverage=cov_score if cov_score is not None else 0.0,
        spec_compliance=spec_score if spec_score is not None else 0.0,
        discipline=disc_score,
        overall=overall,
        weights_used=dict(config.weights),
        missing_components=missing,
    )

    # ---- Baseline cache lookup (PR-B Task 09 wired) ----
    # REQ-DF-03: il base fornito dal chiamante ha PRECEDENZA su origin/main.
    # `origin/main` resta solo come ultimo fallback quando `base` non risolve
    # (es. repo locale senza quel ref) — evita drift di cache su branch aperti
    # verso un target diverso da main (es. sviluppo, release/*).
    main_sha = (
        _git(["rev-parse", base], repo_root)
        or _git(["rev-parse", "origin/main"], repo_root)
    )
    repo_full_name = os.environ.get("GITHUB_REPOSITORY", "local/unknown")
    baseline_scores: ScoreCard | None = None
    if main_sha:
        try:
            baseline_scores = fetch_baseline(repo_full_name, main_sha)
        except Exception:
            # Cache layer is non-fatal: treat any unexpected error as miss so
            # the regression check falls back to baseline_synthetic semantics.
            baseline_scores = None
    baseline_synthetic = baseline_scores is None

    # ---- Decision via regression analyzer (PR-B Task 11 wired) ----
    # SEVERELY_DEGRADED is reserved for the orchestrator (regression.py module
    # docstring): when compute_overall flags degraded (<2 dims available) OR
    # when any dim is missing (tooling absent → zero placeholder would
    # otherwise trip the hard-floor gate as a false positive).
    if degraded or missing:
        rv = RegressionVerdict(
            block_dimensions=[],
            warn_dimensions=[],
            improved_dimensions=[],
            hard_floor_breaches=[],
            decision="SEVERELY_DEGRADED",
            reason=(
                f"Severely degraded (missing dims: {missing or '<2 available'}). "
                "Fix tooling before re-run."
            ),
        )
    else:
        rv = compute_regression_verdict(
            current=scorecard,
            baseline=baseline_scores,
            cfg=config,
            baseline_synthetic=baseline_synthetic,
        )
    decision = rv.decision

    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root) or "unknown"
    evidence = {
        "schema_version": SCHEMA_VERSION,  # "2.0"
        "sha": sha,
        "branch": branch,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "dirty_tree": bool(dirty),
        "base_branch": base,
        "stack_detected": [r.name for r in applicable_runners],
        "metrics": {},  # v1 metrics filled by orchestrate(); v2 foundation skips
        "spec_drift": None,
        "verdict": {
            "block": decision.startswith("BLOCK"),
            "block_reasons": [rv.reason] if decision.startswith("BLOCK") else [],
            "warnings": [],
        },
        "current_scores": asdict(scorecard),
        "baseline_scores": asdict(baseline_scores) if baseline_scores else None,
        "deltas": None,
        "regression_verdict": asdict(rv),
        "reviewer_verdict": None,
        "budget_snapshot_at": None,
        "baseline_synthetic": baseline_synthetic,
        "mutation": asdict(mutation_findings) if mutation_findings else None,
    }

    content = _json.dumps(evidence, indent=2, default=str)
    try:
        success, used_fallback, reason = write_evidence_atomic(
            out_path, content, sha=sha, repo_root=repo_root
        )
    except DiskFullError as e:
        sys.stderr.write(f"review-evidence: ENOSPC writing evidence ({e})\n")
        return EXIT_DISK_FULL
    if not success:
        return EXIT_GENERIC
    if used_fallback:
        sys.stderr.write(f"review-evidence: used fallback path ({reason})\n")
    return EXIT_OK


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sha", required=True)
    p.add_argument("--base", required=True)
    p.add_argument("--dirty", default="0")
    p.add_argument("--out", required=True)
    args = p.parse_args()
    # Env-flag dispatch: when DEVFORGE_SCORING_V2_ENABLED=1, use the v2
    # orchestrator (ScoreCard + RegressionVerdict + baseline_synthetic).
    # Otherwise fall back to the v1 orchestrate() path. Task 14 wiring.
    if os.environ.get("DEVFORGE_SCORING_V2_ENABLED", "0") == "1":
        return orchestrate_v2(
            sha=args.sha, base=args.base, dirty=args.dirty == "1",
            out_path=Path(args.out),
        )
    return orchestrate(sha=args.sha, base=args.base, dirty=args.dirty == "1", out_path=Path(args.out))


if __name__ == "__main__":
    sys.exit(main())
