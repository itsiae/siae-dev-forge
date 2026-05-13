"""Tests for agents/code-reviewer.md Step 0.6 (v2 scoring gatekeeper).

AC #12 + CRITICAL F1 contract tests:
- Step 0.6 section exists with Gatekeeper Logic
- 5 decision branch values enumerated explicitly
- Hard floor non-overridable rule explicit (F1)
- AUTO_APPROVE emits review summary advisory (W2 fix)
- BREAK-GLASS override path documented
"""
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]
CODE_REVIEWER = REPO_ROOT / "agents" / "code-reviewer.md"


def test_step_0_6_section_exists():
    content = CODE_REVIEWER.read_text()
    assert "Step 0.6" in content
    assert "Gatekeeper" in content or "gatekeeper" in content


def test_step_0_6_lists_5_decision_branch():
    """AC #12: 5 decision values explicit."""
    content = CODE_REVIEWER.read_text()
    for decision in [
        "AUTO_APPROVE",
        "REVIEWER_HANDOFF",
        "BLOCK_HARD_FLOOR",
        "BLOCK_REGRESSION",
        "SEVERELY_DEGRADED",
    ]:
        assert decision in content, f"Decision branch {decision} missing"


def test_step_0_6_hard_floor_non_overridable():
    """CRITICAL F1: reviewer can NEVER override hard floor."""
    content = CODE_REVIEWER.read_text()
    # Must explicitly state non-overridable
    assert re.search(
        r"NON[\s-]+overridable|cannot.*overrule|NEVER.*override",
        content,
        re.IGNORECASE,
    )


def test_step_0_6_auto_approve_advisory():
    """W2 fix: AUTO_APPROVE emit review summary anyway."""
    content = CODE_REVIEWER.read_text()
    assert "advisory" in content.lower()
    assert "summary" in content.lower()


def test_step_0_6_break_glass_documented():
    """Document admin BREAK-GLASS override path."""
    content = CODE_REVIEWER.read_text()
    assert "BREAK-GLASS" in content
