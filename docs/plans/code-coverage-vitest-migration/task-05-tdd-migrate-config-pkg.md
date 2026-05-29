# Task 05 — TDD red+green: migrate jest config translation + package.json rewrite + setup rename

**Status:** `[PENDING]`
**Depends on:** task-04
**Estimate:** 25 min
**Files:**
- `skills/code-coverage/scripts/tests/test_migrate_jest_to_vitest.py` (EXTEND)
- `skills/code-coverage/scripts/migrate_jest_to_vitest.py` (EXTEND)

## Goal

Aggiungere a migrate:
- `translate_jest_config_to_vitest(jest_cfg_path, ws_dir) -> tuple[str, list[str]]`: legge jest.config.* via regex/JSON, emette content `vitest.config.ts` + lista unmapped_keys (per chiavi in `config_keys_manual_review`).
- `rewrite_package_json(pkg_path) -> dict`: sostituisce script `jest` → `vitest run`, rimuove jest-deps, aggiunge vitest-deps, strip top-level `jest` key.
- `rename_setup_files(ws_dir) -> list[str]`: rinomina `jest.setup.*` → `vitest.setup.ts`, applica codemod_text dentro.

## Steps

### A. Tests

Append a `test_migrate_jest_to_vitest.py`:

```python
def test_translate_jest_config_basic_node_env(tmp_path):
    from migrate_jest_to_vitest import translate_jest_config_to_vitest
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { testEnvironment: 'node' };"
    )
    content, unmapped = translate_jest_config_to_vitest(
        tmp_path / "jest.config.js", tmp_path
    )
    assert "defineConfig" in content
    assert "environment: 'node'" in content
    assert "provider: 'v8'" in content
    assert unmapped == []


def test_translate_jest_config_jsdom_env(tmp_path):
    from migrate_jest_to_vitest import translate_jest_config_to_vitest
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { testEnvironment: 'jsdom' };"
    )
    content, _ = translate_jest_config_to_vitest(
        tmp_path / "jest.config.js", tmp_path
    )
    assert "environment: 'jsdom'" in content


def test_translate_flags_setupFilesAfterEach_unmapped(tmp_path):
    """WARN-2 / Amendment-4: setupFilesAfterEach has NO Vitest equivalent."""
    from migrate_jest_to_vitest import translate_jest_config_to_vitest
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { setupFilesAfterEach: ['./setup.ts'] };"
    )
    _, unmapped = translate_jest_config_to_vitest(
        tmp_path / "jest.config.js", tmp_path
    )
    assert any("setupFilesAfterEach" in u for u in unmapped)


def test_translate_flags_globalSetup_unmapped(tmp_path):
    from migrate_jest_to_vitest import translate_jest_config_to_vitest
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { globalSetup: './gs.js' };"
    )
    _, unmapped = translate_jest_config_to_vitest(
        tmp_path / "jest.config.js", tmp_path
    )
    assert any("globalSetup" in u for u in unmapped)


def test_translate_module_name_mapper(tmp_path):
    from migrate_jest_to_vitest import translate_jest_config_to_vitest
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { moduleNameMapper: { '^@/(.*)$': '<rootDir>/src/$1' } };"
    )
    content, _ = translate_jest_config_to_vitest(
        tmp_path / "jest.config.js", tmp_path
    )
    assert "resolve" in content
    assert "alias" in content


def test_rewrite_package_json_scripts(tmp_path):
    from migrate_jest_to_vitest import rewrite_package_json
    (tmp_path / "package.json").write_text(json.dumps({
        "scripts": {
            "test": "jest",
            "test:watch": "jest --watch",
            "test:coverage": "jest --coverage",
        },
        "devDependencies": {"jest": "^29.0.0", "@types/jest": "^29", "ts-jest": "^29"},
    }, indent=2))
    rewrite_package_json(tmp_path / "package.json")
    pkg = json.loads((tmp_path / "package.json").read_text())
    assert pkg["scripts"]["test"] == "vitest run"
    assert pkg["scripts"]["test:watch"] == "vitest"
    assert "--coverage" in pkg["scripts"]["test:coverage"]
    assert "vitest" in pkg["scripts"]["test:coverage"]


def test_rewrite_package_json_removes_jest_deps(tmp_path):
    from migrate_jest_to_vitest import rewrite_package_json
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {
            "jest": "^29", "@types/jest": "^29", "ts-jest": "^29",
            "babel-jest": "^29", "@swc/jest": "^0.2",
        },
    }, indent=2))
    rewrite_package_json(tmp_path / "package.json")
    pkg = json.loads((tmp_path / "package.json").read_text())
    dev = pkg["devDependencies"]
    assert "jest" not in dev
    assert "@types/jest" not in dev
    assert "ts-jest" not in dev
    assert "babel-jest" not in dev
    assert "@swc/jest" not in dev
    assert "vitest" in dev
    assert "@vitest/coverage-v8" in dev


def test_rewrite_package_json_strips_inline_jest_key(tmp_path):
    from migrate_jest_to_vitest import rewrite_package_json
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^29"},
        "jest": {"testEnvironment": "node"},
    }, indent=2))
    rewrite_package_json(tmp_path / "package.json")
    pkg = json.loads((tmp_path / "package.json").read_text())
    assert "jest" not in pkg


def test_rewrite_package_json_adds_jsdom_for_frontend(tmp_path):
    from migrate_jest_to_vitest import rewrite_package_json
    (tmp_path / "package.json").write_text(json.dumps({
        "dependencies": {"react": "^18.0.0"},
        "devDependencies": {"jest": "^29"},
    }, indent=2))
    rewrite_package_json(tmp_path / "package.json")
    pkg = json.loads((tmp_path / "package.json").read_text())
    assert "jsdom" in pkg["devDependencies"]


def test_rename_jest_setup_to_vitest_setup(tmp_path):
    from migrate_jest_to_vitest import rename_setup_files
    (tmp_path / "jest.setup.ts").write_text(
        "import '@testing-library/jest-dom';\nglobal.fetch = jest.fn();\n"
    )
    renamed = rename_setup_files(tmp_path)
    assert not (tmp_path / "jest.setup.ts").is_file()
    assert (tmp_path / "vitest.setup.ts").is_file()
    content = (tmp_path / "vitest.setup.ts").read_text()
    assert "@testing-library/jest-dom/vitest" in content
    assert "vi.fn" in content
    assert any("jest.setup.ts" in r and "vitest.setup.ts" in r for r in renamed)
```

