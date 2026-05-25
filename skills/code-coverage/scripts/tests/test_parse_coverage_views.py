"""Test per --view {full,repair,summary} di parse_coverage.py (B1) e
priority anchor fix (B2) e parse_go_cover weighted (B3).

TDD: questi test sono scritti PRIMA dell'implementazione (Red).
"""
import json
import subprocess
from pathlib import Path

import parse_coverage as pc

FIXTURES = Path(__file__).parent / "fixtures"
SCRIPT = Path(__file__).resolve().parent.parent / "parse_coverage.py"


# ============================================================================
# B1 — --view repair / summary flag (additivo, no breaking)
# ============================================================================

def test_view_full_is_default_and_emits_modules(tmp_path):
    """Default --view full emette payload completo con modules[]."""
    data = {
        "total": {"lines": {"pct": 70.0}, "branches": {"pct": 60.0}},
        "src/a.ts": {"lines": {"pct": 80.0}, "branches": {"pct": 50.0, "total": 5}},
    }
    fixt = tmp_path / "summary.json"
    fixt.write_text(json.dumps(data))
    result = subprocess.run(
        ["python3", str(SCRIPT), "vitest", str(fixt)],
        capture_output=True, text=True, check=True,
    )
    payload = json.loads(result.stdout)
    assert "modules" in payload
    assert payload["modules"], "default view must include modules[]"


def test_view_repair_strips_modules_and_keeps_aggregates(tmp_path):
    """--view repair: emette global + sub_threshold_modules (max 20) + failing_test_files + p1_floor_violators."""
    # B2: parent_dirs e' primary classifier post-anchor fix
    rules = {
        "priority_levels": {
            "P1": {"parent_dirs": ["services"], "min_coverage_pct": 80.0, "min_branch_pct": 70.0},
            "P2": {"parent_dirs": ["utils"], "min_coverage_pct": 70.0, "min_branch_pct": 60.0},
        }
    }
    # Genera 30 moduli (di cui 25 sub-threshold)
    data: dict = {
        "total": {"lines": {"pct": 65.0}, "branches": {"pct": 50.0}},
    }
    for i in range(30):
        # 25 sub-threshold P2 (utils, 70 floor) + 5 OK
        pct = 50.0 if i < 25 else 90.0
        data[f"src/utils/m_{i}.ts"] = {
            "lines": {"pct": pct},
            "branches": {"pct": pct, "total": 5},
        }
    fixt = tmp_path / "summary.json"
    fixt.write_text(json.dumps(data))
    skill_assets = tmp_path / "assets"
    skill_assets.mkdir()
    (skill_assets / "priority-rules.json").write_text(json.dumps(rules))

    full_proc = subprocess.run(
        ["python3", str(SCRIPT), "vitest", str(fixt), "--skill-root", str(tmp_path)],
        capture_output=True, text=True, check=True,
    )
    repair_proc = subprocess.run(
        ["python3", str(SCRIPT), "vitest", str(fixt), "--skill-root", str(tmp_path), "--view", "repair"],
        capture_output=True, text=True, check=True,
    )
    repair_payload = json.loads(repair_proc.stdout)

    # Aggregates preserved
    assert "global" in repair_payload
    assert repair_payload["global"]["lines_pct"] == 65.0
    assert repair_payload["global"]["threshold_met"] is False
    # modules[] stripped
    assert "modules" not in repair_payload
    # sub_threshold_modules present, capped at 20
    assert "sub_threshold_modules" in repair_payload
    assert len(repair_payload["sub_threshold_modules"]) <= 20
    # Reduction ≥ 80% in bytes vs full
    full_bytes = len(full_proc.stdout)
    repair_bytes = len(repair_proc.stdout)
    assert repair_bytes < full_bytes * 0.5, (
        f"repair ({repair_bytes}B) should be < 50% of full ({full_bytes}B)"
    )


