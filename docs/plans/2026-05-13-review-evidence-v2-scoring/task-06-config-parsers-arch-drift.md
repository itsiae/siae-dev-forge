# Task 06 — Config parsers + arch_drift check

**SP:** 3.0 · **AC mappati:** AC #18, B3 (CRITICAL), W3 · **Dipendenze:** Task 01 · **Wave:** 1b

## Goal

Implementare 2 parser config:
1. `.devforge-scores.yml` — weights + hard_floors + regression_budget + ignore_paths
2. `.devforge-arch.yml` — forbidden_paths per arch_drift detection

E `arch_drift` check module che usa il secondo per detect violazioni.

CRITICAL B3: detect config file change in PR → require override marker.

## File coinvolti

**Creare:**
- `lib/review_evidence/config.py` (parser + validator)
- `lib/review_evidence/checks/__init__.py`
- `lib/review_evidence/checks/arch_drift.py`
- `tests/test_review_evidence_config.py`
- `tests/test_review_evidence_arch_drift.py`
- `tests/fixtures/review-evidence/devforge_scores_valid.yml`
- `tests/fixtures/review-evidence/devforge_scores_invalid_weights.yml`
- `tests/fixtures/review-evidence/devforge_arch.yml`

## Step TDD

### Step 1 — Fixtures

`devforge_scores_valid.yml`:

```yaml
schema_version: 1
weights:
  security: 0.30
  quality: 0.20
  coverage: 0.20
  spec_compliance: 0.15
  discipline: 0.15
hard_floors:
  security: 60
  coverage: 50
  overall: 55
  min_dim: 40
regression_budget:
  hard_block:
    security: -2
    coverage: -5
    quality: -5
    spec_compliance: -10
    discipline: -20
  warn_reviewer:
    security: 0
    coverage: -2
    quality: -2
    spec_compliance: -5
    discipline: -10
ignore_paths:
  - "node_modules/"
  - "**/*.gen.py"
```

`devforge_scores_invalid_weights.yml` (sum=0.5, deve fallire E4):

```yaml
schema_version: 1
weights:
  security: 0.30
  quality: 0.10
  coverage: 0.10
  spec_compliance: 0.0
  discipline: 0.0
```

`devforge_arch.yml`:

```yaml
schema_version: 1
forbidden_paths:
  - from: "src/api/"
    to: "src/db/"
    reason: "api must go through service layer"
  - from: "src/test/"
    to: "src/main/"
    reason: "test cannot bleed into prod"
```

### Step 2 — Test config parser

```python
"""Tests for .devforge-scores.yml parser + validator."""
import pytest
from pathlib import Path
from lib.review_evidence.config import (
    load_scores_config,
    DevForgeScoresConfig,
    ConfigValidationError,
    detect_config_change_in_pr,
)

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_load_valid_config(tmp_path):
    (tmp_path / ".devforge-scores.yml").write_text(
        (FIX / "devforge_scores_valid.yml").read_text()
    )
    cfg = load_scores_config(tmp_path)
    assert cfg.weights["security"] == 0.30
    assert sum(cfg.weights.values()) == pytest.approx(1.0, abs=0.01)
    assert cfg.hard_floors["min_dim"] == 40


def test_load_missing_returns_defaults(tmp_path):
    cfg = load_scores_config(tmp_path)
    assert cfg.weights["security"] == 0.30  # default
    assert cfg.hard_floors["overall"] == 55


def test_invalid_weights_sum_raises(tmp_path):
    (tmp_path / ".devforge-scores.yml").write_text(
        (FIX / "devforge_scores_invalid_weights.yml").read_text()
    )
    with pytest.raises(ConfigValidationError, match="weights sum"):
        load_scores_config(tmp_path)


def test_detect_config_change_in_pr_require_override(tmp_path):
    """B3 CRITICAL: config file change in PR diff = require override marker."""
    import subprocess as sp
    sp.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sp.run(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    sp.run(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    sp.run(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / ".devforge-scores.yml").write_text("schema_version: 1\nweights:\n  security: 0.30\n")
    sp.run(["git", "add", "."], cwd=tmp_path, check=True)
    sp.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    # Modify config
    (tmp_path / ".devforge-scores.yml").write_text("schema_version: 1\nweights:\n  security: 0.50\n")
    sp.run(["git", "add", "."], cwd=tmp_path, check=True)
    sp.run(["git", "commit", "-m", "tamper"], cwd=tmp_path, check=True, capture_output=True)

    changed = detect_config_change_in_pr(tmp_path, base_sha="HEAD~1", head_sha="HEAD")
    assert changed is True
```

