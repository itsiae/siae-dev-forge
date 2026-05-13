"""skill_adoption check — 4-tier fallback signal (W4 spec).

Detects whether the PR author followed the DevForge skill chain
(brainstorming -> TDD -> verification) using a 4-tier fallback:

1. ``~/.claude/projects/<project>/devforge-state/activity.jsonl`` events
   (project name resolved via ``DEVFORGE_ACTIVITY_PROJECT``).
2. ``docs/plans/<topic>/overview.md`` modified within PR_OPEN - 7d.
3. ``git log --grep "test:" --since=<PR_OPEN -7d>`` returns >= 1 commit.
4. None of the above -> ``discipline_signal_missing=True`` (caller uses 50).

Edge C1: bot PRs (label ``bot-pr`` or user matching
``dependabot[bot]`` / ``renovate[bot]`` / ``github-actions[bot]``) skip
the check entirely, returning ``is_bot_pr=True`` with all other fields
left at their defaults.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional


@dataclass
class SkillAdoptionResult:
    """Outcome of the 4-tier skill-adoption probe."""

    is_bot_pr: bool = False
    brainstorming_done: bool = False
    tdd_cycle_seen: bool = False
    verification_run: bool = False
    discipline_signal_missing: bool = False


BOT_USER_PATTERNS = (
    "dependabot[bot]",
    "renovate[bot]",
    "github-actions[bot]",
)
BOT_LABEL = "bot-pr"

# Activity event names persisted by DevForge skills.
_EVENT_BRAINSTORMING = "brainstorming_done"
_EVENT_TDD = "tdd_cycle"
_EVENT_VERIFICATION = "verification_run"


def detect_skill_adoption(
    repo_root: Path,
    pr_open_time: datetime,
    pr_labels: Optional[Iterable[str]],
    pr_user: str,
) -> SkillAdoptionResult:
    """Return a SkillAdoptionResult populated via 4-tier fallback.

    Args:
        repo_root: Path to the repository checkout (used for Tier 2/3).
        pr_open_time: PR open timestamp (timezone-aware).
        pr_labels: Iterable of PR label names (may be ``None``).
        pr_user: GitHub login of the PR author.

    Notes:
        * Bot PRs short-circuit immediately with ``is_bot_pr=True``.
        * Any I/O or subprocess error is swallowed silently: the function
          must never raise, the caller relies on the marker fields to
          drive scoring.
    """
    labels = list(pr_labels or [])
    if BOT_LABEL in labels or pr_user in BOT_USER_PATTERNS:
        return SkillAdoptionResult(is_bot_pr=True)

    cutoff = pr_open_time - timedelta(days=7)
    result = SkillAdoptionResult()

    # Tier 1: activity.jsonl events.
    if _activity_has_signal(_EVENT_BRAINSTORMING, cutoff):
        result.brainstorming_done = True
    if _activity_has_signal(_EVENT_TDD, cutoff):
        result.tdd_cycle_seen = True
    if _activity_has_signal(_EVENT_VERIFICATION, cutoff):
        result.verification_run = True

    # Tier 2: design doc presence under docs/plans/<topic>/overview.md.
    if not result.brainstorming_done:
        if _design_doc_present(repo_root, cutoff):
            result.brainstorming_done = True

    # Tier 3: git log --grep "test:" since cutoff.
    if not result.tdd_cycle_seen:
        if _git_log_has_test_commit(repo_root, cutoff):
            result.tdd_cycle_seen = True

    # Tier 4: none -> mark missing (neutral 50 caller-side).
    if not (
        result.brainstorming_done
        or result.tdd_cycle_seen
        or result.verification_run
    ):
        result.discipline_signal_missing = True

    return result


def _activity_has_signal(event_name: str, cutoff: datetime) -> bool:
    """True iff ``activity.jsonl`` contains ``event_name`` >= ``cutoff``."""
    project = os.getenv("DEVFORGE_ACTIVITY_PROJECT", "")
    if not project:
        return False
    home = Path(os.environ.get("HOME", "/"))
    activity = (
        home
        / ".claude"
        / "projects"
        / project
        / "devforge-state"
        / "activity.jsonl"
    )
    if not activity.exists():
        return False
    try:
        for line in activity.read_text().splitlines():
            if not line.strip():
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue
            if evt.get("event") != event_name:
                continue
            ts = evt.get("timestamp", "")
            if not ts:
                continue
            try:
                parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                continue
            if parsed >= cutoff:
                return True
    except OSError:
        return False
    return False


def _design_doc_present(repo_root: Path, cutoff: datetime) -> bool:
    """True iff any ``docs/plans/*/overview.md`` was modified >= cutoff."""
    plans_dir = repo_root / "docs" / "plans"
    if not plans_dir.exists():
        return False
    try:
        for overview in plans_dir.rglob("overview.md"):
            try:
                mtime = datetime.fromtimestamp(
                    overview.stat().st_mtime, tz=timezone.utc
                )
            except OSError:
                continue
            if mtime >= cutoff:
                return True
    except OSError:
        return False
    return False


def _git_log_has_test_commit(repo_root: Path, cutoff: datetime) -> bool:
    """True iff ``git log --grep "test:"`` since cutoff returns >=1 commit."""
    try:
        proc = subprocess.run(
            [
                "git",
                "log",
                "--grep",
                "test:",
                f"--since={cutoff.strftime('%Y-%m-%d')}",
                "--oneline",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    return bool(proc.stdout.strip())
