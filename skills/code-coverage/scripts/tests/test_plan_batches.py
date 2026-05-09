"""Test per plan_batches.py — verifica D1 conditional ordering."""
import json
import subprocess
from pathlib import Path

import plan_batches as pb

FIXTURES = Path(__file__).parent / "fixtures" / "plan-input"
SCRIPT = Path(__file__).resolve().parent.parent / "plan_batches.py"


def run_planner_via_cli(fixture_dir: Path) -> dict:
    result = subprocess.run(
        [
            "python3", str(SCRIPT),
            "--size", str(fixture_dir / "size.json"),
            "--stack", str(fixture_dir / "stack.json"),
        ],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def _plan(fixture: str) -> dict:
    size = json.loads((FIXTURES / fixture / "size.json").read_text())
    stack = json.loads((FIXTURES / fixture / "stack.json").read_text())
    rules = pb.load_priority_rules()
    return pb.build_plan(size, stack, rules)


def test_with_module_coverage_uses_tier_first():
    plan = _plan("with-coverage")
    batches = plan["batches"]
    first_batch_files = batches[0]["files"]
    first_tiers = {f["tier"] for f in first_batch_files}
    assert first_tiers == {"T1"}, f"Expected T1 first, got {first_tiers}"
    paths = [f["path"] for f in first_batch_files]
    assert paths.index("src/utils/parse.ts") < paths.index("src/utils/format.ts")
    assert plan["ordering_strategy"] == "tier-first"


def test_without_module_coverage_uses_p_tier_fallback():
    plan = _plan("no-coverage")
    batches = plan["batches"]
    first_batch_files = batches[0]["files"]
    first_priorities = {f["priority"] for f in first_batch_files}
    assert "P1" in first_priorities, f"Expected P1 first, got {first_priorities}"
    paths = [f["path"] for f in first_batch_files]
    assert "src/services/payment.ts" in paths
    assert plan["ordering_strategy"] == "p-tier-fallback"


def test_batch_ceiling_respected_t1():
    """T1 ceiling = 3. Con 2 file T1, devono essere in un solo batch."""
    plan = _plan("with-coverage")
    t1_batches = [b for b in plan["batches"] if b["tier"] == "T1"]
    for b in t1_batches:
        assert b["size"] <= 3


def test_empty_file_list_returns_empty_batches():
    rules = pb.load_priority_rules()
    plan = pb.build_plan({"file_list": []}, {"module_coverage": []}, rules)
    assert plan["batches"] == []
    assert plan["total_files"] == 0


def test_cli_entry_point():
    plan = run_planner_via_cli(FIXTURES / "with-coverage")
    assert plan["ordering_strategy"] == "tier-first"
    assert plan["total_files"] > 0
