"""Test detect_jest_incompat.py — full signal coverage I1..I10 + decision tree.

All tests subprocess-driven against the script. No mocking.
"""
import json
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent.parent / "detect_jest_incompat.py"


def _run(repo: Path) -> dict:
    r = subprocess.run(
        ["python3", str(SCRIPT), str(repo)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(r.stdout)


# ─── Baseline: no jest / legacy jest no-incompat ────────────────────────

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


# ─── I1: React Native ─────────────────────────────────────────────────

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


# ─── I2: Vue CLI ──────────────────────────────────────────────────────

def test_I2_vue_cli_preset(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^27", "@vue/cli-plugin-unit-jest": "^4.5.0"},
    }))
    out = _run(tmp_path)
    assert "I2" in out["workspaces"]["."]["incompatibility_signals"]


def test_I2_does_not_fire_if_vite_present(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {
            "jest": "^29", "@vue/cli-plugin-unit-jest": "^4",
            "vite": "^5.0.0", "@vitejs/plugin-vue": "^5.0.0",
        },
    }))
    out = _run(tmp_path)
    assert "I2" not in out["workspaces"]["."]["incompatibility_signals"]


# ─── I3: Angular ──────────────────────────────────────────────────────

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


# ─── I4: Node < 18 ────────────────────────────────────────────────────

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


# ─── I5: Custom transformer ───────────────────────────────────────────

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
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^29", "ts-jest": "^29"},
    }))
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { transform: { '^.+\\\\.tsx?$': 'ts-jest' } };"
    )
    out = _run(tmp_path)
    assert "I5" not in out["workspaces"]["."]["incompatibility_signals"]


# ─── I6: Custom resolver ──────────────────────────────────────────────

def test_I6_custom_local_resolver(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "^29"}}))
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { resolver: './my-resolver.js' };"
    )
    out = _run(tmp_path)
    assert "I6" in out["workspaces"]["."]["incompatibility_signals"]


# ─── I7: ts-jest AST transformers ─────────────────────────────────────

def test_I7_ts_jest_ast_transformers(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^29", "ts-jest": "^29"},
    }))
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { globals: { 'ts-jest': { astTransformers: { before: ['x'] } } } };"
    )
    out = _run(tmp_path)
    assert "I7" in out["workspaces"]["."]["incompatibility_signals"]


# ─── I8: Custom testEnvironment ───────────────────────────────────────

def test_I8_custom_test_environment(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "^29"}}))
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { testEnvironment: './my-env.js' };"
    )
    out = _run(tmp_path)
    assert "I8" in out["workspaces"]["."]["incompatibility_signals"]


def test_I8_jsdom_safe(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "^29"}}))
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { testEnvironment: 'jsdom' };"
    )
    out = _run(tmp_path)
    assert "I8" not in out["workspaces"]["."]["incompatibility_signals"]


# ─── I9: Jest version < 27 ────────────────────────────────────────────

def test_I9_jest_version_below_27(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^26.6.0"},
    }))
    out = _run(tmp_path)
    assert "I9" in out["workspaces"]["."]["incompatibility_signals"]


def test_I9_jest_29_safe(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^29.0.0"},
    }))
    out = _run(tmp_path)
    assert "I9" not in out["workspaces"]["."]["incompatibility_signals"]


# ─── I10: User opt-out ────────────────────────────────────────────────

def test_I10_env_var_keep_jest(tmp_path, monkeypatch):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "^29"}}))
    monkeypatch.setenv("CC_KEEP_JEST", "1")
    out = _run(tmp_path)
    ws = out["workspaces"]["."]
    assert "I10" in ws["incompatibility_signals"]
    assert ws["decision"] == "jest-forced"


def test_I10_env_var_disable_migration(tmp_path, monkeypatch):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "^29"}}))
    monkeypatch.setenv("CC_DISABLE_JEST_MIGRATION", "1")
    out = _run(tmp_path)
    assert "I10" in out["workspaces"]["."]["incompatibility_signals"]


def test_I10_overrides_force_jest(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "^29"}}))
    (tmp_path / ".code-coverage").mkdir()
    (tmp_path / ".code-coverage" / "overrides.json").write_text(json.dumps({
        "force_jest": True, "force_jest_reason": "legacy CI",
    }))
    out = _run(tmp_path)
    ws = out["workspaces"]["."]
    assert "I10" in ws["incompatibility_signals"]
    assert ws["decision"] == "jest-forced"


# ─── Decision tree ────────────────────────────────────────────────────

def test_decision_jest_incompat_when_any_signal(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "dependencies": {"react-native": "0.74.0"},
        "devDependencies": {"jest": "^29"},
    }))
    out = _run(tmp_path)
    ws = out["workspaces"]["."]
    assert ws["decision"] == "jest-incompat"
    assert ws["decision_reason"].startswith("hard-incompat:I1")


# ─── Monorepo ──────────────────────────────────────────────────────────

def test_monorepo_per_workspace_decision(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "private": True, "workspaces": ["packages/*"],
    }))
    (tmp_path / "packages" / "rn-app").mkdir(parents=True)
    (tmp_path / "packages" / "rn-app" / "package.json").write_text(json.dumps({
        "name": "rn", "dependencies": {"react-native": "0.74.0"},
        "devDependencies": {"jest": "^29"},
    }))
    (tmp_path / "packages" / "lib").mkdir(parents=True)
    (tmp_path / "packages" / "lib" / "package.json").write_text(json.dumps({
        "name": "lib", "devDependencies": {"jest": "^29"}, "scripts": {"test": "jest"},
    }))
    (tmp_path / "packages" / "lib" / "jest.config.js").write_text("module.exports = {};")
    out = _run(tmp_path)
    assert out["workspaces"]["packages/rn-app"]["decision"] == "jest-incompat"
    assert out["workspaces"]["packages/lib"]["decision"] == "vitest-migrate"


def test_writes_jest_compat_json_file(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "^29"}}))
    _run(tmp_path)
    assert (tmp_path / ".code-coverage" / "jest-compat.json").is_file()


def test_output_includes_force_jest_reason(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "^29"}}))
    (tmp_path / ".code-coverage").mkdir()
    (tmp_path / ".code-coverage" / "overrides.json").write_text(json.dumps({
        "force_jest": True, "force_jest_reason": "regulatory audit",
    }))
    out = _run(tmp_path)
    assert "regulatory audit" in (out["workspaces"]["."]["force_jest_reason"] or "")
