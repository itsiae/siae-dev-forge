"""Test migrate_jest_to_vitest.py — codemod, config translation, package.json,
snapshot, dirty-tree refuse, opt-out, per-PM matrix, smoke verify."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "migrate_jest_to_vitest.py"
sys.path.insert(0, str(SCRIPT.parent))


# ─── Codemod text-level ──────────────────────────────────────────────────

def test_codemod_jest_fn_to_vi_fn():
    from migrate_jest_to_vitest import codemod_text
    src = "const m = jest.fn();\nconst spy = jest.spyOn(obj, 'foo');\n"
    out, _, _ = codemod_text(src)
    assert "vi.fn()" in out
    assert "vi.spyOn(" in out
    assert "jest.fn" not in out
    assert "jest.spyOn" not in out


def test_codemod_jest_mock_to_vi_mock():
    from migrate_jest_to_vitest import codemod_text
    src = "jest.mock('./x');\njest.unmock('./y');\njest.doMock('./z');\n"
    out, _, _ = codemod_text(src)
    assert "vi.mock('./x')" in out
    assert "vi.unmock('./y')" in out
    assert "vi.doMock('./z')" in out


def test_codemod_timers():
    from migrate_jest_to_vitest import codemod_text
    src = "jest.useFakeTimers();\njest.advanceTimersByTime(1000);\njest.runAllTimers();\n"
    out, _, _ = codemod_text(src)
    assert "vi.useFakeTimers" in out
    assert "vi.advanceTimersByTime" in out
    assert "vi.runAllTimers" in out


def test_codemod_no_rewrite_requireActual():
    """Amendment-4: requireActual stays as-is, but emits manual_review."""
    from migrate_jest_to_vitest import codemod_text
    src = "const real = jest.requireActual('./foo');\n"
    out, _, manual = codemod_text(src)
    assert "jest.requireActual" in out
    assert "vi.importActual" not in out
    assert any("requireActual" in m for m in manual)


def test_codemod_no_rewrite_requireMock():
    from migrate_jest_to_vitest import codemod_text
    src = "const m = jest.requireMock('./foo');\n"
    out, _, manual = codemod_text(src)
    assert "jest.requireMock" in out
    assert "vi.importMock" not in out
    assert any("requireMock" in m for m in manual)


def test_codemod_isolate_modules_rewrites_with_warning():
    from migrate_jest_to_vitest import codemod_text
    src = "jest.isolateModules(() => { require('./x'); });\n"
    out, _, manual = codemod_text(src)
    assert "vi.isolateModules" in out
    assert any("isolateModules" in m for m in manual)


def test_codemod_injects_vi_import():
    from migrate_jest_to_vitest import codemod_text
    src = "const m = jest.fn();\ntest('x', () => {});\n"
    out, _, _ = codemod_text(src)
    assert "from 'vitest'" in out


def test_codemod_does_not_double_import():
    from migrate_jest_to_vitest import codemod_text
    src = "import { vi } from 'vitest';\nconst m = vi.fn();\n"
    out, _, _ = codemod_text(src)
    assert out.count("from 'vitest'") == 1


def test_codemod_idempotent():
    from migrate_jest_to_vitest import codemod_text
    src = "const m = jest.fn();\n"
    out1, _, _ = codemod_text(src)
    out2, _, _ = codemod_text(out1)
    assert out1 == out2


def test_codemod_strips_jest_globals_import():
    from migrate_jest_to_vitest import codemod_text
    src = "import { describe, it, expect, jest } from '@jest/globals';\nconst m = jest.fn();\n"
    out, _, _ = codemod_text(src)
    assert "@jest/globals" not in out
    assert "vi.fn" in out


def test_codemod_testing_library_jest_dom_rewritten():
    from migrate_jest_to_vitest import codemod_text
    src = "import '@testing-library/jest-dom';\n"
    out, _, _ = codemod_text(src)
    assert "@testing-library/jest-dom/vitest" in out


def test_codemod_testing_library_jest_dom_extend_expect():
    from migrate_jest_to_vitest import codemod_text
    src = "import '@testing-library/jest-dom/extend-expect';\n"
    out, _, _ = codemod_text(src)
    assert "@testing-library/jest-dom/vitest" in out


# ─── Config translation ──────────────────────────────────────────────────

def test_translate_jest_config_basic_node_env(tmp_path):
    from migrate_jest_to_vitest import translate_jest_config_to_vitest
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { testEnvironment: 'node' };"
    )
    content, unmapped = translate_jest_config_to_vitest(
        tmp_path / "jest.config.js", tmp_path,
    )
    assert "defineConfig" in content
    assert "environment: 'node'" in content
    assert "provider: 'v8'" in content


def test_translate_jest_config_jsdom_env(tmp_path):
    from migrate_jest_to_vitest import translate_jest_config_to_vitest
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { testEnvironment: 'jsdom' };"
    )
    content, _ = translate_jest_config_to_vitest(
        tmp_path / "jest.config.js", tmp_path,
    )
    assert "environment: 'jsdom'" in content


def test_translate_flags_setupFilesAfterEach_unmapped(tmp_path):
    from migrate_jest_to_vitest import translate_jest_config_to_vitest
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { setupFilesAfterEach: ['./setup.ts'] };"
    )
    _, unmapped = translate_jest_config_to_vitest(
        tmp_path / "jest.config.js", tmp_path,
    )
    assert any("setupFilesAfterEach" in u for u in unmapped)


def test_translate_flags_globalSetup_unmapped(tmp_path):
    from migrate_jest_to_vitest import translate_jest_config_to_vitest
    (tmp_path / "jest.config.js").write_text(
        "module.exports = { globalSetup: './gs.js' };"
    )
    _, unmapped = translate_jest_config_to_vitest(
        tmp_path / "jest.config.js", tmp_path,
    )
    assert any("globalSetup" in u for u in unmapped)


# ─── Package.json rewrite ────────────────────────────────────────────────

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


# ─── Setup file rename ───────────────────────────────────────────────────

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


# ─── PM detection ────────────────────────────────────────────────────────

def test_detect_pm_npm(tmp_path):
    from migrate_jest_to_vitest import detect_pm
    (tmp_path / "package-lock.json").write_text("{}")
    assert detect_pm(tmp_path) == "npm"


def test_detect_pm_pnpm(tmp_path):
    from migrate_jest_to_vitest import detect_pm
    (tmp_path / "pnpm-lock.yaml").write_text("")
    assert detect_pm(tmp_path) == "pnpm"


def test_detect_pm_yarn_classic(tmp_path):
    from migrate_jest_to_vitest import detect_pm
    (tmp_path / "yarn.lock").write_text("")
    assert detect_pm(tmp_path) == "yarn"


def test_detect_pm_yarn_berry(tmp_path):
    from migrate_jest_to_vitest import detect_pm
    (tmp_path / "yarn.lock").write_text("")
    (tmp_path / ".yarnrc.yml").write_text("nodeLinker: pnp\n")
    assert detect_pm(tmp_path) == "yarn-berry"


def test_detect_pm_bun(tmp_path):
    from migrate_jest_to_vitest import detect_pm
    (tmp_path / "bun.lockb").write_text("")
    assert detect_pm(tmp_path) == "bun"


def test_detect_pm_default_npm_when_no_lockfile(tmp_path):
    from migrate_jest_to_vitest import detect_pm
    assert detect_pm(tmp_path) == "npm"


# ─── Per-PM cmd matrix ───────────────────────────────────────────────────

def test_install_cmd_for_all_pms():
    from migrate_jest_to_vitest import install_cmd_for
    assert install_cmd_for("npm") == ["npm", "install"]
    assert install_cmd_for("pnpm") == ["pnpm", "install"]
    assert install_cmd_for("yarn") == ["yarn", "install"]
    assert install_cmd_for("yarn-berry") == ["yarn", "install"]
    assert install_cmd_for("bun") == ["bun", "install"]


def test_rollback_install_cmd_for_all_pms():
    """Rollback uses frozen-lockfile flag for reproducibility (BLOCK-1 fix)."""
    from migrate_jest_to_vitest import rollback_install_cmd_for
    assert rollback_install_cmd_for("npm") == ["npm", "ci"]
    assert rollback_install_cmd_for("pnpm") == ["pnpm", "install", "--frozen-lockfile"]
    assert rollback_install_cmd_for("yarn") == ["yarn", "install", "--frozen-lockfile"]
    assert rollback_install_cmd_for("yarn-berry") == ["yarn", "install", "--immutable"]
    assert rollback_install_cmd_for("bun") == ["bun", "install", "--frozen-lockfile"]


# ─── Snapshot / restore ──────────────────────────────────────────────────

def test_snapshot_captures_files(tmp_path):
    from migrate_jest_to_vitest import snapshot_files
    (tmp_path / "package.json").write_text(json.dumps({"name": "x"}))
    (tmp_path / "package-lock.json").write_text("{}")
    snapshot_files(tmp_path, [tmp_path / "package.json", tmp_path / "package-lock.json"])
    snap = tmp_path / ".code-coverage" / "migration-snapshot"
    assert (snap / "package.json").is_file()
    assert (snap / "package-lock.json").is_file()


def test_restore_snapshot(tmp_path):
    from migrate_jest_to_vitest import snapshot_files, restore_snapshot
    (tmp_path / "package.json").write_text("original")
    snapshot_files(tmp_path, [tmp_path / "package.json"])
    (tmp_path / "package.json").write_text("modified")
    restore_snapshot(tmp_path)
    assert (tmp_path / "package.json").read_text() == "original"


# ─── Pre-flight + opt-out ────────────────────────────────────────────────

def test_dirty_tree_refuses(tmp_path):
    """Pre-flight: refuse if git status dirty on touched files."""
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "^29"}}))
    (tmp_path / "jest.config.js").write_text("module.exports = {};")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True)
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "^29", "x": "y"}}))

    from migrate_jest_to_vitest import check_clean_tree
    clean, _ = check_clean_tree(tmp_path, [tmp_path / "package.json"])
    assert clean is False


def test_clean_tree_allows(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "package.json").write_text(json.dumps({"name": "x"}))
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "init"], check=True)
    from migrate_jest_to_vitest import check_clean_tree
    clean, _ = check_clean_tree(tmp_path, [tmp_path / "package.json"])
    assert clean is True


def test_opt_out_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("CC_DISABLE_JEST_MIGRATION", "1")
    (tmp_path / ".code-coverage").mkdir()
    (tmp_path / ".code-coverage" / "strategy.json").write_text(json.dumps({
        "framework_by_workspace": {".": {"framework": "vitest", "migrate": True}},
    }))
    r = subprocess.run(
        ["python3", str(SCRIPT), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 4
    out = json.loads(r.stdout)
    assert out["status"] == "skipped"


def test_noop_when_no_migrating_workspaces(tmp_path):
    (tmp_path / ".code-coverage").mkdir()
    (tmp_path / ".code-coverage" / "strategy.json").write_text(json.dumps({
        "framework_by_workspace": {".": {"framework": "vitest", "migrate": False}},
    }))
    r = subprocess.run(
        ["python3", str(SCRIPT), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 4