def test_view_repair_includes_all_p1_sub_threshold_uncapped(tmp_path):
    """P1 sub-threshold modules NON sono capped a 20 (priorita' assoluta enforcement)."""
    # B2: parent_dirs primary classifier (path_patterns ancorato escluso da match)
    rules = {
        "priority_levels": {
            "P1": {"parent_dirs": ["services"], "min_coverage_pct": 80.0, "min_branch_pct": 70.0},
        }
    }
    data: dict = {"total": {"lines": {"pct": 50.0}, "branches": {"pct": 40.0}}}
    # 25 P1 sub-threshold (line=50, floor=80)
    for i in range(25):
        data[f"src/services/svc_{i}.ts"] = {"lines": {"pct": 50.0}, "branches": {"pct": 40.0, "total": 5}}
    fixt = tmp_path / "summary.json"
    fixt.write_text(json.dumps(data))
    skill_assets = tmp_path / "assets"
    skill_assets.mkdir()
    (skill_assets / "priority-rules.json").write_text(json.dumps(rules))

    proc = subprocess.run(
        ["python3", str(SCRIPT), "vitest", str(fixt), "--skill-root", str(tmp_path), "--view", "repair"],
        capture_output=True, text=True, check=True,
    )
    payload = json.loads(proc.stdout)
    # P1 floor violators (line < 80) ALL included, capped at 20 separately
    assert "p1_floor_violators" in payload
    assert len(payload["p1_floor_violators"]) <= 20
    # But sub_threshold_modules should include ALL 25 P1 (uncapped P1 rule)
    p1_in_sub_thr = [
        m for m in payload["sub_threshold_modules"]
        if m.get("priority") == "P1"
    ]
    assert len(p1_in_sub_thr) == 25, (
        f"all 25 P1 sub-threshold should be present in sub_threshold_modules, got {len(p1_in_sub_thr)}"
    )


def test_view_summary_emits_minimal_payload(tmp_path):
    """--view summary: solo {global, count_modules, count_sub_threshold}, ~200 tok."""
    data: dict = {"total": {"lines": {"pct": 80.0}, "branches": {"pct": 70.0}}}
    for i in range(20):
        pct = 50.0 if i < 5 else 90.0
        data[f"src/m_{i}.ts"] = {"lines": {"pct": pct}, "branches": {"pct": pct, "total": 5}}
    fixt = tmp_path / "summary.json"
    fixt.write_text(json.dumps(data))
    proc = subprocess.run(
        ["python3", str(SCRIPT), "vitest", str(fixt), "--view", "summary"],
        capture_output=True, text=True, check=True,
    )
    payload = json.loads(proc.stdout)
    assert "global" in payload
    assert "count_modules" in payload
    assert "count_sub_threshold" in payload
    assert payload["count_modules"] == 20
    # No modules[] / sub_threshold_modules in summary
    assert "modules" not in payload
    assert "sub_threshold_modules" not in payload
    # Size sanity: summary ≪ 2 KB
    assert len(proc.stdout) < 2048


# ============================================================================
# B2 — Priority anchor fix (last_2_segments) parità con estimate_size.py
# ============================================================================

def test_priority_pattern_unanchored_does_not_match_substring():
    """`**/store/**` NON deve matchare `src/api/restore.ts` (substring 'store')."""
    rules = {
        "priority_levels": {
            "P1": {"path_patterns": ["**/store/**"], "min_coverage_pct": 80.0, "min_branch_pct": 70.0},
        }
    }
    pri, _, _ = pc.assign_priority_and_threshold("src/api/restore.ts", rules)
    assert pri is None, (
        f"src/api/restore.ts must NOT match '**/store/**' (false-positive on 'restore'), got {pri}"
    )


def test_priority_pattern_match_real_store_dir():
    """Direct match via parent_dirs (primary classifier post-B2).

    Path `src/store/user.ts` → parent='store' → P1 via parent_dirs.
    path_patterns ancorato a last_2='store/user.ts' non matcha `**/store/**`
    deliberatamente (richiede '/store/' boundary → namespace anti-explosion).
    """
    rules = {
        "priority_levels": {
            "P1": {
                "parent_dirs": ["store"],
                "path_patterns": ["**/store/**"],
                "min_coverage_pct": 80.0,
                "min_branch_pct": 70.0,
            },
        }
    }
    pri, _, _ = pc.assign_priority_and_threshold("src/store/user.ts", rules)
    assert pri == "P1"


