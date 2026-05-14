"""Criterion 16: Functional regression delta vs precedente release."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional
from lib.release_risk.schema import CriterionResult

COVERAGE_DELTA_THRESHOLD_PP = -2.0  # below this → trigger
TEST_DISABLED_PATTERN = re.compile(
    r"@Disabled|@Ignore|\.skip\(|\.xskip\(|xit\(|test\.skip|describe\.skip", re.I
)


def resolve_prev_release_main_sha(current_release_branch: str, repo_root: Path) -> Optional[str]:
    """Risolvi SHA del merge commit della precedente release in main.

    Returns None se primissima release (no precedenti).
    """
    try:
        # Step 1: trova ref precedente release
        ref_out = subprocess.run(
            ["git", "branch", "-r", "--sort=-committerdate"],
            cwd=repo_root, capture_output=True, text=True, check=True, timeout=10,
        ).stdout
        release_refs = [
            line.strip() for line in ref_out.splitlines()
            if "origin/release/" in line and current_release_branch not in line
        ]
        if not release_refs:
            return None
        prev_ref = release_refs[0]
        prev_name = prev_ref.replace("origin/", "", 1)

        # Step 2: trova merge commit in main matching uno dei 3 formati
        log_out = subprocess.run(
            ["git", "log", "origin/main", "--merges", "--pretty=format:%H %s"],
            cwd=repo_root, capture_output=True, text=True, check=True, timeout=15,
        ).stdout
        # Pattern flessibile: branch '<name>' | pull request #N from .../<name> | remote-tracking branch '<name>'
        merge_pattern = re.compile(
            rf"^([a-f0-9]+) Merge.+(branch '|pull request #\d+ from [^/]+/|remote-tracking branch ')"
            rf"{re.escape(prev_name)}"
        )
        for line in log_out.splitlines():
            m = merge_pattern.match(line)
            if m:
                return m.group(1)
        return None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def count_test_disabled_deleted(repo_root: Path, prev_sha: str) -> tuple[int, int]:
    """Count test disabled/deleted in diff prev_sha..HEAD. Returns (disabled, deleted)."""
    try:
        # Disabled: grep su content diff added lines (+)
        diff = subprocess.run(
            ["git", "diff", f"{prev_sha}...HEAD"],
            cwd=repo_root, capture_output=True, text=True, check=True, timeout=30,
        ).stdout
        added_lines = [l for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
        disabled_count = sum(1 for l in added_lines if TEST_DISABLED_PATTERN.search(l))

        # Deleted: git diff --diff-filter=D (file deletions)
        deleted_files = subprocess.run(
            ["git", "diff", "--diff-filter=D", "--name-only", f"{prev_sha}...HEAD"],
            cwd=repo_root, capture_output=True, text=True, check=True, timeout=10,
        ).stdout.splitlines()
        test_file_pattern = re.compile(r"(test|spec|__tests__|\.test\.|\.spec\.)", re.I)
        deleted_count = sum(1 for f in deleted_files if test_file_pattern.search(f))
        return (disabled_count, deleted_count)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return (0, 0)


def evaluate_criterion_16(
    repo_root: Path,
    current_release_branch: str,
    current_coverage_pct: Optional[float],
    baseline_fetcher=None,
) -> CriterionResult:
    """Criterion 16 main entry.

    Args:
        baseline_fetcher: callable (repo, sha) -> Optional[ScoreCard]. Iniettabile.

    Returns:
        CriterionResult weight=2.
    """
    prev_sha = resolve_prev_release_main_sha(current_release_branch, repo_root)
    if not prev_sha:
        return CriterionResult(
            id=16, name="Functional regression delta", status="TOOL_UNAVAILABLE",
            weight=2, evidence=["first release, no baseline available"],
            source="baseline_cache",
        )

    if baseline_fetcher is None:
        return CriterionResult(
            id=16, name="Functional regression delta", status="TOOL_UNAVAILABLE",
            weight=2, evidence=["baseline_fetcher not provided"],
            source="baseline_cache",
        )

    baseline = baseline_fetcher(prev_sha)
    coverage_delta = None
    if baseline and current_coverage_pct is not None:
        coverage_delta = current_coverage_pct - float(baseline.coverage)

    disabled_count, deleted_count = count_test_disabled_deleted(repo_root, prev_sha)

    trigger = (
        (coverage_delta is not None and coverage_delta < COVERAGE_DELTA_THRESHOLD_PP)
        or disabled_count > 0
        or deleted_count > 0
    )

    evidence = [
        f"prev_release_main_sha={prev_sha[:8]}",
        f"coverage_delta={coverage_delta:.2f}pp" if coverage_delta is not None else "coverage_delta=N/A",
        f"test_disabled_added={disabled_count}",
        f"test_deleted={deleted_count}",
    ]

    return CriterionResult(
        id=16, name="Functional regression delta",
        status="YES" if trigger else "NO", weight=2,
        evidence=evidence, source="baseline_cache",
    )
