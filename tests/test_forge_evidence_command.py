"""Tests for commands/forge-evidence.md command file."""
from pathlib import Path
import re

REPO_ROOT = Path(__file__).parent.parent
COMMAND = REPO_ROOT / "commands" / "forge-evidence.md"


def test_command_exists():
    assert COMMAND.exists()


def test_command_has_frontmatter():
    content = COMMAND.read_text()
    assert content.startswith("---")
    # Frontmatter must contain BOTH name AND description (repo convention,
    # cfr. commands/forge-*.md)
    assert re.search(r"^name:\s*forge-evidence\s*$", content, re.MULTILINE)
    assert re.search(r"^description:\s*.+", content, re.MULTILINE)


def test_command_invokes_review_evidence_hook():
    content = COMMAND.read_text()
    assert "review-evidence" in content
    assert ".claude/review-evidence/" in content


def test_command_documents_ci_lifecycle():
    content = COMMAND.read_text()
    # Must mention the gh pr create / gh pr edit pattern
    assert "gh pr create" in content
    assert "gh pr edit" in content
    assert "SARIF" in content or "CI quality" in content


def test_command_documents_toolfail_breakglass():
    """Lo skip discrezionale è rimosso; il comando documenta il breakglass tool-fail."""
    content = COMMAND.read_text()
    assert "DEVFORGE_SKIP_EVIDENCE" not in content, "vecchio skip discrezionale ancora documentato"
    assert (".devforge-evidence-toolfail" in content
            or "DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS" in content)
