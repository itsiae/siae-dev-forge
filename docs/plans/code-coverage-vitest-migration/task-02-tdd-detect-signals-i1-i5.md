# Task 02 — TDD red: detect_jest_incompat signals I1-I5

**Status:** `[PENDING]`
**Estimate:** 15 min
**Files:**
- `skills/code-coverage/scripts/tests/test_detect_jest_incompat.py` (NEW)

## Goal

RED phase TDD: scrivere test che falliscono per i signal I1 (react-native), I2 (vue-cli-jest), I3 (angular-jest), I4 (node<18), I5 (custom transformer). I test NON devono passare ora (script `detect_jest_incompat.py` non esiste).

## Steps

1. Creare `scripts/tests/test_detect_jest_incompat.py`:

```python
"""Test detect_jest_incompat.py — signals I1-I5."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "detect_jest_incompat.py"


def _run(repo: Path) -> dict:
    r = subprocess.run(
        ["python3", str(SCRIPT), str(repo)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(r.stdout)


def test_no_jest_no_signals_returns_vitest_default(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"vitest": "^1.0.0"},
    }))
    out = _run(tmp_path)
    ws = out["workspaces"]["."]
    assert ws["has_jest_artifacts"] is False
    assert ws["incompatibility_signals"] == []
    assert ws["decision"] == "vitest-default"


def test_legacy_jest_no_incompat_returns_vitest_migrate(tmp_path):
    """THE BUG FIX: jest.config.* alone does NOT force jest."""
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^29.0.0", "ts-jest": "^29.0.0"},
        "scripts": {"test": "jest"},
    }))
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { testEnvironment: 'node' };"
    )
    out = _run(tmp_path)
    ws = out["workspaces"]["."]
    assert ws["has_jest_artifacts"] is True
    assert ws["incompatibility_signals"] == []
    assert ws["decision"] == "vitest-migrate"


def test_I1_react_native_dep(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "dependencies": {"react-native": "0.74.0"},
        "devDependencies": {"jest": "^29.0.0"},
    }))
    out = _run(tmp_path)
    assert "I1" in out["workspaces"]["."]["incompatibility_signals"]


def test_I1_jest_expo_preset(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^29", "jest-expo": "^50.0.0"},
    }))
    out = _run(tmp_path)
    assert "I1" in out["workspaces"]["."]["incompatibility_signals"]


def test_I1_metro_config(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "^29"}}))
    (tmp_path / "metro.config.js").write_text("module.exports = {};")
    out = _run(tmp_path)
    assert "I1" in out["workspaces"]["."]["incompatibility_signals"]


def test_I2_vue_cli_preset(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^27", "@vue/cli-plugin-unit-jest": "^4.5.0"},
    }))
    out = _run(tmp_path)
    assert "I2" in out["workspaces"]["."]["incompatibility_signals"]


def test_I2_does_not_fire_if_vite_present(tmp_path):
    """Vue project with Vite + jest preset → not incompat (Vite available)."""
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {
            "jest": "^29", "@vue/cli-plugin-unit-jest": "^4",
            "vite": "^5.0.0", "@vitejs/plugin-vue": "^5.0.0",
        },
    }))
    out = _run(tmp_path)
    assert "I2" not in out["workspaces"]["."]["incompatibility_signals"]


def test_I3_angular_preset_no_analogjs(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^29", "jest-preset-angular": "^14.0.0"},
    }))
    out = _run(tmp_path)
    assert "I3" in out["workspaces"]["."]["incompatibility_signals"]


def test_I3_does_not_fire_with_analogjs(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {
            "jest": "^29", "jest-preset-angular": "^14",
            "@analogjs/vitest-angular": "^1.0.0",
        },
    }))
    out = _run(tmp_path)
    assert "I3" not in out["workspaces"]["."]["incompatibility_signals"]


def test_I4_engines_node_lt_18(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "engines": {"node": ">=16.0.0 <18.0.0"},
        "devDependencies": {"jest": "^29"},
    }))
    out = _run(tmp_path)
    assert "I4" in out["workspaces"]["."]["incompatibility_signals"]


def test_I4_nvmrc_lt_18(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^29"},
    }))
    (tmp_path / ".nvmrc").write_text("v16.20.0\n")
    out = _run(tmp_path)
    assert "I4" in out["workspaces"]["."]["incompatibility_signals"]


def test_I4_does_not_fire_at_18(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "engines": {"node": ">=18.0.0"},
        "devDependencies": {"jest": "^29"},
    }))
    out = _run(tmp_path)
    assert "I4" not in out["workspaces"]["."]["incompatibility_signals"]


def test_I5_custom_transformer_outside_allowlist(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^29"},
    }))
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { transform: { '^.+\\\\.tsx?$': './my-custom-transformer.js' } };"
    )
    out = _run(tmp_path)
    assert "I5" in out["workspaces"]["."]["incompatibility_signals"]


def test_I5_ts_jest_safe(tmp_path):
    """ts-jest is in allowlist → I5 does NOT fire."""
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^29", "ts-jest": "^29"},
    }))
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { transform: { '^.+\\\\.tsx?$': 'ts-jest' } };"
    )
    out = _run(tmp_path)
    assert "I5" not in out["workspaces"]["."]["incompatibility_signals"]
```

2. Run: `python3 -m pytest skills/code-coverage/scripts/tests/test_detect_jest_incompat.py -v` — expect ALL tests FAIL (script doesn't exist yet — `FileNotFoundError` or `ENOENT`).

## Acceptance

- [ ] 14 test definiti
- [ ] Tutti i test fallano (RED) — atteso perché lo script non esiste
- [ ] Nessun test usa mock — solo subprocess + tmp_path filesystem