### Step 3 — Test arch_drift

```python
"""Tests for arch_drift check (W3 spec)."""
from pathlib import Path
from lib.review_evidence.checks.arch_drift import detect_arch_drift, ArchDrift

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_no_arch_yml_no_violations(tmp_path):
    result = detect_arch_drift(tmp_path, changed_files=["src/api/handler.py"])
    assert result.violations == []
    assert result.rules_file_present is False


def test_forbidden_path_violation_detected(tmp_path):
    (tmp_path / ".devforge-arch.yml").write_text(
        (FIX / "devforge_arch.yml").read_text()
    )
    # Create file with forbidden import
    api_dir = tmp_path / "src" / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "handler.py").write_text("from src.db.connection import db\n")
    
    result = detect_arch_drift(tmp_path, changed_files=["src/api/handler.py"])
    assert len(result.violations) == 1
    assert result.rules_file_present is True


def test_allowed_path_no_violation(tmp_path):
    (tmp_path / ".devforge-arch.yml").write_text(
        (FIX / "devforge_arch.yml").read_text()
    )
    api_dir = tmp_path / "src" / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "handler.py").write_text("from src.service.user import service\n")
    
    result = detect_arch_drift(tmp_path, changed_files=["src/api/handler.py"])
    assert result.violations == []
```

### Step 4 — Implementa config.py

```python
"""DevForge scores config parser + validator."""
from __future__ import annotations
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigValidationError(ValueError):
    pass


DEFAULT_WEIGHTS = {"security": 0.30, "quality": 0.20, "coverage": 0.20,
                    "spec_compliance": 0.15, "discipline": 0.15}
DEFAULT_HARD_FLOORS = {"security": 60, "coverage": 50, "overall": 55, "min_dim": 40}
DEFAULT_HARD_BLOCK_BUDGET = {"security": -2, "coverage": -5, "quality": -5,
                              "spec_compliance": -10, "discipline": -20}
DEFAULT_WARN_BUDGET = {"security": 0, "coverage": -2, "quality": -2,
                        "spec_compliance": -5, "discipline": -10}


@dataclass
class DevForgeScoresConfig:
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    hard_floors: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_HARD_FLOORS))
    hard_block_budget: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_HARD_BLOCK_BUDGET))
    warn_budget: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_WARN_BUDGET))
    ignore_paths: list[str] = field(default_factory=list)


def load_scores_config(repo_root: Path) -> DevForgeScoresConfig:
    path = repo_root / ".devforge-scores.yml"
    if not path.exists():
        return DevForgeScoresConfig()
    data = yaml.safe_load(path.read_text())
    weights = data.get("weights", DEFAULT_WEIGHTS)
    if abs(sum(weights.values()) - 1.0) > 0.01:
        raise ConfigValidationError(
            f"weights sum {sum(weights.values())} != 1.0 ± 0.01 (E4 fix)"
        )
    return DevForgeScoresConfig(
        weights=weights,
        hard_floors=data.get("hard_floors", DEFAULT_HARD_FLOORS),
        hard_block_budget=data.get("regression_budget", {}).get("hard_block", DEFAULT_HARD_BLOCK_BUDGET),
        warn_budget=data.get("regression_budget", {}).get("warn_reviewer", DEFAULT_WARN_BUDGET),
        ignore_paths=data.get("ignore_paths", []),
    )


def detect_config_change_in_pr(repo_root: Path, base_sha: str, head_sha: str) -> bool:
    """B3 CRITICAL: detect if .devforge-scores.yml is in PR diff."""
    try:
        p = subprocess.run(
            ["git", "diff", "--name-only", f"{base_sha}...{head_sha}"],
            cwd=repo_root, capture_output=True, text=True, timeout=10, check=False,
        )
        changed = p.stdout.splitlines()
        return ".devforge-scores.yml" in changed
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
```

