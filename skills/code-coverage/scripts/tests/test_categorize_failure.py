"""Test per categorize_failure.py — 6 categorie + normalize() determinismo."""
import json
import subprocess
from pathlib import Path

import categorize_failure as cf

FIXTURES = Path(__file__).parent / "fixtures" / "failures"
SCRIPT = Path(__file__).resolve().parent.parent / "categorize_failure.py"


def run_categorizer_via_cli(input_file: Path) -> dict:
    result = subprocess.run(
        ["python3", str(SCRIPT), str(input_file)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def _categorize_text(text: str) -> dict:
    return cf.categorize(text, cf.load_strategies())


def test_cat1_dependency():
    out = _categorize_text((FIXTURES / "cat1-dependency.txt").read_text())
    assert out["category"] == 1
    assert out["category_name"] == "dependency"
    assert "lodash" in out["captures"][0]


def test_cat2_import():
    out = _categorize_text((FIXTURES / "cat2-import.txt").read_text())
    assert out["category"] == 2
    assert out["category_name"] == "import"


def test_cat3_runtime():
    out = _categorize_text((FIXTURES / "cat3-runtime.txt").read_text())
    assert out["category"] == 3
    assert out["category_name"] == "runtime"


def test_cat4_mock():
    out = _categorize_text((FIXTURES / "cat4-mock.txt").read_text())
    assert out["category"] == 4
    assert out["category_name"] == "mock"


def test_cat5_assertion():
    out = _categorize_text((FIXTURES / "cat5-assertion.txt").read_text())
    assert out["category"] == 5
    assert out["category_name"] == "assertion"


def test_cat6_transient_evaluated_first():
    """Cat 6 (transient) viene valutata PRIMA di Cat 1-5 per evitare false categorization."""
    out = _categorize_text((FIXTURES / "cat6-transient.txt").read_text())
    assert out["category"] == 6
    assert out["category_name"] == "transient"


def test_normalize_deterministic():
    err1 = "Error at /home/user/project/src/foo.ts:12:5 timestamp=2026-05-09T10:00:00 ptr=0xabc123"
    err2 = "Error at /tmp/build/src/bar.ts:99:1 timestamp=2026-05-10T15:30:45 ptr=0xdef456"
    sig1 = cf.normalize(err1)
    sig2 = cf.normalize(err2)
    assert sig1 == sig2, f"normalize() non deterministico:\n{sig1}\n!=\n{sig2}"
    assert len(sig1) <= 200


def test_normalize_strips_ansi():
    err = "\x1b[31mAssertionError\x1b[0m: foo bar"
    sig = cf.normalize(err)
    assert "\x1b" not in sig
    assert "AssertionError" in sig


def test_no_match_returns_null_category():
    out = _categorize_text("just some random log line without recognized error pattern")
    assert out["category"] is None
    assert out["category_name"] is None
    assert out["captures"] == []


def test_cli_entry_point():
    out = run_categorizer_via_cli(FIXTURES / "cat1-dependency.txt")
    assert out["category"] == 1


def test_cli_missing_file():
    result = subprocess.run(
        ["python3", str(SCRIPT), "/tmp/does-not-exist.txt"],
        capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out["category"] is None
    assert "error" in out
