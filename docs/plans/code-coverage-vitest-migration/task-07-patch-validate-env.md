# Task 07 — Patch validate_env.py + regression test

**Status:** `[PENDING]`
**Depends on:** task-03 (detect_jest_incompat.py must exist)
**Estimate:** 12 min
**Files:**
- `skills/code-coverage/scripts/validate_env.py` (PATCH `_detect_required_framework` lines 117-151)
- `skills/code-coverage/scripts/tests/test_validate_env_ext.py` (EXTEND con regression test)

## Goal

Sostituire `_detect_required_framework` inline detection (lines 117-151) con delega a `.code-coverage/jest-compat.json`. Fallback a `vitest` se compat file assente.

## Steps

### A. Patch `validate_env.py`

Aprire `skills/code-coverage/scripts/validate_env.py`, individuare la funzione `_detect_required_framework` (linee 117-151). Sostituire con:

```python
def _detect_required_framework(repo_path: Path) -> str:
    """Infer the required test framework from repo manifest files.

    BUG-FIX (2026-05-28): per Principle 4 (Vitest-first), JS/TS projects with
    Jest artifacts are NO LONGER classified as 'jest' by mere presence. The
    Jest fallback is decided by Phase 2 via
    `assets/vitest-jest-compat.json` + `detect_jest_incompat.py`. This function
    reads the pre-computed `.code-coverage/jest-compat.json` and returns
    'jest' only when an incompatibility signal (I1..I10) fired OR user
    opted into Jest via overrides.json.
    """
    import json as _json
    pkg_json = _find_manifest_recursive(repo_path, "package.json")
    if pkg_json is not None:
        compat_path = repo_path / ".code-coverage" / "jest-compat.json"
        if compat_path.is_file():
            try:
                compat = _json.loads(compat_path.read_text(encoding="utf-8"))
                root = compat.get("workspaces", {}).get(".", {})
                decision = root.get("decision", "")
                if decision in ("jest-incompat", "jest-forced"):
                    return "jest"
                return "vitest"
            except (_json.JSONDecodeError, OSError):
                pass
        # Fallback: compat file absent (validate_env may run pre-Phase-2).
        # Honor overrides.json force_jest as last resort.
        overrides = repo_path / ".code-coverage" / "overrides.json"
        if overrides.is_file():
            try:
                ov = _json.loads(overrides.read_text(encoding="utf-8"))
                if ov.get("force_jest") is True and ov.get("force_jest_reason"):
                    return "jest"
            except (_json.JSONDecodeError, OSError):
                pass
        return "vitest"

    # (Existing non-JS branches preserved below — pyspark sniff etc.)
    # ... keep all the code AFTER the original JS branch unchanged ...
```

**CRITICO:** preservare il codice esistente per pyspark/python/java/etc. dopo il blocco JS. Solo il blocco JS (linee 119-150) viene sostituito.

### B. Regression test

Append a `scripts/tests/test_validate_env_ext.py`:

```python
def test_required_framework_vitest_when_jest_compat_migrate(tmp_path):
    """BUG-FIX regression: jest.config + scripts.test=jest -> NOT 'jest'."""
    from validate_env import _detect_required_framework
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^29"}, "scripts": {"test": "jest"},
    }))
    (tmp_path / "jest.config.js").write_text("module.exports = {};")
    # Simulate Phase 2 output
    (tmp_path / ".code-coverage").mkdir()
    (tmp_path / ".code-coverage" / "jest-compat.json").write_text(json.dumps({
        "version": "1.0.0",
        "workspaces": {".": {"decision": "vitest-migrate", "has_jest_artifacts": True,
                             "incompatibility_signals": []}},
    }))
    assert _detect_required_framework(tmp_path) == "vitest"


def test_required_framework_jest_when_jest_compat_incompat(tmp_path):
    from validate_env import _detect_required_framework
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "^29"}}))
    (tmp_path / ".code-coverage").mkdir()
    (tmp_path / ".code-coverage" / "jest-compat.json").write_text(json.dumps({
        "workspaces": {".": {"decision": "jest-incompat",
                             "incompatibility_signals": [{"signal": "I1"}]}},
    }))
    assert _detect_required_framework(tmp_path) == "jest"


def test_required_framework_jest_when_compat_forced(tmp_path):
    from validate_env import _detect_required_framework
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"vitest": "^1"}}))
    (tmp_path / ".code-coverage").mkdir()
    (tmp_path / ".code-coverage" / "jest-compat.json").write_text(json.dumps({
        "workspaces": {".": {"decision": "jest-forced"}},
    }))
    assert _detect_required_framework(tmp_path) == "jest"


def test_required_framework_vitest_when_compat_absent_fallback(tmp_path):
    """Pre-Phase-2 call: default to vitest."""
    from validate_env import _detect_required_framework
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^29"}, "scripts": {"test": "jest"},
    }))
    (tmp_path / "jest.config.js").write_text("module.exports = {};")
    assert _detect_required_framework(tmp_path) == "vitest"


def test_required_framework_jest_when_overrides_force_no_compat(tmp_path):
    from validate_env import _detect_required_framework
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "^29"}}))
    (tmp_path / ".code-coverage").mkdir()
    (tmp_path / ".code-coverage" / "overrides.json").write_text(json.dumps({
        "force_jest": True, "force_jest_reason": "compliance",
    }))
    assert _detect_required_framework(tmp_path) == "jest"
```

### C. Run

```bash
python3 -m pytest skills/code-coverage/scripts/tests/test_validate_env_ext.py -v
```

## Acceptance

- [ ] Funzione `_detect_required_framework` JS branch sostituita
- [ ] Non-JS branches (pyspark/python/java/etc.) preservate identiche
- [ ] 5 nuovi regression test pass
- [ ] Test esistenti in `test_validate_env_ext.py` ancora pass (no regression)
