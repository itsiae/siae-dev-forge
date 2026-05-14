"""Validation tests for stack-specific `.devforge-scores-*.yml` templates.

Each template ships in `docs/templates/` and must:
- Exist on disk
- Have `weights` summing to 1.0 ± 0.01
- Be loadable by `lib.review_evidence.config.load_scores_config`
- Provide stack-specific `ignore_paths`

Plus AWS-specific invariants (security dominant, tighter regression budget).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

# Ensure lib import works
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.review_evidence.config import load_scores_config  # noqa: E402

STACK_TEMPLATES = ["java", "python", "ios", "android", "aws"]


@pytest.mark.parametrize("stack", STACK_TEMPLATES)
def test_template_exists(stack):
    p = _REPO_ROOT / "docs" / "templates" / f".devforge-scores-{stack}.yml"
    assert p.exists(), f"Template missing: {p}"


@pytest.mark.parametrize("stack", STACK_TEMPLATES)
def test_template_weights_sum_to_one(stack):
    p = _REPO_ROOT / "docs" / "templates" / f".devforge-scores-{stack}.yml"
    data = yaml.safe_load(p.read_text())
    assert "weights" in data
    weights_sum = sum(data["weights"].values())
    assert abs(weights_sum - 1.0) <= 0.01, f"{stack} weights sum {weights_sum} != 1.0"


@pytest.mark.parametrize("stack", STACK_TEMPLATES)
def test_template_loads_via_config_parser(stack, tmp_path):
    # Copy template to fake repo_root as `.devforge-scores.yml`, load, verify no exception
    src = _REPO_ROOT / "docs" / "templates" / f".devforge-scores-{stack}.yml"
    dst = tmp_path / ".devforge-scores.yml"
    dst.write_text(src.read_text())
    cfg = load_scores_config(tmp_path)
    assert cfg.weights, f"{stack}: weights empty"
    assert all(
        k in cfg.weights
        for k in ("security", "quality", "coverage", "spec_compliance", "discipline")
    )
    assert all(
        k in cfg.hard_floors for k in ("security", "coverage", "overall", "min_dim")
    )


@pytest.mark.parametrize("stack", STACK_TEMPLATES)
def test_template_has_stack_specific_ignore_paths(stack):
    p = _REPO_ROOT / "docs" / "templates" / f".devforge-scores-{stack}.yml"
    data = yaml.safe_load(p.read_text())
    assert "ignore_paths" in data
    assert len(data["ignore_paths"]) > 0, f"{stack}: ignore_paths empty"


def test_aws_template_security_dominant():
    """AWS IaC = security CRITICAL, weight must be highest."""
    p = _REPO_ROOT / "docs" / "templates" / ".devforge-scores-aws.yml"
    data = yaml.safe_load(p.read_text())
    weights = data["weights"]
    assert weights["security"] == max(weights.values()), (
        "AWS template: security must be dominant weight"
    )
    assert weights["security"] >= 0.45, (
        "AWS security weight must be >=0.45 (IaC misconfig = breach risk)"
    )


def test_aws_template_tighter_regression_budget():
    """AWS security regression budget must be tighter than default (-2 -> -1)."""
    p = _REPO_ROOT / "docs" / "templates" / ".devforge-scores-aws.yml"
    data = yaml.safe_load(p.read_text())
    assert data["regression_budget"]["hard_block"]["security"] == -1
