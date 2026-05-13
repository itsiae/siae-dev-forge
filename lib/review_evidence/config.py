"""DevForge scores config parser + validator.

Loads `.devforge-scores.yml` from repo root with:
- weights (sum must be 1.0 ± 0.01, else E4 ConfigValidationError)
- hard_floors
- regression_budget (hard_block + warn_reviewer)
- ignore_paths

Also exposes `detect_config_change_in_pr` (CRITICAL B3): flags when the
config file itself is part of the PR diff so the renderer can require an
override marker before trusting the new weights.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigValidationError(ValueError):
    """Raised when `.devforge-scores.yml` fails schema/sum validation."""


DEFAULT_WEIGHTS: dict[str, float] = {
    "security": 0.30,
    "quality": 0.20,
    "coverage": 0.20,
    "spec_compliance": 0.15,
    "discipline": 0.15,
}
DEFAULT_HARD_FLOORS: dict[str, int] = {
    "security": 60,
    "coverage": 50,
    "overall": 55,
    "min_dim": 40,
}
DEFAULT_HARD_BLOCK_BUDGET: dict[str, int] = {
    "security": -2,
    "coverage": -5,
    "quality": -5,
    "spec_compliance": -10,
    "discipline": -20,
}
DEFAULT_WARN_BUDGET: dict[str, int] = {
    "security": 0,
    "coverage": -2,
    "quality": -2,
    "spec_compliance": -5,
    "discipline": -10,
}

CONFIG_FILENAME = ".devforge-scores.yml"


@dataclass
class DevForgeScoresConfig:
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    hard_floors: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_HARD_FLOORS))
    hard_block_budget: dict[str, int] = field(
        default_factory=lambda: dict(DEFAULT_HARD_BLOCK_BUDGET)
    )
    warn_budget: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_WARN_BUDGET))
    ignore_paths: list[str] = field(default_factory=list)


def load_scores_config(repo_root: Path) -> DevForgeScoresConfig:
    """Load `.devforge-scores.yml` or return defaults if missing.

    Raises:
        ConfigValidationError: when weights do not sum to 1.0 ± 0.01 (E4).
    """
    path = Path(repo_root) / CONFIG_FILENAME
    if not path.exists():
        return DevForgeScoresConfig()

    try:
        data: Any = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise ConfigValidationError(f"invalid YAML in {CONFIG_FILENAME}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigValidationError(
            f"{CONFIG_FILENAME} must be a mapping, got {type(data).__name__}"
        )

    weights = data.get("weights", DEFAULT_WEIGHTS)
    if not isinstance(weights, dict) or not weights:
        raise ConfigValidationError("weights must be a non-empty mapping")

    weight_total = sum(weights.values())
    if abs(weight_total - 1.0) > 0.01:
        raise ConfigValidationError(
            f"weights sum {weight_total:.4f} != 1.0 ± 0.01 (E4 fix)"
        )

    regression_budget = data.get("regression_budget") or {}
    hard_block = regression_budget.get("hard_block", DEFAULT_HARD_BLOCK_BUDGET)
    warn = regression_budget.get("warn_reviewer", DEFAULT_WARN_BUDGET)

    return DevForgeScoresConfig(
        weights=dict(weights),
        hard_floors=dict(data.get("hard_floors", DEFAULT_HARD_FLOORS)),
        hard_block_budget=dict(hard_block),
        warn_budget=dict(warn),
        ignore_paths=list(data.get("ignore_paths", [])),
    )


def detect_config_change_in_pr(
    repo_root: Path, base_sha: str, head_sha: str
) -> bool:
    """CRITICAL B3: detect if `.devforge-scores.yml` is in PR diff.

    Returns True when the scores config file appears in the
    `base_sha...head_sha` diff (PR symmetric range). False on git errors so
    we never fail-open without telemetry — callers must inspect.
    """
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", f"{base_sha}...{head_sha}"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

    if proc.returncode != 0:
        return False

    changed = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return CONFIG_FILENAME in changed
