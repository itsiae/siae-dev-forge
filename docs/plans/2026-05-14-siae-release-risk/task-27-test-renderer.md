# Task 27 — [TDD] test renderer snapshot 4 livelli

**Stato:** [PENDING]
**SP:** 1.5 Human / 0.5 Augmented
**Dipendenze:** task-26

## Goal

Snapshot test rendering markdown su 4 livelli LOW/MEDIUM/HIGH/CRITICAL + partial + suggested followup.

## File coinvolti

- Create: `tests/test_release_risk_renderer.py`

## Step

### Step 1 — Write test

Write `tests/test_release_risk_renderer.py`:
```python
import pytest
from lib.release_risk.renderer import render_scorecard, _criterion_emoji
from lib.release_risk.schema import (
    ReleaseRiskReport, ScoreCard, GenesisInfo, CriterionResult,
)


def _make_report(level, score, decision, criteria=None, partial=False, followups=None,
                 genesis=None):
    return ReleaseRiskReport(
        service="sport-test-service",
        release_branch="release/1.0.0",
        target_branch="main",
        diff_hash="abc123",
        baseline_main_sha="1a2b3c4d",
        diff_summary={"files_changed": 5},
        identification={"version": "1.0.0", "owner": "team-x"},
        genesis=genesis or GenesisInfo(merge_commits=[]),
        criteria=criteria or [],
        scorecard=ScoreCard(total_score=score, level=level, decision=decision,
                            decision_rationale="r",
                            suggested_followups=followups or [], partial=partial),
        generated_at="2026-05-14T10:00:00Z",
        output_path="docs/releases/2026-05-14-test.md",
    )


def test_render_low():
    r = _make_report("LOW", 2, "GO")
    md = render_scorecard(r)
    assert "🟢 Release Risk Scorecard" in md
    assert "Level: **LOW**" in md
    assert "Score: **2/36**" in md
    assert "Decision: **GO**" in md
    assert "GO deploy standard" in md


def test_render_medium_with_partial_warning():
    r = _make_report("MEDIUM", 7, "GO_WITH_MONITORING", partial=True)
    md = render_scorecard(r)
    assert "🟡" in md
    assert "PARTIAL SCORECARD" in md


def test_render_high():
    r = _make_report("HIGH", 12, "POSTPONE_WITHOUT_TL")
    md = render_scorecard(r)
    assert "🟠" in md
    assert "POSTPONE" in md
    assert "War room 4h" in md


def test_render_critical():
    r = _make_report("CRITICAL", 18, "NO_GO_WITHOUT_CAB")
    md = render_scorecard(r)
    assert "🔴" in md
    assert "CAB approval" in md
    assert "STOP" in md


def test_suggested_followup_block_rendered():
    r = _make_report("MEDIUM", 8, "GO_WITH_MONITORING", followups=["siae-security"])
    md = render_scorecard(r)
    assert "SUGGESTED FOLLOW-UP" in md
    assert "`siae-security`" in md


def test_idempotency_marker_first_line():
    r = _make_report("LOW", 0, "GO")
    md = render_scorecard(r, idempotency_marker="<!-- release-risk:abc123 -->")
    assert md.startswith("<!-- release-risk:abc123 -->")


def test_genesis_no_merges():
    gi = GenesisInfo(merge_commits=[], no_merges_found=True)
    r = _make_report("LOW", 0, "GO", genesis=gi)
    md = render_scorecard(r)
    assert "linearly" in md


def test_genesis_declined_warning():
    gi = GenesisInfo(merge_commits=[{"sha": "abc"}], declined=True)
    r = _make_report("LOW", 0, "GO", genesis=gi)
    md = render_scorecard(r)
    assert "Genesis NON confermato" in md


def test_emoji_positive_weight_yes_is_red_x():
    c = CriterionResult(id=1, name="DB", status="YES", weight=3)
    assert _criterion_emoji(c) == "❌"


def test_emoji_negative_weight_yes_is_green_check():
    c = CriterionResult(id=10, name="FF", status="YES", weight=-1)
    assert _criterion_emoji(c) == "✅"
```

### Step 2 — Esegui

```bash
pytest tests/test_release_risk_renderer.py -v
```
Output atteso: 10 PASSED.

### Step 3 — Commit

```bash
git add tests/test_release_risk_renderer.py
git commit -m "test(release-risk): renderer 4 livelli + partial + followup + genesis + emoji"
```

## Criteri di accettazione

- [ ] 10 test PASSED
- [ ] Snapshot 4 livelli
- [ ] Test inversione emoji per negative-weight
- [ ] Test idempotency marker
- [ ] Test genesis 2 outcome (no merges, declined)
- [ ] Commit eseguito
