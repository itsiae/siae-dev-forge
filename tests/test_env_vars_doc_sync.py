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
    "DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS",
    "DEVFORGE_EVIDENCE_ICLOUD_WARN",
    "DEVFORGE_EVIDENCE_COLLECTOR_PATH",
    "DEVFORGE_EVIDENCE_ICLOUD_WARNING",
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


def test_no_undocumented_devforge_evidence_env_var():
    """Grep code for DEVFORGE_EVIDENCE_* env var; every var must be both
    in EXPECTED_VARS and in hooks/ENV_VARS.md. Catches drift automatically
    so new env vars can't sneak in without doc + EXPECTED_VARS update.
    """
    import subprocess

    p = subprocess.run(
        [
            "grep",
            "-rhoE",
            "DEVFORGE_EVIDENCE_[A-Z_]+",
            "lib/review_evidence/",
            "hooks/",
            "tests/",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    found = set(p.stdout.split())
    real_vars = {v for v in found if v.startswith("DEVFORGE_EVIDENCE_")}

    missing_from_expected = real_vars - EXPECTED_VARS
    assert not missing_from_expected, (
        f"Env vars used in code but not in EXPECTED_VARS: {missing_from_expected}\n"
        "Add to tests/test_env_vars_doc_sync.py::EXPECTED_VARS and hooks/ENV_VARS.md"
    )

    env_vars_md = (REPO_ROOT / "hooks" / "ENV_VARS.md").read_text()
    missing_from_doc = {v for v in real_vars if v not in env_vars_md}
    assert not missing_from_doc, (
        f"Env vars used in code but not in hooks/ENV_VARS.md: {missing_from_doc}"
    )
