# Task 11 — Integration: test_phase2_decision_tree archetypal (5 fixtures)

**Status:** `[PENDING]`
**Depends on:** task-03, task-06, task-07
**Estimate:** 15 min
**Files:**
- `skills/code-coverage/scripts/tests/test_phase2_decision_tree.py` (NEW)

## Goal

Test end-to-end del decision tree v2 su 5 archetipi: clean vitest, legacy jest no-incompat (THE BUG-FIX), React Native (I1), monorepo misto, force-jest override (I10).

## Steps

### A. Create `test_phase2_decision_tree.py`

```python
"""End-to-end integration test for Phase 2 decision tree (Vitest-first v2).

5 archetypal fixtures verify the full chain:
  detect_jest_incompat.py -> jest-compat.json -> decision

Each fixture asserts the (framework, migrate, decision_reason) triplet.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "detect_jest_incompat.py"


def _detect(repo: Path) -> dict:
    r = subprocess.run(
        ["python3", str(SCRIPT), str(repo)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(r.stdout)


# ─── Archetype 1: clean Vitest project ────────────────────────────────

def test_archetype_clean_vitest(tmp_path):
    """No jest artifacts → vitest-default, migrate=false."""
    (tmp_path / "package.json").write_text(json.dumps({
        "name": "clean-vitest",
        "devDependencies": {"vitest": "^1.6.0", "@vitest/coverage-v8": "^1.6.0"},
        "scripts": {"test": "vitest run", "test:coverage": "vitest run --coverage"},
    }))
    out = _detect(tmp_path)
    ws = out["workspaces"]["."]
    assert ws["has_jest_artifacts"] is False
    assert ws["incompatibility_signals"] == []
    assert ws["decision"] == "vitest-default"
    assert ws["decision_reason"] == "vitest-first-default"


# ─── Archetype 2: legacy Jest, no incompat (THE BUG FIX) ──────────────

def test_archetype_legacy_jest_no_incompat_migrates(tmp_path):
    """jest.config + ts-jest + jest in scripts → vitest-migrate (NOT jest!).

    This is the regression test for the user-reported bug:
    'Se trova i jest ma la versione di VITEST non e' incompatibile, deve
     sempre fare i vitest e sostituire i jest con i vitest'
    """
    (tmp_path / "package.json").write_text(json.dumps({
        "name": "legacy-jest",
        "devDependencies": {
            "jest": "^29.7.0",
            "@types/jest": "^29.5.0",
            "ts-jest": "^29.1.0",
        },
        "scripts": {
            "test": "jest",
            "test:watch": "jest --watch",
            "test:coverage": "jest --coverage",
        },
    }))
    (tmp_path / "jest.config.js").write_text(
        "module.exports = {\n"
        "  preset: 'ts-jest',\n"
        "  testEnvironment: 'node',\n"
        "  moduleNameMapper: { '^@/(.*)$': '<rootDir>/src/$1' },\n"
        "};\n"
    )
    out = _detect(tmp_path)
    ws = out["workspaces"]["."]
    assert ws["has_jest_artifacts"] is True
    assert ws["incompatibility_signals"] == [], (
        f"BUG REGRESSION: legacy jest project triggered signals {ws['incompatibility_signals']}"
    )
    assert ws["decision"] == "vitest-migrate"
    assert ws["decision_reason"] == "jest-legacy-migrating-to-vitest"


# ─── Archetype 3: React Native (I1 fires) ──────────────────────────────

def test_archetype_react_native_keeps_jest(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "name": "rn-app",
        "dependencies": {"react-native": "0.74.0", "react": "18.2.0"},
        "devDependencies": {"jest": "^29", "jest-expo": "^50.0.0"},
        "scripts": {"test": "jest"},
    }))
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { preset: 'jest-expo' };"
    )
    out = _detect(tmp_path)
    ws = out["workspaces"]["."]
    assert "I1" in ws["incompatibility_signals"]
    assert ws["decision"] == "jest-incompat"
    assert ws["decision_reason"].startswith("hard-incompat:I1")


# ─── Archetype 4: monorepo (mixed RN + lib) ────────────────────────────

def test_archetype_monorepo_mixed(tmp_path):
    """Monorepo with 1 RN workspace + 1 vanilla lib workspace.
    RN keeps jest; lib migrates to vitest. Decision per-workspace."""
    (tmp_path / "package.json").write_text(json.dumps({
        "name": "mono", "private": True, "workspaces": ["packages/*"],
    }))
    rn = tmp_path / "packages" / "rn-app"
    rn.mkdir(parents=True)
    (rn / "package.json").write_text(json.dumps({
        "name": "@mono/rn",
        "dependencies": {"react-native": "0.74.0"},
        "devDependencies": {"jest": "^29"},
    }))
    lib = tmp_path / "packages" / "lib"
    lib.mkdir(parents=True)
    (lib / "package.json").write_text(json.dumps({
        "name": "@mono/lib",
        "devDependencies": {"jest": "^29", "ts-jest": "^29"},
        "scripts": {"test": "jest"},
    }))
    (lib / "jest.config.js").write_text(
        "module.exports = { testEnvironment: 'node' };"
    )
    out = _detect(tmp_path)
    rn_ws = out["workspaces"]["packages/rn-app"]
    lib_ws = out["workspaces"]["packages/lib"]
    assert rn_ws["decision"] == "jest-incompat"
    assert lib_ws["decision"] == "vitest-migrate"


# ─── Archetype 5: force-jest override (I10) ────────────────────────────

def test_archetype_force_jest_override(tmp_path):
    """User explicitly opts into Jest via overrides.json (I10)."""
    (tmp_path / "package.json").write_text(json.dumps({
        "name": "forced-jest",
        "devDependencies": {"vitest": "^1.6.0"},  # vitest already there
    }))
    (tmp_path / ".code-coverage").mkdir()
    (tmp_path / ".code-coverage" / "overrides.json").write_text(json.dumps({
        "force_jest": True,
        "force_jest_reason": "regulatory audit requires jest test runner certified",
    }))
    out = _detect(tmp_path)
    ws = out["workspaces"]["."]
    assert "I10" in ws["incompatibility_signals"]
    assert ws["decision"] == "jest-forced"
    assert "regulatory audit" in (ws["force_jest_reason"] or "")


# ─── Additional: validate_env.py delegate behaviour ────────────────────

def test_validate_env_delegates_to_jest_compat_migrate(tmp_path):
    """Integration: validate_env._detect_required_framework reads jest-compat.json."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from validate_env import _detect_required_framework

    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^29"}, "scripts": {"test": "jest"},
    }))
    (tmp_path / "jest.config.js").write_text("module.exports = {};")
    # Run Phase 2 detector first
    _detect(tmp_path)
    # validate_env should now return 'vitest' (migrate decision)
    assert _detect_required_framework(tmp_path) == "vitest"


def test_validate_env_delegates_to_jest_compat_incompat(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from validate_env import _detect_required_framework

    (tmp_path / "package.json").write_text(json.dumps({
        "dependencies": {"react-native": "0.74.0"},
        "devDependencies": {"jest": "^29"},
    }))
    _detect(tmp_path)
    assert _detect_required_framework(tmp_path) == "jest"
```

### B. Run

```bash
python3 -m pytest skills/code-coverage/scripts/tests/test_phase2_decision_tree.py -v
```

## Acceptance

- [ ] 7 archetypal/integration test pass (5 archetypal + 2 validate_env delegate)
- [ ] Archetype 2 (legacy jest no-incompat) is THE regression test del bug — passes
- [ ] Archetype 4 (monorepo) verifica per-workspace decisione
- [ ] Tutti i test sono subprocess-driven (no mocking)
