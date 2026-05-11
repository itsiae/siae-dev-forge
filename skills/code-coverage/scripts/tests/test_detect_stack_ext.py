"""Test estensione detect_stack.py — verifica i 4 nuovi campi output (P10)."""
import json
import subprocess
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "repos"
SCRIPT = Path(__file__).resolve().parent.parent / "detect_stack.py"


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


def test_pre_existing_coverage_pct_calculated():
    out = run_detect(FIXTURES / "vue-app")
    assert "pre_existing_coverage_pct" in out
    # vue-app: 3 lines covered su 5 total = 60%
    assert 55 <= out["pre_existing_coverage_pct"] <= 65


def test_coverage_exclude_emitted():
    out = run_detect(FIXTURES / "vue-app")
    assert "coverage_exclude" in out
    assert isinstance(out["coverage_exclude"], list)


def test_jacoco_pre_existing_fallback():
    """Maven repo senza lcov.info ma con jacoco.xml deve produrre pre_existing_coverage_pct."""
    out = run_detect(FIXTURES / "maven-app")
    assert "pre_existing_coverage_pct" in out
    # 80 covered / 100 total = 80%
    assert 75 <= out["pre_existing_coverage_pct"] <= 85