def test_priority_pattern_match_namespace_does_not_explode_p1():
    """`**/services/**` NON deve matchare `it/siae/services/foo/bar.java`
    perche' il file finale NON e' dentro services/* (last_2_segments=foo/bar.java).

    Empirical baseline Agent-A: senza anchor, namespace progetto contenente
    `services` (Java SIAE) classifica TUTTI i file come P1 → floor enforcement
    loop esplode.
    """
    rules = {
        "priority_levels": {
            "P1": {"path_patterns": ["**/services/**"], "min_coverage_pct": 80.0, "min_branch_pct": 70.0},
        }
    }
    # last_2_segments = "foo/bar.java" — il namespace ancestor "services" e' a
    # 2 livelli di distanza, NON deve triggerare P1.
    pri, _, _ = pc.assign_priority_and_threshold("it/siae/services/foo/bar.java", rules)
    assert pri is None, (
        f"namespace 'services' ancestor non deve triggerare P1 su file in foo/, got {pri}"
    )


def test_priority_pattern_match_modules_service_lambda_namespace():
    """`**/service/**` NON deve matchare `modules/service/lambda/src/api/uptime.ts`
    (SIAE Lambda layout): last_2_segments=api/uptime.ts → no match.

    ADR-3 baseline: 90% file → P1 false-positive senza anchor.
    """
    rules = {
        "priority_levels": {
            "P1": {"path_patterns": ["**/service/**"], "min_coverage_pct": 80.0, "min_branch_pct": 70.0},
        }
    }
    pri, _, _ = pc.assign_priority_and_threshold(
        "modules/service/lambda/src/api/uptime.ts", rules
    )
    assert pri is None, (
        f"modules/service/lambda/.../api/uptime.ts non deve essere P1, got {pri}"
    )


# ============================================================================
# B3 — parse_go_cover weighted by numStmt
# ============================================================================

def test_go_cover_out_format_weighted_by_numstmt(tmp_path):
    """coverage.out format (mode + file:start.line.col,end.line.col numStmt count):
    1 func 100% (10 stmts) + 1 func 0% (200 stmts) → line_pct ~= 4.76% (10/210).
    """
    content = (
        "mode: count\n"
        # File A: 1 block, 10 stmts, count=1 (covered)
        "github.com/foo/pkg/file.go:10.1,15.2 10 1\n"
        # File A: 1 block, 200 stmts, count=0 (NOT covered)
        "github.com/foo/pkg/file.go:20.1,40.2 200 0\n"
    )
    fixt = tmp_path / "coverage.out"
    fixt.write_text(content)
    result = pc.parse("go-test", fixt, priority_rules=None)
    assert result["error"] is None
    # global_pct should be weighted: 10 covered / 210 total ≈ 4.76%
    assert 4.0 <= result["global_pct"] <= 6.0, (
        f"weighted line_pct should be ~4.76, got {result['global_pct']}"
    )
    assert len(result["modules"]) == 1
    mod = result["modules"][0]
    assert 4.0 <= mod["lines_pct"] <= 6.0


def test_go_cover_func_format_still_parsed_with_warning(tmp_path, capfd):
    """Backward-compat: -func output (senza header `mode:`) ancora parsato
    con stderr warning. Format: file:line:\tFunc\tpct%.
    """
    content = (
        "github.com/foo/pkg/file.go:10:\tFuncA\t85.7%\n"
        "github.com/foo/pkg/file.go:20:\tFuncB\t75.0%\n"
        "total:\t(statements)\t78.5%\n"
    )
    fixt = tmp_path / "func.txt"
    fixt.write_text(content)
    result = pc.parse("go-test", fixt, priority_rules=None)
    assert result["error"] is None
    # Fallback: aritmetic mean dei func % (back-compat)
    assert result["global_pct"] == 78.5


# ============================================================================
# CLI E2E sanity
# ============================================================================

def test_cli_view_flag_validates_choices(tmp_path):
    """--view invalid → argparse choices error (exit != 0 ok per argparse)."""
    fixt = tmp_path / "summary.json"
    fixt.write_text(json.dumps({"total": {"lines": {"pct": 50.0}, "branches": {"pct": 0.0}}}))
    proc = subprocess.run(
        ["python3", str(SCRIPT), "vitest", str(fixt), "--view", "bogus"],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode != 0
