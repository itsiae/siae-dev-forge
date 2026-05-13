"""Tests for .devforge-scores.yml parser + validator (Task 06)."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lib.review_evidence.config import (
    ConfigValidationError,
    DevForgeScoresConfig,
    detect_config_change_in_pr,
    load_scores_config,
)

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_load_valid_config(tmp_path: Path) -> None:
    (tmp_path / ".devforge-scores.yml").write_text(
        (FIX / "devforge_scores_valid.yml").read_text()
    )
    cfg = load_scores_config(tmp_path)
    assert isinstance(cfg, DevForgeScoresConfig)
    assert cfg.weights["security"] == 0.30
    assert sum(cfg.weights.values()) == pytest.approx(1.0, abs=0.01)
    assert cfg.hard_floors["min_dim"] == 40
    assert cfg.hard_block_budget["security"] == -2
    assert cfg.warn_budget["coverage"] == -2
    assert "node_modules/" in cfg.ignore_paths


def test_load_missing_returns_defaults(tmp_path: Path) -> None:
    cfg = load_scores_config(tmp_path)
    assert cfg.weights["security"] == 0.30  # default
    assert cfg.hard_floors["overall"] == 55
    assert cfg.ignore_paths == []


def test_invalid_weights_sum_raises(tmp_path: Path) -> None:
    (tmp_path / ".devforge-scores.yml").write_text(
        (FIX / "devforge_scores_invalid_weights.yml").read_text()
    )
    with pytest.raises(ConfigValidationError, match="weights sum"):
        load_scores_config(tmp_path)


def test_detect_config_change_in_pr_require_override(tmp_path: Path) -> None:
    """B3 CRITICAL: config file change in PR diff = require override marker."""
    sp = subprocess
    sp.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sp.run(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    sp.run(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    sp.run(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / ".devforge-scores.yml").write_text(
        "schema_version: 1\nweights:\n  security: 1.0\n"
    )
    sp.run(["git", "add", "."], cwd=tmp_path, check=True)
    sp.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)

    # Modify config in second commit
    (tmp_path / ".devforge-scores.yml").write_text(
        "schema_version: 1\nweights:\n  security: 0.50\n  quality: 0.50\n"
    )
    sp.run(["git", "add", "."], cwd=tmp_path, check=True)
    sp.run(["git", "commit", "-m", "tamper"], cwd=tmp_path, check=True, capture_output=True)

    changed = detect_config_change_in_pr(tmp_path, base_sha="HEAD~1", head_sha="HEAD")
    assert changed is True
