# Task 10 — skill_adoption check (4-tier fallback signal)

**SP:** 1.5 · **AC mappati:** W4, C1, C7 · **Dipendenze:** Task 02 (scoring SkillAdoptionInput) · **Wave:** 3

## Goal

Implementare `lib/review_evidence/checks/skill_adoption.py` che rileva se il dev ha usato la skill chain DevForge (brainstorming → TDD → verification) tramite 4-tier fallback signal (W4 spec). Bot PR (Dependabot) skippa il check sempre (edge C1). Dev senza DevForge installato → score neutro 50 (no false negative).

## File coinvolti

**Creare:**
- `lib/review_evidence/checks/skill_adoption.py`
- `tests/test_review_evidence_skill_adoption.py`

## Step TDD

### Step 1 — Test

```python
"""Tests for skill_adoption check."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from lib.review_evidence.checks.skill_adoption import (
    detect_skill_adoption,
    SkillAdoptionResult,
)


def test_bot_pr_label_skips_check(tmp_path):
    """C1: label bot-pr → is_bot_pr=True, score=100."""
    result = detect_skill_adoption(
        repo_root=tmp_path,
        pr_open_time=datetime.now(timezone.utc),
        pr_labels=["bot-pr"],
        pr_user="ci-bot",
    )
    assert result.is_bot_pr is True
    # All other fields irrelevant on bot PR


def test_bot_user_dependabot(tmp_path):
    """C1 variant: user dependabot[bot] → is_bot_pr=True."""
    result = detect_skill_adoption(
        repo_root=tmp_path, pr_open_time=datetime.now(timezone.utc),
        pr_labels=[], pr_user="dependabot[bot]",
    )
    assert result.is_bot_pr is True


def test_brainstorming_signal_from_design_doc(tmp_path):
    """Tier 2: docs/plans/<topic>/overview.md modificato entro PR_OPEN-7d."""
    plans = tmp_path / "docs" / "plans" / "2026-05-13-test"
    plans.mkdir(parents=True)
    overview = plans / "overview.md"
    overview.write_text("# Test plan\nstatus: approved\n")
    
    result = detect_skill_adoption(
        repo_root=tmp_path,
        pr_open_time=datetime.now(timezone.utc),
        pr_labels=[], pr_user="lorenzo",
    )
    assert result.brainstorming_done is True


def test_no_signal_neutral_50(tmp_path):
    """W4 fallback: dev senza DevForge → score neutro 50, marker missing."""
    result = detect_skill_adoption(
        repo_root=tmp_path,
        pr_open_time=datetime.now(timezone.utc),
        pr_labels=[], pr_user="external-contributor",
    )
    assert result.discipline_signal_missing is True
    assert result.brainstorming_done is False
    assert result.tdd_cycle_seen is False
    assert result.verification_run is False


def test_tdd_signal_from_git_log(tmp_path):
    """Tier 3: git log --grep 'test:' returns >=1."""
    import subprocess as sp
    sp.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sp.run(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    sp.run(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    sp.run(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("x")
    sp.run(["git", "add", "."], cwd=tmp_path, check=True)
    sp.run(["git", "commit", "-m", "test: add foo"], cwd=tmp_path,
            check=True, capture_output=True)
    
    result = detect_skill_adoption(
        repo_root=tmp_path,
        pr_open_time=datetime.now(timezone.utc),
        pr_labels=[], pr_user="lorenzo",
    )
    assert result.tdd_cycle_seen is True


def test_activity_jsonl_signal(tmp_path, monkeypatch):
    """Tier 1: ~/.claude/projects/.../activity.jsonl con eventi skill."""
    fake_home = tmp_path / "home"
    activity_dir = fake_home / ".claude" / "projects" / "test-project" / "devforge-state"
    activity_dir.mkdir(parents=True)
    activity = activity_dir / "activity.jsonl"
    now = datetime.now(timezone.utc)
    line = json.dumps({
        "event": "brainstorming_done",
        "timestamp": now.isoformat(),
    })
    activity.write_text(line + "\n")
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("DEVFORGE_ACTIVITY_PROJECT", "test-project")
    
    result = detect_skill_adoption(
        repo_root=tmp_path,
        pr_open_time=now,
        pr_labels=[], pr_user="lorenzo",
    )
    assert result.brainstorming_done is True
```