### Step 5 — Implementa arch_drift.py

```python
"""Arch drift detection — forbidden_paths cross-check."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ArchViolation:
    file: str
    import_: str
    rule_from: str
    rule_to: str
    reason: str


@dataclass
class ArchDrift:
    violations: list[ArchViolation] = field(default_factory=list)
    rules_file_present: bool = False


_PYTHON_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z0-9_.]+)", re.MULTILINE)


def _extract_imports(file_path: Path) -> list[str]:
    if not file_path.exists():
        return []
    try:
        content = file_path.read_text()
    except UnicodeDecodeError:
        return []
    if file_path.suffix == ".py":
        return [m.group(1).replace(".", "/") for m in _PYTHON_IMPORT_RE.finditer(content)]
    # TS/JS: basic regex
    if file_path.suffix in (".ts", ".tsx", ".js", ".jsx"):
        ts_re = re.compile(r"""(?:from|require)\s*\(?\s*['"]([^'"]+)['"]""")
        return ts_re.findall(content)
    return []


def detect_arch_drift(repo_root: Path, changed_files: list[str]) -> ArchDrift:
    rules_path = repo_root / ".devforge-arch.yml"
    if not rules_path.exists():
        return ArchDrift(violations=[], rules_file_present=False)
    
    try:
        rules = yaml.safe_load(rules_path.read_text()) or {}
    except yaml.YAMLError:
        return ArchDrift(violations=[], rules_file_present=False)
    
    violations: list[ArchViolation] = []
    for f in changed_files:
        from_rules = [r for r in rules.get("forbidden_paths", [])
                       if f.startswith(r["from"])]
        if not from_rules:
            continue
        imports = _extract_imports(repo_root / f)
        for rule in from_rules:
            to_clean = rule["to"].rstrip("/")
            for imp in imports:
                # BLOCK iter1 fix: anchored startswith to avoid false positive
                # (e.g. rule "src/db/" matching "src/database/x")
                if imp.startswith(to_clean + "/") or imp == to_clean:
                    violations.append(ArchViolation(
                        file=f, import_=imp,
                        rule_from=rule["from"], rule_to=rule["to"],
                        reason=rule.get("reason", "forbidden path"),
                    ))
    return ArchDrift(violations=violations, rules_file_present=True)
```

### Step 6 — Run + commit

```bash
python3 -m pytest tests/test_review_evidence_config.py \
                   tests/test_review_evidence_arch_drift.py -v
# 4 + 3 = 7 passed

git add lib/review_evidence/config.py \
        lib/review_evidence/checks/__init__.py \
        lib/review_evidence/checks/arch_drift.py \
        tests/test_review_evidence_config.py \
        tests/test_review_evidence_arch_drift.py \
        tests/fixtures/review-evidence/devforge_scores_valid.yml \
        tests/fixtures/review-evidence/devforge_scores_invalid_weights.yml \
        tests/fixtures/review-evidence/devforge_arch.yml
git commit -m "feat(review-evidence-v2): config parsers + arch_drift check (#task-06)"
```

## Criteri di accettazione

- [ ] `load_scores_config()` returns DevForgeScoresConfig con defaults
- [ ] Weights validation: sum ≈ 1.0 ± 0.01, fail else (E4)
- [ ] **CRITICAL B3:** `detect_config_change_in_pr()` rileva `.devforge-scores.yml` in diff
- [ ] `detect_arch_drift()` legge `.devforge-arch.yml`, parse Python + TS imports
- [ ] Missing arch_yml → 0 violations (no false positive)
- [ ] 7 test PASS
- [ ] No regression v1
