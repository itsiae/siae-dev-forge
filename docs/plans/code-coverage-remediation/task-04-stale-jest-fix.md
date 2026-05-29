# Task 04 — Fix bug workspace-key + stale jest tag

**Goal:** Correggere il BUG reale in `validate_env.py` (legge il workspace hardcoded `"."` invece di `manifest_root` → causa-radice del doppio setup jest→vitest del post-mortem) e taggare `stale-config:` in `detect_jest_incompat.py` quando `jest.config.*` è presente ma `scripts.test` usa vitest. Risolve gap 6.8.

**WS:** WS-1 · **Dipendenze:** nessuna (isolato).

## File coinvolti
- Modifica: `skills/code-coverage/scripts/validate_env.py` (~riga 133: workspace key)
- Modifica: `skills/code-coverage/scripts/detect_jest_incompat.py` (`_detect_jest_artifacts`)
- Modifica: `skills/code-coverage/scripts/tests/test_validate_env_ext.py` + `test_detect_jest_incompat.py`

## Step TDD — Parte A: workspace key bug

### Step 1 — Test fallente
In `skills/code-coverage/scripts/tests/test_validate_env_ext.py` aggiungi:

```python
def test_resolves_framework_from_manifest_root(tmp_path):
    import validate_env
    cc = tmp_path / ".code-coverage"
    cc.mkdir()
    # decision jest è sul sub-workspace, NON su "."
    (cc / "stack.json").write_text('{"manifest_root": "modules/service/lambda-handler"}')
    (cc / "jest-compat.json").write_text(
        '{"workspaces": {"modules/service/lambda-handler": {"decision": "jest-incompat"}, ".": {"decision": "vitest"}}}'
    )
    (tmp_path / "modules" / "service" / "lambda-handler").mkdir(parents=True)
    (tmp_path / "modules" / "service" / "lambda-handler" / "package.json").write_text('{"name": "x"}')
    fw = validate_env._detect_required_framework(tmp_path)
    assert fw == "jest"  # deve leggere il workspace manifest_root, non "."
```

### Step 2 — Verifica che fallisce
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_validate_env_ext.py::test_resolves_framework_from_manifest_root -v`
Output atteso: FAILED — ritorna `"vitest"` (legge la chiave `"."`).

### Step 3 — Implementa
In `scripts/validate_env.py`, sostituisci (intorno a riga 133):
```python
                root = compat.get("workspaces", {}).get(".", {})
                decision = root.get("decision", "")
```
con:
```python
                ws_key = _read_manifest_root_rel(repo_path)
                ws = (compat.get("workspaces", {}).get(ws_key)
                      or compat.get("workspaces", {}).get(".", {}))
                decision = ws.get("decision", "")
```

Aggiungi (a livello modulo, vicino agli altri helper `_`):
```python
def _read_manifest_root_rel(repo_path):
    import json as _json
    stack = repo_path / ".code-coverage" / "stack.json"
    try:
        mr = _json.loads(stack.read_text(encoding="utf-8")).get("manifest_root", ".")
        return mr if isinstance(mr, str) and mr.strip() else "."
    except Exception:
        return "."
```

### Step 4 — Verifica che passa
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_validate_env_ext.py -v`
Output atteso: nuovo test `passed` + nessuna regressione.

## Step TDD — Parte B: stale jest tag

### Step 1 — Test fallente
In `skills/code-coverage/scripts/tests/test_detect_jest_incompat.py` aggiungi:

```python
def test_stale_jest_config_tagged(tmp_path):
    import detect_jest_incompat as d
    (tmp_path / "jest.config.ts").write_text("export default {}")
    (tmp_path / "package.json").write_text(
        '{"scripts": {"test": "vitest run"}, "devDependencies": {"vitest": "^2", "jest": "^29"}}'
    )
    has, artifacts = d._detect_jest_artifacts(tmp_path)
    assert any(a.startswith("stale-config:") for a in artifacts), artifacts
    # nessun artifact "config:" puro quando vitest è il runner attivo
    assert not any(a.startswith("config:") and not a.startswith("stale-config:") for a in artifacts)
```

### Step 2 — Verifica che fallisce
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_detect_jest_incompat.py::test_stale_jest_config_tagged -v`
Output atteso: FAILED (artifact `config:jest.config.ts` invece di `stale-config:`).

### Step 3 — Implementa
In `scripts/detect_jest_incompat.py`, dentro `_detect_jest_artifacts`, calcola i segnali e usa il prefisso `stale-config:` / `stale-deps:` quando vitest è il runner attivo:

```python
    pkg = _read_json(ws / "package.json")
    scripts = pkg.get("scripts") if isinstance(pkg.get("scripts"), dict) else {}
    test_script = str(scripts.get("test", "")) if scripts else ""
    all_deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
    vitest_active = ("vitest" in test_script) or any("vitest" in k for k in all_deps)

    cfg = _find_jest_config(ws)
    if cfg is not None:
        artifacts.append(f"stale-config:{cfg.name}:vitest-active" if vitest_active
                         else f"config:{cfg.name}")
    if "jest" in test_script and "vitest" not in test_script:
        artifacts.append(f"script:test='{test_script[:60]}'")
    jest_deps = [k for k in all_deps if k == "jest" or k.startswith("jest-")
                 or k in ("@types/jest", "ts-jest", "babel-jest", "@swc/jest", "@jest/globals")]
    if jest_deps:
        artifacts.append((f"stale-deps:{','.join(jest_deps[:5])}" if vitest_active
                          else f"deps:{','.join(jest_deps[:5])}"))
```
(Adatta ai nomi reali delle helper `_read_json` / `_find_jest_config` già presenti nel file — leggilo prima.) Mantieni la `decision` esistente: con vitest attivo deve restare `vitest`/`vitest-migrate`, mai `jest`.

### Step 4 — Verifica che passa
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_detect_jest_incompat.py scripts/tests/test_phase2_decision_tree.py -v`
Output atteso: tutti `passed`.

### Step 5 — Commit
```
git add skills/code-coverage/scripts/validate_env.py skills/code-coverage/scripts/detect_jest_incompat.py skills/code-coverage/scripts/tests/test_validate_env_ext.py skills/code-coverage/scripts/tests/test_detect_jest_incompat.py
git commit -m "fix(code-coverage): resolve framework from manifest_root workspace + tag stale jest config"
```

## Criteri di accettazione
- [ ] `_detect_required_framework` legge la chiave `manifest_root`, non `"."` (test verde).
- [ ] `jest.config.ts` + `scripts.test=vitest` → artifact `stale-config:` e decision NON `jest`.
- [ ] `test_phase2_decision_tree.py` continua a passare.
