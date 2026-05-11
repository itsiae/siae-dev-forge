"""Test estensione validate_env.py — real check_framework_installed (P10/ST4)."""
import json
import subprocess
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "repos"
SCRIPT = Path(__file__).resolve().parent.parent / "validate_env.py"


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
