# Task 03 — TDD red+green: detect signals I6-I10 + decision + monorepo + IMPL

**Status:** `[PENDING]`
**Depends on:** task-02
**Estimate:** 30 min
**Files:**
- `skills/code-coverage/scripts/tests/test_detect_jest_incompat.py` (EXTEND)
- `skills/code-coverage/scripts/detect_jest_incompat.py` (NEW)

## Goal

RED: aggiungere test per I6-I10 + decision tree edges + monorepo per-workspace.
GREEN: implementare `detect_jest_incompat.py` fino a far passare TUTTI i 14 test del task-02 + i nuovi.

## Steps

### A. Extend test file con I6-I10 + edge cases

Append a `test_detect_jest_incompat.py`:

```python
def test_I6_custom_local_resolver(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "^29"}}))
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { resolver: './my-resolver.js' };"
    )
    out = _run(tmp_path)
    assert "I6" in out["workspaces"]["."]["incompatibility_signals"]


def test_I7_ts_jest_ast_transformers(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^29", "ts-jest": "^29"},
    }))
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { globals: { 'ts-jest': { astTransformers: { before: ['x'] } } } };"
    )
    out = _run(tmp_path)
    assert "I7" in out["workspaces"]["."]["incompatibility_signals"]


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


def test_decision_jest_incompat_when_any_signal(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({
        "dependencies": {"react-native": "0.74.0"},
        "devDependencies": {"jest": "^29"},
    }))
    out = _run(tmp_path)
    ws = out["workspaces"]["."]
    assert ws["decision"] == "jest-incompat"
    assert ws["decision_reason"].startswith("hard-incompat:I1")


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
```

### B. Implement `scripts/detect_jest_incompat.py`

Lo script è già stato draftato nel design (parte del work iniziale). Lo script ha già la struttura corretta — riusarla. Vedi `scripts/detect_jest_incompat.py` esistente (NB: se non c'è, scriverlo da zero seguendo lo schema). Struttura chiave:

- `_evaluate_check(check, ws, repo_root)` — generico, dispatch su `kind` (package_dep_present, regex_in_jest_config, all_of, any_of, env_var, etc.)
- `_evaluate_signal(sig_def, ws, repo_root)` — wrap intorno a `_evaluate_check(sig_def["detect"], ws, repo_root)`
- `_enumerate_workspaces(repo_root)` — rglob package.json, skip dirs SKIP_DIRS
- `evaluate(repo_root)` — loop signals × workspaces, build decision

Decision logic:
```python
if "I10" in fired: decision = "jest-forced"
elif fired: decision = "jest-incompat"
elif has_artifacts: decision = "vitest-migrate"
else: decision = "vitest-default"
```

### C. Run tests

```bash
cd skills/code-coverage
python3 -m pytest scripts/tests/test_detect_jest_incompat.py -v
```

## Acceptance

- [ ] 28 test totali (14 task-02 + 14 nuovi)
- [ ] Tutti i test pass (GREEN)
- [ ] `scripts/detect_jest_incompat.py` autonomo (no side effects oltre a `.code-coverage/jest-compat.json` + stdout)
- [ ] Exit code 0 sempre (errors in JSON payload)
- [ ] Python 3.8+ compat (no walrus inappropriato, type hints `dict | None` ok perché `from __future__ import annotations`)