### Step 2 — Implementa skill_adoption.py

```python
"""skill_adoption check — 4-tier fallback signal (W4 spec)."""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


@dataclass
class SkillAdoptionResult:
    is_bot_pr: bool = False
    brainstorming_done: bool = False
    tdd_cycle_seen: bool = False
    verification_run: bool = False
    discipline_signal_missing: bool = False


BOT_USER_PATTERNS = ("dependabot[bot]", "renovate[bot]", "github-actions[bot]")


def detect_skill_adoption(
    repo_root: Path,
    pr_open_time: datetime,
    pr_labels: list[str],
    pr_user: str,
) -> SkillAdoptionResult:
    """4-tier fallback:
    1. ~/.claude/projects/<project>/devforge-state/activity.jsonl
    2. docs/plans/<topic>/overview.md (within PR_OPEN -7d)
    3. git log --grep "test:" --since "<PR_OPEN -7d>"
    4. None → discipline_signal_missing=True (neutral 50)
    """
    # C1: bot PR skip
    if "bot-pr" in (pr_labels or []) or pr_user in BOT_USER_PATTERNS:
        return SkillAdoptionResult(is_bot_pr=True)
    
    result = SkillAdoptionResult()
    cutoff = pr_open_time - timedelta(days=7)
    
    # Tier 1: activity.jsonl
    if _activity_has_signal("brainstorming_done", cutoff):
        result.brainstorming_done = True
    if _activity_has_signal("tdd_cycle", cutoff):
        result.tdd_cycle_seen = True
    if _activity_has_signal("verification_run", cutoff):
        result.verification_run = True
    
    # Tier 2: design doc presence
    if not result.brainstorming_done:
        plans_dir = repo_root / "docs" / "plans"
        if plans_dir.exists():
            recent_overviews = [
                p for p in plans_dir.rglob("overview.md")
                if datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc) >= cutoff
            ]
            if recent_overviews:
                result.brainstorming_done = True
    
    # Tier 3: git log grep
    if not result.tdd_cycle_seen:
        try:
            p = subprocess.run(
                ["git", "log", "--grep", "test:", f"--since={cutoff.strftime('%Y-%m-%d')}",
                 "--oneline"],
                cwd=repo_root, capture_output=True, text=True, timeout=5, check=False,
            )
            if p.stdout.strip():
                result.tdd_cycle_seen = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    
    # Tier 4: none → marker
    if not any([result.brainstorming_done, result.tdd_cycle_seen, result.verification_run]):
        result.discipline_signal_missing = True
    
    return result


def _activity_has_signal(event_name: str, cutoff: datetime) -> bool:
    """Read ~/.claude/projects/<project>/devforge-state/activity.jsonl."""
    project = os.getenv("DEVFORGE_ACTIVITY_PROJECT", "")
    if not project:
        return False
    activity = Path(os.environ.get("HOME", "/")) / ".claude" / "projects" / project / "devforge-state" / "activity.jsonl"
    if not activity.exists():
        return False
    try:
        for line in activity.read_text().splitlines():
            if not line.strip():
                continue
            evt = json.loads(line)
            if evt.get("event") == event_name:
                ts = evt.get("timestamp", "")
                if ts and datetime.fromisoformat(ts.replace("Z", "+00:00")) >= cutoff:
                    return True
    except (json.JSONDecodeError, OSError):
        return False
    return False
```

### Step 3 — Run + commit

```bash
python3 -m pytest tests/test_review_evidence_skill_adoption.py -v
# 6 passed

git add lib/review_evidence/checks/skill_adoption.py \
        tests/test_review_evidence_skill_adoption.py
git commit -m "feat(review-evidence-v2): skill_adoption check 4-tier signal (#task-10)"
```

## Criteri di accettazione

- [ ] 4-tier fallback implementato (activity.jsonl → design doc → git log → neutral)
- [ ] **C1:** bot PR (label `bot-pr` o user `dependabot[bot]`) skip check → `is_bot_pr=True`
- [ ] **W4:** signal missing → `discipline_signal_missing=True`, neutral score (caller usa 50)
- [ ] 6 test PASS
- [ ] No regression v1
