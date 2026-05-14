# Task 28 — cli.py entry point

**Stato:** [DONE]
**SP:** 1.5 Human / 0.5 Augmented
**Dipendenze:** task-22, task-24, task-26 + tutti i detector

## Goal

Implementare `lib/release_risk/cli.py` con argparse + entry point `python -m lib.release_risk assess`. Orchestrazione completa: read diff, invoke detector, build report, cache, write output.

## File coinvolti

- Create: `lib/release_risk/cli.py`
- Create: `lib/release_risk/__main__.py` (entry point modulo)

## Step

### Step 1 — Write __main__.py

Write `lib/release_risk/__main__.py`:
```python
"""Module entry point: python -m lib.release_risk <subcommand>."""
from lib.release_risk.cli import main
import sys
sys.exit(main())
```

### Step 2 — Write cli.py

Write `lib/release_risk/cli.py`:
```python
"""CLI entry: python -m lib.release_risk assess --branch X --service Y ..."""
import argparse
import os
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from lib.release_risk.schema import ReleaseRiskReport, GenesisInfo
from lib.release_risk.detector import (
    criterion_1_db_change, criterion_2_ocp_config, criterion_3_breaking_api,
    criterion_4_ext_deps, criterion_5_critical_service_stub, criterion_6_first_release,
    criterion_7_complex_rollback, criterion_8_downtime, criterion_9_data_migration,
    criterion_10_feature_flag, criterion_11_coverage_stub, criterion_12_e2e_tests,
    criterion_13_perf_tests, criterion_14_user_impact, criterion_15_files_count,
)
from lib.release_risk.kg_lookup import lookup_criticality, mcp_invoker_from_json_file
from lib.release_risk.coverage_src import get_coverage
from lib.release_risk.regression_delta import evaluate_criterion_16
from lib.release_risk.security_state import evaluate_criterion_17
from lib.release_risk.genesis import (
    extract_merge_commits, evaluate_criterion_18, build_genesis_info,
)
from lib.release_risk.scoring import compute_score
from lib.release_risk.cache import (
    compute_diff_hash, get as cache_get, put as cache_put, idempotency_marker,
)
from lib.release_risk.renderer import write_scorecard


def assess(args) -> int:
    repo_root = Path(args.repo_root).resolve()
    branch = args.branch
    service = args.service
    trigger = args.trigger

    # Read diff fixtures (passed by caller)
    diff_files = Path(args.diff_files).read_text().splitlines() if args.diff_files else []
    diff_content = Path(args.diff_content).read_text() if args.diff_content else ""

    # Compute diff hash + baseline
    diff_hash = compute_diff_hash(diff_files, diff_content)
    baseline_main_sha = _get_main_sha(repo_root)[:8] if _get_main_sha(repo_root) else "00000000"

    # Cache check
    if not args.no_cache:
        cached = cache_get(branch, diff_hash, baseline_main_sha)
        if cached:
            cached.cached = True
            print(json.dumps({"cached": True, "output_path": cached.output_path}))
            return 0

    # Identification
    identification = {
        "service": service,
        "version": args.version or "unknown",
        "owner": args.owner or "unknown",
        "date": args.release_date or datetime.now(timezone.utc).isoformat(),
        "jira_tickets": _extract_jira_tickets(repo_root, branch),
    }

    # Genesis
    merge_commits = extract_merge_commits(repo_root, branch)
    user_confirmed = args.genesis_confirmed.split(",") if args.genesis_confirmed else None
    declined = args.genesis_declined
    genesis = build_genesis_info(merge_commits, user_confirmed, declined)

    # Run all 18 criteria
    git_tag_count = _count_release_tags(repo_root)
    ci_present, e2e_found = _ci_config_check(repo_root)

    # ADR-2: load MCP sport-kg invoker da JSON prefetch (task-12b bridge)
    kg_data_path = Path(args.kg_data_file) if args.kg_data_file else None
    mcp_invoker = mcp_invoker_from_json_file(kg_data_path)

    cov_result = criterion_11_coverage_stub(
        coverage_src_fn=lambda sha: get_coverage(repo_root, sha),
        sha=_get_head_sha(repo_root),
    )
    c1 = criterion_1_db_change(diff_files, diff_content)
    c9 = criterion_9_data_migration(diff_files, diff_content)

    criteria = [
        c1,
        criterion_2_ocp_config(diff_files, diff_content),
        criterion_3_breaking_api(diff_files, diff_content),
        criterion_4_ext_deps(diff_files, diff_content),
        criterion_5_critical_service_stub(
            service,
            kg_lookup_fn=lambda name: lookup_criticality(name, mcp_invoker=mcp_invoker),
        ),
        criterion_6_first_release(git_tag_count),
        criterion_7_complex_rollback(c1.status, c9.status, diff_content),
        criterion_8_downtime(diff_content),
        c9,
        criterion_10_feature_flag(diff_content),
        cov_result,
        criterion_12_e2e_tests(ci_present, e2e_found),
        criterion_13_perf_tests(diff_content),
        criterion_14_user_impact(args.user_impact_ge_50 if args.user_impact_ge_50 is not None else None),
        criterion_15_files_count(diff_files),
        evaluate_criterion_16(repo_root, branch, _coverage_pct(cov_result),
                              baseline_fetcher=_baseline_fetcher_factory(service)),
        evaluate_criterion_17(repo_root),
        evaluate_criterion_18(genesis),
    ]

    # Score
    scorecard = compute_score(criteria)

    # Build report
    output_path = repo_root / "docs" / "releases" / f"{datetime.now().strftime('%Y-%m-%d')}-{service}-{branch.replace('/', '_')}.md"
    report = ReleaseRiskReport(
        service=service, release_branch=branch, target_branch="main",
        diff_hash=diff_hash, baseline_main_sha=baseline_main_sha,
        diff_summary={"files_changed": len(diff_files)},
        identification=identification, genesis=genesis,
        criteria=criteria, scorecard=scorecard,
        generated_at=datetime.now(timezone.utc).isoformat(),
        output_path=str(output_path), trigger=trigger,
    )

    # Write output + cache + emit event
    marker = idempotency_marker(diff_hash)
    write_scorecard(report, output_path, idempotency_marker=marker)
    cache_put(branch, diff_hash, baseline_main_sha, report)
    _emit_activity_event(report)

    print(json.dumps({
        "cached": False, "output_path": str(output_path),
        "level": scorecard.level, "decision": scorecard.decision,
        "score": scorecard.total_score, "diff_hash": diff_hash,
    }))
    return 0


def _get_main_sha(repo_root: Path) -> Optional[str]:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "origin/main"], cwd=repo_root, text=True, timeout=10
        ).strip()
    except Exception:
        return None


def _get_head_sha(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True, timeout=10
        ).strip()
    except Exception:
        return "unknown"


def _extract_jira_tickets(repo_root: Path, branch: str) -> list[str]:
    import re
    pattern = re.compile(r"\b(SPORT|DIRITTI|OASIS|POP|TAU)-\d+\b")
    try:
        out = subprocess.check_output(
            ["git", "log", f"origin/main..origin/{branch}", "--pretty=%B"],
            cwd=repo_root, text=True, timeout=15,
        )
        return list(set(pattern.findall(out)))
    except Exception:
        return []


def _count_release_tags(repo_root: Path) -> int:
    try:
        out = subprocess.check_output(
            ["git", "tag", "--list", "release*", "v*"], cwd=repo_root, text=True, timeout=5
        )
        return len([l for l in out.splitlines() if l.strip()])
    except Exception:
        return 0


def _ci_config_check(repo_root: Path) -> tuple[bool, bool]:
    workflows = repo_root / ".github" / "workflows"
    if not workflows.exists():
        return (False, False)
    e2e_found = False
    for f in workflows.glob("*.yml"):
        content = f.read_text()
        if any(kw in content.lower() for kw in ("e2e", "integration", "smoke")):
            e2e_found = True
            break
    return (True, e2e_found)


def _coverage_pct(cov_result) -> Optional[float]:
    for ev in cov_result.evidence:
        if ev.startswith("overall_pct="):
            try:
                return float(ev.split("=")[1])
            except Exception:
                return None
    return None


def _baseline_fetcher_factory(service: str):
    def fetcher(sha: str):
        try:
            from lib.review_evidence.baseline_cache import fetch_baseline
            return fetch_baseline(service, sha)
        except Exception:
            return None
    return fetcher


def _emit_activity_event(report: ReleaseRiskReport):
    """Emit via bash devforge_log subprocess (signature `<event> <status> <meta_json>`)."""
    meta = {
        "skill": "siae-release-risk",
        "service": report.service,
        "release_branch": report.release_branch,
        "level": report.scorecard.level,
        "decision": report.scorecard.decision,
        "score": report.scorecard.total_score,
        "score_max": 36,
        "partial": report.scorecard.partial,
        "diff_hash": report.diff_hash,
        "baseline_main_sha": report.baseline_main_sha,
        "cached": report.cached,
        "trigger": report.trigger,
    }
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if not plugin_root:
        return
    try:
        subprocess.run(
            ["bash", "-c",
             f"source '{plugin_root}/lib/logger.sh' && devforge_init_session 2>/dev/null && "
             f"devforge_log 'release-risk' 'success' '{json.dumps(meta)}'"],
            check=False, timeout=5,
        )
    except Exception:
        pass


def main():
    p = argparse.ArgumentParser(prog="lib.release_risk", description="Release Risk Assessment")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("assess", help="Run risk assessment")
    a.add_argument("--repo-root", required=True)
    a.add_argument("--branch", required=True, help="release branch (es. release/2.0.0)")
    a.add_argument("--service", required=True, help="service name (es. sport-x-service)")
    a.add_argument("--diff-files", help="path to file with diff filenames (one per line)")
    a.add_argument("--diff-content", help="path to file with full diff content")
    a.add_argument("--version")
    a.add_argument("--owner")
    a.add_argument("--release-date")
    a.add_argument("--user-impact-ge-50", type=lambda x: x.lower() in ("true", "1", "yes"),
                   default=None)
    a.add_argument("--genesis-confirmed", help="comma-separated feature branches confirmed")
    a.add_argument("--genesis-declined", action="store_true")
    a.add_argument("--trigger", choices=["pr-open", "manual", "cli"], default="cli")
    a.add_argument("--no-cache", action="store_true")
    a.add_argument("--kg-data-file",
                   help="Path to JSON pre-fetched MCP sport-kg output (SKILL.md Step 4c prefetch). "
                        "Senza questo, Criterion 5 ritorna REQUIRES_INPUT su repo KG-mappati.")
    args = p.parse_args()
    if args.cmd == "assess":
        return assess(args)
    return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

### Step 3 — Verifica

```bash
python3 -m lib.release_risk assess --help
```
Output atteso: argparse usage senza errori.

### Step 4 — Commit

```bash
git add lib/release_risk/cli.py lib/release_risk/__main__.py
git commit -m "feat(release-risk): cli entry point (assess subcommand) + activity event emit"
```

## Criteri di accettazione

- [ ] `python -m lib.release_risk assess --help` mostra usage
- [ ] Orchestrazione 18 criteri completa
- [ ] Activity event emit via subprocess `devforge_log`
- [ ] Cache check + write
- [ ] Jira ticket extraction da commit messages
- [ ] Commit eseguito
