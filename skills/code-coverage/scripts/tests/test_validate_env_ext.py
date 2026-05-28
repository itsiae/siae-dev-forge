"""Test estensione validate_env.py — real check_framework_installed (P10/ST4)."""
import json
import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "repos"
SCRIPT = Path(__file__).resolve().parent.parent / "validate_env.py"

# Make validate_env importable for unit-level tests
sys.path.insert(0, str(SCRIPT.parent))


def run_validate(repo_path: Path, framework: str | None = None) -> dict:
    cmd = ["python3", str(SCRIPT), str(repo_path)]
    if framework:
        cmd += ["--framework", framework]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def test_maven_junit5_real_detection():
    out = run_validate(FIXTURES / "maven-app", "junit5")
    fw_check = out.get("framework_check", {})
    assert "junit5" in fw_check
    assert fw_check["junit5"]["installed"] is True
    assert fw_check["junit5"]["source"] == "pom.xml"


def test_cargo_devdep_real_detection():
    out = run_validate(FIXTURES / "cargo-app", "cargo-test")
    fw_check = out.get("framework_check", {})
    assert "cargo-test" in fw_check
    assert fw_check["cargo-test"]["installed"] is True
    assert fw_check["cargo-test"]["source"] == "Cargo.toml"


def test_vue_vitest_real_detection():
    out = run_validate(FIXTURES / "vue-app", "vitest")
    fw_check = out.get("framework_check", {})
    assert "vitest" in fw_check
    # Auto-detect da package.json devDependencies
    assert fw_check["vitest"]["installed"] is True
    assert fw_check["vitest"]["source"] == "package.json"


def test_jest_config_does_not_force_jest_when_vitest_compatible(tmp_path):
    """BUG-FIX (2026-05-28): Principle 4 v2 - jest.config.* alone does NOT
    force jest. Vitest-first is the absolute default; jest selected ONLY
    when an incompatibility signal (I1..I10) fires.

    Old buggy behavior (pre-fix): jest.config.js + vitest in devDeps -> jest
    New correct behavior (post-fix): no incompat signal -> vitest
    """
    repo = tmp_path / "legacy-jest"
    repo.mkdir()
    (repo / "package.json").write_text(json.dumps({
        "name": "legacy-jest",
        "devDependencies": {"vitest": "^1.0.0"},
        "scripts": {"test": "vitest"},
    }))
    (repo / "jest.config.js").write_text("module.exports = {};\n")
    out = run_validate(repo)
    assert out.get("required_framework") == "vitest", (
        f"Expected 'vitest' (Vitest-first, no incompat), "
        f"got {out.get('required_framework')!r}"
    )


def test_detect_framework_nested_package_json(tmp_path):
    """Layout SIAE serverless: TF root, Lambda nested → deve trovare vitest, non unknown."""
    repo = tmp_path / "serverless-repo"
    (repo / "modules" / "retrieve-service" / "lambda-retrieve").mkdir(parents=True)
    # Solo file .tf al root
    (repo / "main.tf").write_text('resource "aws_lambda_function" "x" {}')
    # package.json nested a depth 4
    (repo / "modules" / "retrieve-service" / "lambda-retrieve" / "package.json").write_text(json.dumps({
        "name": "lambda-retrieve",
        "devDependencies": {"@types/aws-lambda": "^1.0.0"},
    }))
    from validate_env import _detect_required_framework
    assert _detect_required_framework(repo) == "vitest"


def test_detect_framework_nested_pyproject(tmp_path):
    """Layout Python nested: pyproject.toml a depth 2."""
    repo = tmp_path / "py-nested"
    (repo / "backend").mkdir(parents=True)
    (repo / "backend" / "pyproject.toml").write_text('[tool.poetry]\nname = "x"\n')
    from validate_env import _detect_required_framework
    assert _detect_required_framework(repo) == "pytest"


def test_detect_framework_pyspark_dispatch(tmp_path):
    """pyproject.toml con keyword 'pyspark' deve dispatchare su 'pytest+chispa'
    (stack-matrix.json:80-93), NON sul fallback pytest generico. Senza questo
    branch, repo PySpark/Glue ETL perdono template + chispa dep."""
    repo = tmp_path / "etl-pyspark"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        '[tool.poetry]\nname = "etl"\n'
        '[tool.poetry.dependencies]\n'
        'python = "^3.11"\n'
        'pyspark = "3.5.0"\n'
    )
    from validate_env import _detect_required_framework
    assert _detect_required_framework(repo) == "pytest+chispa"


def test_detect_framework_databricks_dispatch(tmp_path):
    """requirements.txt con 'databricks' attiva anche il branch pyspark."""
    repo = tmp_path / "etl-dbx"
    repo.mkdir()
    (repo / "requirements.txt").write_text(
        "databricks-connect==13.0.0\npydantic\n"
    )
    from validate_env import _detect_required_framework
    assert _detect_required_framework(repo) == "pytest+chispa"


