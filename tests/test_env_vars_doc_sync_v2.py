"""Verify ENV_VARS.md doc-sync per nuove env Review Evidence v2 (PR-A).

Extends `tests/test_env_vars_doc_sync.py` (v1 evidence env vars). Documenta
i 3 nuovi env var introdotti dalla foundation PR-A; le 4 env var PR-B
(`DEVFORGE_BASELINE_*`, `DEVFORGE_BREAK_GLASS_REGEX`) verranno aggiunte in
Task 15.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

V2_EXPECTED_VARS = {
    "DEVFORGE_SCORES_CONFIG_PATH",
    "DEVFORGE_ARCH_CONFIG_PATH",
    "DEVFORGE_SCORING_V2_ENABLED",
    # PR-B vars saranno aggiunte in Task 15
}


def test_env_vars_md_documents_v2():
    content = (REPO_ROOT / "hooks" / "ENV_VARS.md").read_text()
    missing = [v for v in V2_EXPECTED_VARS if v not in content]
    assert not missing, f"V2 env vars missing from ENV_VARS.md: {missing}"


def test_changelog_has_v1_55_entry():
    cl = (REPO_ROOT / "CHANGELOG.md").read_text()
    assert "v1.55.0" in cl
    assert "review-evidence v2" in cl.lower() or "scoring v2" in cl.lower()
