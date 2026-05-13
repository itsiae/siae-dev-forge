"""Tests for forge-score command + doc-sync v2 final (Task 15 PR-B).

Contract test sui doc final PR-B:
- commands/forge-score.md exists + frontmatter valido
- README.md ha sezione v2 scoring
- CHANGELOG.md v1.55.0 contiene tutti i keyword PR-B
- Template `.devforge-scores.yml` exists
- JSON Schema valido + $schema draft-07
"""
from pathlib import Path
import json
import re

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_forge_score_command_exists():
    """forge-score.md exists + frontmatter (name + description + allowed-tools)."""
    p = REPO_ROOT / "commands" / "forge-score.md"
    assert p.exists(), f"missing {p}"
    content = p.read_text()
    assert content.startswith("---"), "frontmatter delimiter missing"
    assert re.search(r"^name:\s*forge-score\s*$", content, re.MULTILINE), (
        "name: forge-score frontmatter missing"
    )
    assert re.search(r"^description:\s*.+", content, re.MULTILINE), (
        "description frontmatter missing"
    )
    assert re.search(r"^allowed-tools:\s*.+", content, re.MULTILINE), (
        "allowed-tools frontmatter missing"
    )


def test_readme_has_v2_section():
    """README.md ha sezione 'Review Evidence v2' o 'v1.55'."""
    rm = REPO_ROOT / "README.md"
    content = rm.read_text()
    assert "Review Evidence v2" in content or "v1.55" in content, (
        "README.md missing Review Evidence v2 / v1.55 section"
    )


def test_changelog_pr_b_complete():
    """CHANGELOG.md v1.55.0 contiene tutti i keyword PR-B."""
    cl = (REPO_ROOT / "CHANGELOG.md").read_text()
    expected_keywords = [
        "baseline_cache",  # Task 09
        "skill_adoption",  # Task 10
        "regression",      # Task 11
        "forge-score",     # Task 15 (this task)
        "Terraform",       # Task 16
    ]
    missing = [kw for kw in expected_keywords if kw not in cl]
    assert not missing, f"Missing CHANGELOG PR-B keywords: {missing}"


def test_template_devforge_scores_exists():
    """`.devforge-scores.yml` template presente in docs/templates/."""
    p = REPO_ROOT / "docs" / "templates" / ".devforge-scores.yml"
    assert p.exists(), f"missing template {p}"
    content = p.read_text()
    # Sanity: weights + hard_floors + regression_budget keys presenti
    assert "weights:" in content, "template missing 'weights:' block"
    assert "hard_floors:" in content, "template missing 'hard_floors:' block"
    assert "regression_budget:" in content, "template missing 'regression_budget:' block"


def test_schema_devforge_scores_valid_json():
    """JSON Schema draft-07 valido + $schema URI corretto."""
    p = REPO_ROOT / "docs" / "schemas" / "devforge-scores.schema.json"
    assert p.exists(), f"missing schema {p}"
    data = json.loads(p.read_text())
    assert "$schema" in data, "JSON Schema missing $schema URI"
    assert "draft-07" in data["$schema"], (
        f"expected draft-07 schema, got {data['$schema']}"
    )
    # Top-level required keys per validare il template
    assert data.get("type") == "object", "schema root type must be object"
    assert "properties" in data, "schema missing properties"
    assert "weights" in data["properties"], "schema missing 'weights' property"