def test_detect_framework_no_manifest_returns_unknown(tmp_path):
    """Repo senza alcun manifest → unknown."""
    repo = tmp_path / "empty"
    repo.mkdir(parents=True)
    (repo / "README.md").write_text("# empty")
    from validate_env import _detect_required_framework
    assert _detect_required_framework(repo) == "unknown"


def test_detect_framework_skip_dirs_ignored(tmp_path):
    """package.json dentro node_modules NON deve essere considerato."""
    repo = tmp_path / "skip-dir"
    (repo / "node_modules" / "some-pkg").mkdir(parents=True)
    (repo / "node_modules" / "some-pkg" / "package.json").write_text('{"name":"x"}')
    from validate_env import _detect_required_framework
    assert _detect_required_framework(repo) == "unknown"


def test_check_framework_installed_walks_to_manifest_root(tmp_path):
    """ADR-2: _check_framework_installed deve cercare in manifest_root_rel,
    non al repo root, per supportare layout monorepo/nested.

    Setup: root package.json (NO vitest) + modules/service/lambda/package.json
    (CON vitest in devDeps + node_modules/vitest). Atteso: framework_installed=True
    quando si passa manifest_root_rel="modules/service/lambda".
    """
    repo = tmp_path / "nested-repo"
    repo.mkdir()
    # Root package.json: nessun vitest
    (repo / "package.json").write_text(json.dumps({
        "name": "root-mono",
        "devDependencies": {"typescript": "^5.0.0"},
    }))
    # Nested manifest con vitest
    nested = repo / "modules" / "service" / "lambda"
    nested.mkdir(parents=True)
    (nested / "package.json").write_text(json.dumps({
        "name": "lambda-svc",
        "devDependencies": {"vitest": "^1.0.0"},
    }))
    # node_modules/vitest nel manifest_root (non al repo root)
    (nested / "node_modules" / "vitest").mkdir(parents=True)

    from validate_env import _check_framework_installed

    # Senza manifest_root (default "."), cerca al root → installed=False
    flat = _check_framework_installed(repo, "vitest")
    assert flat["installed"] is False, (
        f"Expected installed=False con manifest_root='.', got {flat!r}"
    )

    # Con manifest_root_rel nested → installed=True (legge nested package.json)
    nested_check = _check_framework_installed(
        repo, "vitest", "modules/service/lambda"
    )
    assert nested_check["installed"] is True, (
        f"Expected installed=True con manifest_root nested, got {nested_check!r}"
    )
    assert nested_check["source"] == "package.json"


def test_install_commands_target_manifest_root(tmp_path):
    """ADR-2: install_commands deve avere prefisso `cd <manifest_root> &&`
    quando .code-coverage/stack.json dichiara un manifest_root nested e il
    framework richiesto (vitest) NON e' installato in quel path."""
    repo = tmp_path / "nested-install"
    repo.mkdir()
    # Manifest nested SENZA vitest (forza install_commands non vuoto)
    nested = repo / "modules" / "service" / "lambda"
    nested.mkdir(parents=True)
    (nested / "package.json").write_text(json.dumps({
        "name": "lambda-svc",
        "devDependencies": {"typescript": "^5.0.0"},
    }))
    # stack.json con manifest_root nested
    (repo / ".code-coverage").mkdir()
    (repo / ".code-coverage" / "stack.json").write_text(json.dumps({
        "manifest_root": "modules/service/lambda",
        "framework": "vitest",
    }))
    # Root package.json segnaposto per far inferire vitest se proprio serve
    (repo / "package.json").write_text(json.dumps({"name": "root"}))

    out = run_validate(repo, framework="vitest")
    assert out.get("manifest_root") == "modules/service/lambda", (
        f"Expected manifest_root='modules/service/lambda' nel JSON, got {out.get('manifest_root')!r}"
    )
    install_cmds = out.get("install_commands", [])
    assert install_cmds, "install_commands deve essere non vuoto (vitest mancante)"
    # Almeno un comando deve avere prefisso cd <manifest_root> &&
    has_prefix = any(
        cmd.startswith("cd modules/service/lambda && ")
        for cmd in install_cmds
        if not cmd.lstrip().startswith("#")
    )
    assert has_prefix, (
        f"Atteso prefisso 'cd modules/service/lambda && ' in install_commands, got {install_cmds!r}"
    )


# ─── Bug-fix regression: Vitest-first delegation to jest-compat.json ──────

def test_required_framework_vitest_when_jest_compat_migrate(tmp_path):
    """BUG-FIX regression: jest.config + scripts.test=jest -> NOT 'jest'."""
    from validate_env import _detect_required_framework
    (tmp_path / "package.json").write_text(json.dumps({
        "devDependencies": {"jest": "^29"}, "scripts": {"test": "jest"},
    }))
    (tmp_path / "jest.config.js").write_text("module.exports = {};")
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
                             "incompatibility_signals": ["I1"]}},
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
    """Pre-Phase-2 call: default to vitest. THE FIX vs old presence-based logic."""
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
