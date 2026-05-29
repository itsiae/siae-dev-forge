import json
from pathlib import Path
import detect_stack


def _write_summary(tmp_path: Path, lines_pct: float, branches_pct: float) -> Path:
    cov = tmp_path / "coverage"
    cov.mkdir(parents=True, exist_ok=True)
    summary = {
        "total": {
            "lines": {"total": 100, "covered": int(lines_pct), "pct": lines_pct},
            "branches": {"total": 100, "covered": int(branches_pct), "pct": branches_pct},
            "functions": {"total": 10, "covered": 6, "pct": 60.0},
            "statements": {"total": 100, "covered": int(lines_pct), "pct": lines_pct},
        }
    }
    p = cov / "coverage-summary.json"
    p.write_text(json.dumps(summary), encoding="utf-8")
    return p


def test_parse_branch_from_summary(tmp_path):
    _write_summary(tmp_path, 59.08, 42.31)
    line_pct, branch_pct = detect_stack.parse_coverage_summary_for_branch(tmp_path)
    assert line_pct == 59.08
    assert branch_pct == 42.31


def test_branch_zero_treated_as_unavailable(tmp_path):
    # V8 a volte riporta branches.pct=0 anche se line>0 → branch non disponibile
    _write_summary(tmp_path, 80.0, 0.0)
    line_pct, branch_pct = detect_stack.parse_coverage_summary_for_branch(tmp_path)
    assert line_pct == 80.0
    assert branch_pct == 0.0  # il caller interpreta 0 come "non disponibile"


def test_missing_summary_returns_zeros(tmp_path):
    line_pct, branch_pct = detect_stack.parse_coverage_summary_for_branch(tmp_path)
    assert (line_pct, branch_pct) == (0.0, 0.0)
