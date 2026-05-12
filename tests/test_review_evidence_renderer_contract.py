"""Verifica che gli agent contengano la sezione Step 0.5 evidence-loading.

Contract test per Task 12 — Renderer integration in code-reviewer + spec-reviewer.
I file agent sono markdown puri: il test fa solo grep textuale per garantire
che le ancore strutturali della sezione Step 0.5 siano presenti.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CODE_REVIEWER = REPO_ROOT / "agents" / "code-reviewer.md"
SPEC_REVIEWER = REPO_ROOT / "agents" / "spec-reviewer.md"


def test_code_reviewer_has_step_0_5():
    content = CODE_REVIEWER.read_text()
    assert "Step 0.5" in content
    assert ".claude/review-evidence/" in content
    assert "evidence_from_json" in content or "verdict" in content
    assert "NON ricalcolare" in content or "non ricalcolare" in content.lower()


def test_code_reviewer_lists_source_field():
    content = CODE_REVIEWER.read_text()
    assert "source" in content
    assert "local:" in content or "ci:sarif:" in content


def test_code_reviewer_has_fallback_branch():
    content = CODE_REVIEWER.read_text()
    assert "evidence not pre-computed" in content
    assert "NON-DETERMINISTIC" in content


def test_spec_reviewer_has_spec_drift_section():
    content = SPEC_REVIEWER.read_text()
    assert "Step 0.5" in content
    assert "spec_drift" in content
    assert "drift_severity" in content


def test_spec_reviewer_has_fallback_branch():
    content = SPEC_REVIEWER.read_text()
    assert "evidence not pre-computed" in content
