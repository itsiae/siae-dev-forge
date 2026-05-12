"""Verify that every DEVFORGE_EVIDENCE_* env var referenced in code is
documented in hooks/ENV_VARS.md, and vice versa.

Also enforces presence of the Review Evidence Hook section / mentions in
CHANGELOG.md, .gitignore and README.md (doc-sync gate for task-15).
"""
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

EXPECTED_VARS = {
    "DEVFORGE_EVIDENCE_MIN_COVERAGE",
    "DEVFORGE_EVIDENCE_MAX_COVERAGE_DELTA",
    "DEVFORGE_EVIDENCE_MAX_LINT_ERRORS",
    "DEVFORGE_EVIDENCE_MAX_COMPLEXITY",
    "DEVFORGE_EVIDENCE_CI_SARIF_BLOCK_LEVEL",
    "DEVFORGE_EVIDENCE_SPEC_DRIFT_BLOCK",
    "DEVFORGE_EVIDENCE_DESIGN_DOC",
    "DEVFORGE_SKIP_EVIDENCE",
    "DEVFORGE_EVIDENCE_ICLOUD_WARN",
}


def test_env_vars_md_documents_all():
    content = (REPO_ROOT / "hooks" / "ENV_VARS.md").read_text()
    missing = []
    for v in EXPECTED_VARS:
        if v not in content:
            missing.append(v)
    assert not missing, f"Missing from ENV_VARS.md: {missing}"


def test_changelog_has_review_evidence_entry():
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text()
    assert "review-evidence" in changelog.lower() or "review evidence" in changelog.lower()


def test_gitignore_has_review_evidence_dir():
    gitignore = (REPO_ROOT / ".gitignore").read_text()
    assert ".claude/review-evidence/" in gitignore


def test_readme_has_review_evidence_section():
    readme = (REPO_ROOT / "README.md").read_text()
    assert "review-evidence" in readme.lower() or "Review Evidence" in readme