### B. Implementation extensions

Aggiungere a `migrate_jest_to_vitest.py`:

```python
JEST_SETUP_NAMES = ("jest.setup.ts", "jest.setup.js", "jest.setup.mjs", "setupTests.ts", "setupTests.js")

REMOVE_DEVDEPS = {
    "jest", "@types/jest", "ts-jest", "babel-jest", "@swc/jest",
    "jest-environment-jsdom", "jest-environment-node", "jest-config", "jest-cli",
    "@jest/globals",
}

VITEST_CONFIG_TEMPLATE = '''import {{ defineConfig }} from 'vitest/config';

// Generated by code-coverage skill Phase 4b (Jest -> Vitest migration).
// Review and adapt as needed.
export default defineConfig({{
{alias_block}  test: {{
    environment: '{env}',
    globals: true,
{setup_block}    coverage: {{
      provider: 'v8',
      reporter: ['text', 'json-summary'],
    }},
  }},
}});
'''


def translate_jest_config_to_vitest(jest_cfg: Path, ws_dir: Path) -> tuple[str, list[str]]:
    text = jest_cfg.read_text(encoding="utf-8", errors="ignore")
    unmapped: list[str] = []

    compat = _load_compat()
    manual_review_keys = compat["api_migration_map"]["config_keys_manual_review"]
    for key in manual_review_keys:
        if re.search(rf"\b{re.escape(key)}\s*:", text):
            unmapped.append(f"{key}: no direct Vitest equivalent, manual review")

    env = "node"
    m = re.search(r"testEnvironment\s*:\s*['\"](\w+)['\"]", text)
    if m and m.group(1) == "jsdom":
        env = "jsdom"

    aliases: dict[str, str] = {}
    m = re.search(r"moduleNameMapper\s*:\s*\{([^}]+)\}", text, re.DOTALL)
    if m:
        for k, v in re.findall(r"['\"]([^'\"]+)['\"]\s*:\s*['\"]([^'\"]+)['\"]", m.group(1)):
            ck = re.sub(r"^\^?|\$?$|\(\.\*\)", "", k).strip("/")
            aliases[ck] = v.replace("<rootDir>/", "").replace("$1", "")

    alias_block = ""
    if aliases:
        alias_block = "  resolve: {\n    alias: {\n"
        for k, v in aliases.items():
            alias_block += f"      {json.dumps(k)}: {json.dumps(v)},\n"
        alias_block += "    },\n  },\n"

    setup_files: list[str] = []
    m = re.search(r"\bsetupFiles\s*:\s*\[([^\]]+)\]", text, re.DOTALL)
    if m:
        setup_files = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
    setup_block = ""
    if setup_files:
        renamed = [s.replace("jest.setup", "vitest.setup") for s in setup_files]
        setup_block = f"    setupFiles: {json.dumps(renamed)},\n"

    content = VITEST_CONFIG_TEMPLATE.format(
        alias_block=alias_block,
        env=env,
        setup_block=setup_block,
    )
    return content, unmapped


def rewrite_package_json(pkg_path: Path) -> dict:
    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    report = {"scripts_changed": [], "devdeps_removed": [], "devdeps_added": []}
    scripts = pkg.get("scripts", {})
    for name, script in list(scripts.items()):
        if not isinstance(script, str):
            continue
        new_script = re.sub(r"\bjest\s+--watch(?:All)?\b", "vitest", script)
        new_script = re.sub(r"\bjest\s+--coverage\b", "vitest run --coverage", new_script)
        new_script = re.sub(r"(^|\s|&&\s*)jest($|\s)", r"\1vitest run\2", new_script)
        new_script = re.sub(r"\s+", " ", new_script).strip()
        if new_script != script:
            scripts[name] = new_script
            report["scripts_changed"].append(name)
    if scripts:
        pkg["scripts"] = scripts

    dev = pkg.get("devDependencies", {})
    for dep in list(dev.keys()):
        if dep in REMOVE_DEVDEPS or dep.startswith("jest-") and dep not in {"jest-junit"}:
            del dev[dep]
            report["devdeps_removed"].append(dep)
    for added in ("vitest", "@vitest/coverage-v8"):
        if added not in dev:
            dev[added] = "^1.6.0"
            report["devdeps_added"].append(added)

    all_deps = {**(pkg.get("dependencies") or {}), **dev}
    frontend_markers = {"react", "vue", "@angular/core", "svelte"}
    if any(k in all_deps for k in frontend_markers) and "jsdom" not in dev:
        dev["jsdom"] = "^24.0.0"
        report["devdeps_added"].append("jsdom")

    if dev:
        pkg["devDependencies"] = dev
    if "jest" in pkg:
        del pkg["jest"]

    pkg_path.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")
    return report


def rename_setup_files(ws_dir: Path) -> list[str]:
    renamed: list[str] = []
    for name in JEST_SETUP_NAMES:
        src = ws_dir / name
        if not src.is_file():
            continue
        text = src.read_text(encoding="utf-8", errors="ignore")
        new_text, _, _ = codemod_text(text)
        dst = ws_dir / "vitest.setup.ts"
        if dst.exists() and dst != src:
            renamed.append(f"CONFLICT:{src.name} -> vitest.setup.ts (target exists)")
            continue
        dst.write_text(new_text, encoding="utf-8")
        src.unlink()
        renamed.append(f"{src.name} -> vitest.setup.ts")
    return renamed
```

### C. Run

```bash
python3 -m pytest skills/code-coverage/scripts/tests/test_migrate_jest_to_vitest.py -v
```

## Acceptance

- [ ] 10 nuovi test pass (config translation + package.json + setup rename)
- [ ] Tutti i test del task-04 ancora pass
- [ ] No regression sull'asset (vitest-jest-compat.json letto correttamente)
