"""Test per parse_coverage.py — copre i 4 casi richiesti dal design doc PR3.

I test usano direct-import per consentire misura coverage tramite
coverage.py (subprocess sarebbe invisibile al tracer). Un test e2e
finale invoca il CLI per verificare l'entry-point main().
"""
import json
import subprocess
from pathlib import Path

import parse_coverage as pc

FIXTURES = Path(__file__).parent / "fixtures"
SCRIPT = Path(__file__).resolve().parent.parent / "parse_coverage.py"


def _load_fixture(name: str) -> dict:
    with open(FIXTURES / name) as f:
        return json.load(f)


def test_vitest_json_summary_parsing():
    data = _load_fixture("vitest-summary.json")
    result = pc.parse("vitest", FIXTURES / "vitest-summary.json", priority_rules=None)
    assert result["framework"] == "vitest"
    assert result["error"] is None
    assert result["global_pct"] == 75.0
    assert isinstance(result["modules"], list)
    assert all("path" in m and "lines_pct" in m for m in result["modules"])


def test_jest_json_summary_parsing():
    result = pc.parse("jest", FIXTURES / "jest-summary.json", priority_rules=None)
    assert result["framework"] == "jest"
    assert result["global_pct"] == 75.0
    assert len(result["modules"]) == 1


def test_pytest_cov_json_parsing():
    result = pc.parse("pytest", FIXTURES / "pytest-cov.json", priority_rules=None)
    assert result["framework"] == "pytest"
    assert result["global_pct"] == 80.0
    assert all("path" in m for m in result["modules"])


def test_malformed_input_fallback():
    result = pc.parse("vitest", FIXTURES / "malformed.txt", priority_rules=None)
    assert result["error"] is not None
    assert "Parse error" in result["error"]
    assert result["global_pct"] == 0.0
    assert result["modules"] == []


def test_input_file_missing():
    result = pc.parse("vitest", FIXTURES / "does-not-exist.json", priority_rules=None)
    assert "Input file does not exist" in result["error"]


def test_unsupported_framework():
    # Dispatcher branch: framework valido per argparse ma non handled
    # (simuliamo bypass del CLI chiamando parse() direttamente con stringa fake)
    result = pc.parse("foobar", FIXTURES / "vitest-summary.json", priority_rules=None)
    assert result["error"] and "non supportato" in result["error"]


def test_jacoco_xml_parsing():
    xml = (
        '<?xml version="1.0"?><report>'
        '<counter type="LINE" missed="20" covered="80"/>'
        '<counter type="BRANCH" missed="10" covered="40"/>'
        '<package name="com/example">'
        '<counter type="LINE" missed="5" covered="45"/>'
        '</package>'
        '</report>'
    )
    tmp = FIXTURES / "_tmp-jacoco.xml"
    tmp.write_text(xml)
    try:
        result = pc.parse("jacoco", tmp, priority_rules=None)
        assert result["error"] is None
        assert result["global_pct"] == 80.0
        assert result["global_branch_pct"] == 80.0
        assert result["modules"][0]["path"] == "com.example"
    finally:
        tmp.unlink()


def test_go_cover_parsing():
    content = (
        "github.com/foo/pkg/file.go:10:\tFuncA\t85.7%\n"
        "github.com/foo/pkg/file.go:20:\tFuncB\t75.0%\n"
        "total:\t(statements)\t78.5%\n"
    )
    tmp = FIXTURES / "_tmp-cover.txt"
    tmp.write_text(content)
    try:
        result = pc.parse("go-test", tmp, priority_rules=None)
        assert result["global_pct"] == 78.5
        assert len(result["modules"]) == 1
    finally:
        tmp.unlink()


def test_cargo_tarpaulin_parsing():
    data = {"files": [
        {"path": "src/lib.rs", "covered": 80, "coverable": 100},
        {"path": "src/main.rs", "covered": 30, "coverable": 50},
    ]}
    tmp = FIXTURES / "_tmp-cargo.json"
    tmp.write_text(json.dumps(data))
    try:
        result = pc.parse("cargo", tmp, priority_rules=None)
        assert result["global_pct"] == round((80 + 30) / (100 + 50) * 100, 2)
        assert len(result["modules"]) == 2
    finally:
        tmp.unlink()


def test_priority_rules_assignment():
    rules = {
        "priority_levels": {
            "P1": {"path_patterns": ["**/services/**"], "min_coverage_pct": 80.0},
            "P2": {"path_patterns": ["**/utils/**"], "min_coverage_pct": 70.0},
        }
    }
    result = pc.parse("vitest", FIXTURES / "vitest-summary.json", priority_rules=rules)
    paths = {m["path"]: m for m in result["modules"]}
    payment = paths["src/services/payment.ts"]
    assert payment["priority"] == "P1"
    assert payment["threshold"] == 80.0
    assert payment["status"] == "FAIL"  # 60% < 80%
    fmt = paths["src/utils/format.ts"]
    assert fmt["priority"] == "P2"
    assert fmt["status"] == "PASS"  # 90% >= 70%
    assert "src/services/payment.ts" in result["failing"]


def test_load_priority_rules_returns_none_when_absent(tmp_path):
    assert pc.load_priority_rules(tmp_path) is None


def test_cli_entry_point():
    """E2E sul main() via subprocess per verificare argparse + json output."""
    result = subprocess.run(
        ["python3", str(SCRIPT), "vitest", str(FIXTURES / "vitest-summary.json")],
        capture_output=True,
        text=True,
        check=True,
    )
    output = json.loads(result.stdout)
    assert output["global_pct"] == 75.0
