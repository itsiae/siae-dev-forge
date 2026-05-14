"""Criterion 18 + Step 4b: Release genesis confirmation (feature branch list)."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional
from lib.release_risk.schema import CriterionResult, GenesisInfo

MERGE_COMMIT_LIMIT = 30
FEATURE_BRANCH_PATTERN = re.compile(
    r"Merge.+(?:branch '|pull request #\d+ from [^/]+/|remote-tracking branch ')"
    r"([^'\s]+)",
    re.I,
)


def extract_merge_commits(repo_root: Path, release_branch: str, target: str = "origin/main") -> list[dict]:
    """Returns list[{sha, subject, feature_branch}]. Empty se no merges."""
    try:
        out = subprocess.run(
            ["git", "log", f"{target}..origin/{release_branch}",
             "--merges", "--pretty=format:%H|%s", f"-n{MERGE_COMMIT_LIMIT}"],
            cwd=repo_root, capture_output=True, text=True, check=True, timeout=15,
        ).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []

    commits = []
    for line in out.splitlines():
        if "|" not in line:
            continue
        sha, subject = line.split("|", 1)
        m = FEATURE_BRANCH_PATTERN.search(subject)
        feature = m.group(1) if m else None
        commits.append({"sha": sha.strip(), "subject": subject.strip(), "feature_branch": feature})
    return commits


def evaluate_criterion_18(genesis: GenesisInfo) -> CriterionResult:
    """3-outcome handling from GenesisInfo state."""
    if genesis.no_merges_found:
        return CriterionResult(
            id=18, name="Unexpected feature in release", status="NO", weight=2,
            evidence=["release branch built linearly, no feature-branch merges"],
            source="genesis:no-merges",
        )
    if genesis.declined:
        return CriterionResult(
            id=18, name="Unexpected feature in release", status="REQUIRES_INPUT", weight=2,
            evidence=["user declined Step 4b genesis confirmation"],
            source="genesis:declined",
            notes="Genesis NOT confirmed by user — manual verification required pre-deploy",
        )
    if genesis.anomaly is True:
        return CriterionResult(
            id=18, name="Unexpected feature in release", status="YES", weight=2,
            evidence=[f"unexpected_features={genesis.unexpected}",
                      f"confirmed={genesis.user_confirmed}"],
            source="genesis:user-flag",
        )
    return CriterionResult(
        id=18, name="Unexpected feature in release", status="NO", weight=2,
        evidence=[f"all_features_confirmed={genesis.user_confirmed}"],
        source="genesis:user-confirm",
    )


def build_genesis_info(merge_commits: list[dict],
                       user_confirmed: Optional[list[str]] = None,
                       declined: bool = False) -> GenesisInfo:
    """Construct GenesisInfo da merge_commits + user response."""
    if not merge_commits:
        return GenesisInfo(merge_commits=[], no_merges_found=True)
    if declined:
        return GenesisInfo(merge_commits=merge_commits, declined=True)
    if user_confirmed is None:
        # Fallback: tutti i commit senza conferma utente esplicita
        return GenesisInfo(merge_commits=merge_commits, declined=True)

    all_features = [c["feature_branch"] for c in merge_commits if c["feature_branch"]]
    unexpected = [f for f in all_features if f not in user_confirmed]
    return GenesisInfo(
        merge_commits=merge_commits,
        user_confirmed=user_confirmed,
        unexpected=unexpected,
        anomaly=len(unexpected) > 0,
    )
