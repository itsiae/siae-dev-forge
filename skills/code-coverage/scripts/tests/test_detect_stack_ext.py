"""Test estensione detect_stack.py — verifica i 4 nuovi campi output (P10)."""
import json
import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "repos"
SCRIPT = Path(__file__).resolve().parent.parent / "detect_stack.py"

# Permetti import diretto di detect_stack per test unit-level
sys.path.insert(0, str(SCRIPT.parent))


def run_detect(repo_path: Path) -> dict:
    result = subprocess.run(
        ["python3", str(SCRIPT), str(repo_path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def test_test_infrastructure_emitted():
    out = run_detect(FIXTURES / "vue-app")
    assert "test_infrastructure" in out
    ti = out["test_infrastructure"]
    assert "frameworks_detected" in ti
    assert "test_dirs" in ti
    assert "patterns_sample" in ti
    assert "vitest" in ti["frameworks_detected"]
    assert any("__tests__" in d for d in ti["test_dirs"])


def test_module_coverage_from_lcov():
    out = run_detect(FIXTURES / "vue-app")
    assert "module_coverage" in out
    mc = out["module_coverage"]
    assert len(mc) == 2
    assert all("path" in m and "lines_pct" in m for m in mc)
    fmt = next(m for m in mc if "format" in m["path"])
    assert 60 <= fmt["lines_pct"] <= 70


def test_pre_existing_coverage_pct_from_github_variable_missing():
    """ADR-8: local report = source of truth. gh variable = hint (auxiliary).
    Vue-app fixture ha lcov.info locale (60% lines) -> pct=60.0, source=local_report.
    gh variable assente -> hint=0.0.
    """
    out = run_detect(FIXTURES / "vue-app")
    assert "pre_existing_coverage_pct" in out
    assert out["pre_existing_coverage_pct"] == 60.0
    assert out["pre_existing_coverage_source"] == "local_report"
    assert out["pre_existing_coverage_hint"] == 0.0


def test_coverage_exclude_emitted():
    out = run_detect(FIXTURES / "vue-app")
    assert "coverage_exclude" in out
    assert isinstance(out["coverage_exclude"], list)


def test_jacoco_module_coverage_still_emitted():
    """ADR-8: jacoco.xml locale -> pct=80.0 source=local_report.
    module_coverage ancora popolato per D1 TIER-FIRST ordering.
    """
    out = run_detect(FIXTURES / "maven-app")
    assert "pre_existing_coverage_pct" in out
    assert out["pre_existing_coverage_pct"] == 80.0
    assert out["pre_existing_coverage_source"] == "local_report"
    # module_coverage continua a venire da jacoco
    assert "module_coverage" in out
    assert len(out["module_coverage"]) >= 1


def test_pre_existing_coverage_source_field_present():
    """ADR-8: source field can be local_report (lcov/jacoco) | github_variable | missing."""
    out = run_detect(FIXTURES / "vue-app")
    assert "pre_existing_coverage_source" in out
    assert out["pre_existing_coverage_source"] in {"local_report", "github_variable", "missing"}


def test_parse_github_owner_repo_url_forms():
    from detect_stack import _parse_github_owner_repo
    cases = [
        # (input, expected_output)
        ("https://github.com/owner/repo", "owner/repo"),
        ("https://github.com/owner/repo.git", "owner/repo"),
        ("https://github.com/owner/repo/", "owner/repo"),
        ("https://user:token@github.com/owner/repo.git", "owner/repo"),
        ("git@github.com:owner/repo.git", "owner/repo"),
        ("git@github.com:owner/repo", "owner/repo"),
        ("git@github.com-personal:owner/repo.git", "owner/repo"),  # SSH alias
        ("ssh://git@github.com/owner/repo.git", "owner/repo"),
        ("ssh://git@github.com:22/owner/repo.git", "owner/repo"),  # SSH port
        ("ssh://git@github.com:22/owner/repo", "owner/repo"),
        ("git+ssh://git@github.com/owner/repo.git", "owner/repo"),
        ("https://github.com/owner/foo.bar.io.git", "owner/foo.bar.io"),  # dots in name
        ("https://github.com/owner/foo.bar", "owner/foo.bar"),
        # Negative:
        ("https://gitlab.com/owner/repo.git", None),
        ("https://bitbucket.org/owner/repo", None),
        ("", None),
        ("not-a-url", None),
        ("https://github.com/", None),
        ("https://github.com/onlyowner", None),
    ]
    for inp, expected in cases:
        out = _parse_github_owner_repo(inp)
        assert out == expected, f"For {inp!r}: expected {expected!r}, got {out!r}"


# ---------------------------------------------------------------------------
# Anthropic error-reporting pattern: stdout JSON full-shape + exit 0
# ---------------------------------------------------------------------------

def _run_raw(args: list[str]) -> subprocess.CompletedProcess:
    """Run detect_stack.py senza check=True per ispezionare exit code."""
    return subprocess.run(
        ["python3", str(SCRIPT), *args],
        capture_output=True, text=True, check=False,
    )


def test_normal_path_has_error_null():
    out = run_detect(FIXTURES / "vue-app")
    assert "error" in out, "normal path JSON must include 'error' key"
    assert out["error"] is None


def test_not_a_directory_emits_stdout_json_exit_zero(tmp_path):
    missing = tmp_path / "does_not_exist_xyz"
    proc = _run_raw([str(missing)])
    assert proc.returncode == 0, f"expected exit 0, got {proc.returncode}"
    payload = json.loads(proc.stdout)
    assert payload["error"] is not None
    assert "Not a directory" in payload["error"]
    # full-shape schema: default fields + maven_aggregator (Task 01) + branch fields (Task 01) + error
    assert len(payload.keys()) == 23


def test_missing_argument_emits_stdout_json_exit_zero():
    proc = _run_raw([])
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["error"] is not None
    assert "Usage" in payload["error"]
    assert len(payload.keys()) == 23  # +1 maven_aggregator (Task 01) +2 branch fields (Task 01)


def test_walk_finds_java_deep_layout(tmp_path):
    """Java enterprise layout: src/main/java/com/foo/bar/baz/Module.java depth>6."""
    repo = tmp_path / "java-deep"
    deep = repo / "src" / "main" / "java" / "com" / "example" / "feature" / "service"
    deep.mkdir(parents=True)
    (deep / "MyService.java").write_text("package com.example.feature.service;\nclass MyService {}\n")
    from detect_stack import detect_languages
    langs = detect_languages(repo)
    assert "java" in langs, f"expected java in langs, got {langs}"


def test_walk_finds_python_deep_layout(tmp_path):
    """Python nested package: apps/svc/domain/usecase/handler/file.py."""
    repo = tmp_path / "py-deep"
    deep = repo / "apps" / "svc" / "domain" / "usecase" / "handler"
    deep.mkdir(parents=True)
    (deep / "ProcessOrder.py").write_text("def handler(): pass\n")
    from detect_stack import detect_languages
    langs = detect_languages(repo)
    assert "python" in langs


def test_walk_skips_dirs_correctly(tmp_path):
    """node_modules/.../file.ts NON deve apparire in langs (skip dir)."""
    repo = tmp_path / "skip"
    nm = repo / "node_modules" / "some-pkg" / "src"
    nm.mkdir(parents=True)
    (nm / "x.ts").write_text("export const x = 1;\n")
    from detect_stack import detect_languages
    langs = detect_languages(repo)
    assert "typescript" not in langs, f"node_modules should be skipped, got {langs}"


def test_error_payload_schema_complete(tmp_path):
    """Consumer (SKILL.md Phase 1) deve poter parsare lo stesso shape sempre."""
    missing = tmp_path / "missing"
    proc = _run_raw([str(missing)])
    payload = json.loads(proc.stdout)
    expected_keys = {
        "repo_path", "languages", "frameworks", "package_managers",
        "build_systems", "monorepo", "monorepo_workspaces",
        "ci_cd", "architecture_style",
        "existing_test_frameworks", "test_infrastructure",
        "pre_existing_coverage_pct", "pre_existing_coverage_source",
        "pre_existing_coverage_hint",
        "module_coverage", "coverage_exclude",
        "orchestration_only", "orchestration_reason", "manifest_root",
        "maven_aggregator",
        "pre_existing_branch_pct", "line_branch_delta",
        "error",
    }
    assert set(payload.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Task-02 (G1) — Orchestration-only gate
# ---------------------------------------------------------------------------

def _init_git_repo(repo: Path, remote_url: str) -> None:
    """Inizializza un repo git stub con remote ``origin`` settato.

    Idempotente: se ``.git`` esiste, sovrascrive ``config``.
    """
    import subprocess as _sp
    repo.mkdir(parents=True, exist_ok=True)
    _sp.run(["git", "-C", str(repo), "init", "-q"], check=False)
    # rimuovi origin esistente (idempotenza)
    _sp.run(["git", "-C", str(repo), "remote", "remove", "origin"],
            check=False, capture_output=True)
    _sp.run(["git", "-C", str(repo), "remote", "add", "origin", remote_url],
            check=False, capture_output=True)


def test_orchestration_only_by_name_iac_suffix(tmp_path):
    from detect_stack import is_orchestration_only_repo
    repo = tmp_path / "foobar-iac"
    _init_git_repo(repo, "git@github.com:itsiae/foobar-iac.git")
    ok, reason = is_orchestration_only_repo(repo)
    assert ok is True
    assert reason == "name_pattern_iac"


def test_orchestration_only_by_name_iaac_suffix(tmp_path):
    from detect_stack import is_orchestration_only_repo
    repo = tmp_path / "enterpriseplatform-core-iaac"
    _init_git_repo(repo, "git@github.com:itsiae/enterpriseplatform-core-iaac.git")
    ok, reason = is_orchestration_only_repo(repo)
    assert ok is True
    assert reason == "name_pattern_iaac"


def test_orchestration_only_by_content_terraform_dominant(tmp_path):
    from detect_stack import is_orchestration_only_repo
    repo = tmp_path / "tf-only"
    repo.mkdir()
    for i in range(65):
        (repo / f"main_{i}.tf").write_text('resource "aws_s3_bucket" "b" {}\n')
    for i in range(7):
        (repo / f"vars_{i}.hcl").write_text('locals { x = 1 }\n')
    ok, reason = is_orchestration_only_repo(repo)
    assert ok is True
    assert reason == "terraform_dominant_no_runtime_manifest"


def test_orchestration_only_false_on_terraform_with_lambda(tmp_path):
    from detect_stack import is_orchestration_only_repo
    repo = tmp_path / "tf-lambda"
    repo.mkdir()
    for i in range(5):
        (repo / f"main_{i}.tf").write_text('resource "aws_lambda_function" "x" {}\n')
    (repo / "package.json").write_text(json.dumps({
        "name": "lambda-app",
        "dependencies": {"aws-sdk": "^2.0.0"},
    }))
    ok, reason = is_orchestration_only_repo(repo)
    assert ok is False
    assert reason is None


def test_orchestration_only_false_on_pure_app_repo(tmp_path):
    from detect_stack import is_orchestration_only_repo
    repo = tmp_path / "pure-app"
    src = repo / "src"
    src.mkdir(parents=True)
    (repo / "package.json").write_text(json.dumps({
        "name": "pure-app",
        "dependencies": {"express": "^4.0.0"},
    }))
    for i in range(30):
        (src / f"mod_{i}.ts").write_text("export const x = 1;\n")
    ok, reason = is_orchestration_only_repo(repo)
    assert ok is False
    assert reason is None


# ---------------------------------------------------------------------------
# Task-03 (G2) — manifest_root surfacing
# ---------------------------------------------------------------------------

def test_manifest_root_flat_repo(tmp_path):
    from detect_stack import detect_manifest_root
    repo = tmp_path / "flat"
    repo.mkdir()
    (repo / "package.json").write_text(json.dumps({
        "name": "flat",
        "scripts": {"test": "vitest"},
        "devDependencies": {"vitest": "^1.0.0"},
    }))
    assert detect_manifest_root(repo) == "."


def test_manifest_root_nested_lambda_modules_service(tmp_path):
    from detect_stack import detect_manifest_root
    repo = tmp_path / "nested"
    repo.mkdir()
    (repo / "package.json").write_text(json.dumps({
        "name": "root",
        "devDependencies": {"husky": "^9.0.0"},
    }))
    nested = repo / "modules" / "service" / "lambda"
    nested.mkdir(parents=True)
    (nested / "package.json").write_text(json.dumps({
        "name": "lambda",
        "scripts": {"test": "vitest"},
        "devDependencies": {"vitest": "^1.0.0"},
    }))
    result = detect_manifest_root(repo)
    # Should be the path with test script (depth 3), normalized
    assert result == "modules/service/lambda" or result == "modules\\service\\lambda"


def test_detect_monorepo_extended_modules_pattern(tmp_path):
    from detect_stack import detect_monorepo
    repo = tmp_path / "monorepo-ext"
    repo.mkdir()
    (repo / "package.json").write_text(json.dumps({
        "name": "root",
        "devDependencies": {"husky": "^9.0.0"},
    }))
    nested = repo / "modules" / "service" / "lambda"
    nested.mkdir(parents=True)
    (nested / "package.json").write_text(json.dumps({
        "name": "lambda",
        "scripts": {"test": "vitest"},
        "devDependencies": {"vitest": "^1.0.0"},
    }))
    assert detect_monorepo(repo) is True


def test_manifest_root_picks_deepest_with_test_script(tmp_path):
    from detect_stack import detect_manifest_root
    repo = tmp_path / "multi-nested"
    repo.mkdir()
    (repo / "package.json").write_text(json.dumps({
        "name": "root",
        "devDependencies": {"husky": "^9.0.0"},
    }))
    a = repo / "apps" / "frontend"
    a.mkdir(parents=True)
    (a / "package.json").write_text(json.dumps({
        "name": "frontend",
        "dependencies": {"react": "^18.0.0"},
    }))
    b = repo / "services" / "backend"
    b.mkdir(parents=True)
    (b / "package.json").write_text(json.dumps({
        "name": "backend",
        "scripts": {"test": "jest"},
        "devDependencies": {"jest": "^29.0.0"},
    }))
    result = detect_manifest_root(repo)
    assert result in ("services/backend", "services\\backend")


def test_manifest_root_python_pyproject_with_pytest(tmp_path):
    from detect_stack import detect_manifest_root
    repo = tmp_path / "py-app"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        "[tool.poetry]\nname=\"x\"\n[tool.poetry.dependencies]\npytest=\"^7.0\"\n"
    )
    assert detect_manifest_root(repo) == "."


# ---------------------------------------------------------------------------
# Task-04 (G8) — gh variable demote-to-hint
# ---------------------------------------------------------------------------

def test_pre_existing_coverage_from_local_lcov_wins(tmp_path, monkeypatch):
    """Setup: coverage/lcov.info valido (~82%) + simulazione no-gh-var.
    Atteso: pre_existing_coverage_pct dal lcov, source=local_report.
    """
    repo = tmp_path / "lcov-app"
    repo.mkdir()
    (repo / "package.json").write_text(json.dumps({"name": "x"}))
    cov = repo / "coverage"
    cov.mkdir()
    # 82 covered / 100 total → 82%
    lcov = (
        "SF:src/foo.ts\n"
        "LF:100\n"
        "LH:82\n"
        "end_of_record\n"
    )
    (cov / "lcov.info").write_text(lcov)
    out = run_detect(repo)
    assert out["pre_existing_coverage_pct"] == 82.0
    assert out["pre_existing_coverage_source"] == "local_report"


def test_pre_existing_coverage_from_local_jacoco_wins(tmp_path):
    """Setup: target/site/jacoco/jacoco.xml con missed=20/covered=80 (80%).
    Atteso: pre_existing_coverage_pct=80.0, source=local_report.
    """
    repo = tmp_path / "jacoco-app"
    repo.mkdir()
    (repo / "pom.xml").write_text("<project/>\n")
    target = repo / "target" / "site" / "jacoco"
    target.mkdir(parents=True)
    jacoco_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<report>'
        '<counter type="LINE" missed="20" covered="80"/>'
        '</report>\n'
    )
    (target / "jacoco.xml").write_text(jacoco_xml)
    out = run_detect(repo)
    assert out["pre_existing_coverage_pct"] == 80.0
    assert out["pre_existing_coverage_source"] == "local_report"


def test_pre_existing_coverage_hint_from_gh_when_no_local(tmp_path):
    """Setup: no local report, no gh remote (vue-app-like).
    Atteso: pct=0.0, hint=0.0, source=missing (no gh remote -> no var).
    """
    repo = tmp_path / "no-cov"
    repo.mkdir()
    (repo / "package.json").write_text(json.dumps({"name": "x"}))
    out = run_detect(repo)
    assert out["pre_existing_coverage_pct"] == 0.0
    assert out["pre_existing_coverage_source"] == "missing"
    assert out["pre_existing_coverage_hint"] == 0.0


def test_pre_existing_coverage_missing_both(tmp_path):
    """Setup: empty repo. Atteso: pct=0, hint=0, source=missing."""
    repo = tmp_path / "empty"
    repo.mkdir()
    out = run_detect(repo)
    assert out["pre_existing_coverage_pct"] == 0.0
    assert out["pre_existing_coverage_hint"] == 0.0
    assert out["pre_existing_coverage_source"] == "missing"


# ---------------------------------------------------------------------------
# Task-05 (G12) — test_infrastructure co-presence fix
# ---------------------------------------------------------------------------

def test_test_dirs_excludes_source_dir_named_test(tmp_path):
    """src/api/test/ contiene solo route.ts (no test files) → NON deve apparire in test_dirs."""
    from detect_stack import detect_test_infrastructure
    repo = tmp_path / "route-test-dir"
    test_subdir = repo / "src" / "api" / "test"
    test_subdir.mkdir(parents=True)
    (test_subdir / "route.ts").write_text("export const handler = () => {};\n")
    ti = detect_test_infrastructure(repo, [])
    assert all("src/api/test" not in d and "src\\api\\test" not in d
               for d in ti["test_dirs"]), f"got {ti['test_dirs']}"


def test_test_dirs_includes_dir_with_test_file(tmp_path):
    """src/__tests__/cognito-auth.test.ts → test_dirs INCLUDE src/__tests__."""
    from detect_stack import detect_test_infrastructure
    repo = tmp_path / "real-tests"
    td = repo / "src" / "__tests__"
    td.mkdir(parents=True)
    (td / "cognito-auth.test.ts").write_text("import { describe } from 'vitest';\n")
    ti = detect_test_infrastructure(repo, [])
    assert any("__tests__" in d for d in ti["test_dirs"]), f"got {ti['test_dirs']}"


def test_test_dirs_python_test_underscore_prefix(tmp_path):
    """tests/test_pipeline.py → test_dirs INCLUDE tests."""
    from detect_stack import detect_test_infrastructure
    repo = tmp_path / "py-tests"
    td = repo / "tests"
    td.mkdir(parents=True)
    (td / "test_pipeline.py").write_text("def test_x(): pass\n")
    ti = detect_test_infrastructure(repo, [])
    assert any(d == "tests" for d in ti["test_dirs"]), f"got {ti['test_dirs']}"


def test_test_dirs_java_test_suffix(tmp_path):
    """src/test/java/PaymentServiceTest.java → test_dirs INCLUDE src/test (o src/test/java)."""
    from detect_stack import detect_test_infrastructure
    repo = tmp_path / "java-tests"
    td = repo / "src" / "test" / "java"
    td.mkdir(parents=True)
    (td / "PaymentServiceTest.java").write_text("class PaymentServiceTest {}\n")
    ti = detect_test_infrastructure(repo, [])
    # Should include either src/test or src/test/java (any dir named "test" with a test file inside it via rglob)
    matched = any(("src/test" in d) or ("src\\test" in d) for d in ti["test_dirs"])
    assert matched, f"got {ti['test_dirs']}"
