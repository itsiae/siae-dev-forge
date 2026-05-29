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


# ─── C2 fix: normalize uses first 3 non-empty lines, not just line-1 ─────────


def test_normalize_uses_first_three_non_empty_lines():
    """C2: signature must include lines 2+ so Vitest/Jest headers don't mask
    the actual assertion arriving on later non-empty lines."""
    vitest_like = (
        "\n"
        "❯ src/foo.test.ts (3 tests | 2 failed)\n"
        "\n"
        "  FAIL src/foo.test.ts > computes total\n"
        "    AssertionError: expected 7 to equal 42\n"
        "      at src/foo.test.ts:8:5\n"
    )
    sig = cf.normalize(vitest_like)
    assert "AssertionError" in sig, (
        f"normalize() must surface assertion from line >1, got: {sig!r}"
    )


def test_normalize_caps_at_three_non_empty_lines():
    """C2: stop accumulating at 3 non-empty lines; subsequent stack frames
    must NOT bleed into signature (signature stability across runs)."""
    err = (
        "line 1 header\n"
        "line 2 assertion\n"
        "line 3 location\n"
        "line 4 stack frame should be excluded uuid=abc-123\n"
        "line 5 stack frame should be excluded\n"
    )
    sig = cf.normalize(err)
    assert "line 4" not in sig
    assert "line 5" not in sig
    assert "line 1" in sig
    assert "line 2" in sig
    assert "line 3" in sig


def test_normalize_single_line_behavior_unchanged():
    """C2 regression: single-line input must still produce a single-line sig."""
    err = "AssertionError: expected foo to be bar"
    sig = cf.normalize(err)
    assert sig == "AssertionError: expected foo to be bar"


def test_normalize_deterministic_multiline():
    """C2: two stderr blocks with same assertion shape but different
    paths/timestamps/line:col must produce IDENTICAL signature (grouping key).
    NOTE: normalize_regex strips paths/lines but NOT counters like
    "(3 tests | 1 failed)" — header text must be invariant across the pair."""
    err1 = (
        "FAIL src/foo.test.ts > sum\n"
        "AssertionError: expected 7 to equal 42\n"
        "  at /tmp/a/foo.ts:12:5\n"
    )
    err2 = (
        "FAIL src/foo.test.ts > sum\n"
        "AssertionError: expected 7 to equal 42\n"
        "  at /home/x/foo.ts:99:1\n"
    )
    sig1 = cf.normalize(err1)
    sig2 = cf.normalize(err2)
    assert sig1 == sig2, f"multiline normalize non deterministico:\n{sig1!r}\n!=\n{sig2!r}"


def test_repair_strategies_has_branch_gap_stall():
    p = Path(__file__).resolve().parents[2] / "assets" / "repair-strategies.json"
    data = json.loads(p.read_text())
    # struttura: lista di categorie o dict con "categories"
    cats = data if isinstance(data, list) else data.get("categories", data.get("strategies", []))
    ids = [c.get("id") for c in cats] if isinstance(cats, list) else list(cats.keys())
    assert 13 in ids or "13" in [str(i) for i in ids], "manca categoria 13 branch_gap_stall"
