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


def test_is_skipped_returns_false_when_no_pattern_matches():
    """plan_batches.py:94 — fallback return False quando nessun pattern matcha."""
    assert pb.is_skipped("src/foo.ts", []) is False
    assert pb.is_skipped("src/foo.ts", ["*.py", "test_*.js"]) is False


def test_is_skipped_returns_true_when_pattern_matches():
    """plan_batches.py:92-93 — return True quando pattern matcha."""
    assert pb.is_skipped("src/test_foo.py", ["test_*.py"]) is True
    assert pb.is_skipped("dist/bundle.js", ["dist/*"]) is True


def _make_size_stack(tmp_path, file_list=None, module_coverage=None):
    size = tmp_path / "size.json"
    size.write_text(json.dumps({"file_list": file_list or []}))
    stack = tmp_path / "stack.json"
    stack.write_text(json.dumps({"module_coverage": module_coverage or []}))
    return size, stack


def test_main_size_file_missing_returns_1(tmp_path, monkeypatch):
    """plan_batches.py:150-152 — error path se --size file not exists."""
    import sys
    _, stack = _make_size_stack(tmp_path)
    nonexistent = tmp_path / "missing-size.json"
    monkeypatch.setattr(sys, "argv", ["plan_batches.py", "--size", str(nonexistent), "--stack", str(stack)])
    assert pb.main() == 1


def test_main_stack_file_missing_returns_1(tmp_path, monkeypatch):
    """plan_batches.py:153-155 — error path se --stack file not exists."""
    import sys
    size, _ = _make_size_stack(tmp_path)
    nonexistent = tmp_path / "missing-stack.json"
    monkeypatch.setattr(sys, "argv", ["plan_batches.py", "--size", str(size), "--stack", str(nonexistent)])
    assert pb.main() == 1


def test_main_invalid_json_returns_1(tmp_path, monkeypatch):
    """plan_batches.py:160-162 — error path su JSONDecodeError."""
    import sys
    size = tmp_path / "size.json"
    size.write_text("this is not json {")
    stack = tmp_path / "stack.json"
    stack.write_text("{}")
    monkeypatch.setattr(sys, "argv", ["plan_batches.py", "--size", str(size), "--stack", str(stack)])
    assert pb.main() == 1


def test_main_writes_to_out_file_when_specified(tmp_path, monkeypatch):
    """plan_batches.py:168-169 — write to --out path invece di stdout."""
    import sys
    size, stack = _make_size_stack(tmp_path)
    out = tmp_path / "plan.json"
    monkeypatch.setattr(
        sys, "argv",
        ["plan_batches.py", "--size", str(size), "--stack", str(stack), "--out", str(out)],
    )
    assert pb.main() == 0
    assert out.exists()
    plan = json.loads(out.read_text())
    assert plan["ordering_strategy"] == "none"
    assert plan["total_files"] == 0


def test_main_prints_to_stdout_when_no_out(tmp_path, monkeypatch, capsys):
    """plan_batches.py:170-171 — stdout default quando --out non specificato."""
    import sys
    size, stack = _make_size_stack(tmp_path)
    monkeypatch.setattr(sys, "argv", ["plan_batches.py", "--size", str(size), "--stack", str(stack)])
    assert pb.main() == 0
    captured = capsys.readouterr()
    plan = json.loads(captured.out)
    assert plan["batches"] == []
    assert plan["deferred"] == []


def test_batch_has_multiagent_and_branch_fields():
    """Task-08: ogni batch ha status/assigned_to/completed_by/completed_at;
    ogni file ha branch_operator_count e coverage_mode (default None)."""
    rules = pb.load_priority_rules()
    size_data = {
        "file_list": [
            {"path": "src/dao/LocaleDao.ts", "tier": "T2", "priority": "P2", "loc": 300}
        ]
    }
    stack_data = {"module_coverage": []}
    plan = pb.build_plan(size_data, stack_data, rules)

    assert plan["batches"], "nessun batch prodotto"
    batch = plan["batches"][0]

    # campi multi-agente sul batch
    assert batch["status"] == "pending", f"status atteso 'pending', trovato {batch.get('status')!r}"
    assert batch["assigned_to"] is None
    assert batch["completed_by"] is None
    assert batch["completed_at"] is None

    # campi branch-aware sul file
    f = batch["files"][0]
    assert "branch_operator_count" in f, "branch_operator_count mancante nel file"
    assert f["branch_operator_count"] is None
    assert "coverage_mode" in f, "coverage_mode mancante nel file"
    assert f["coverage_mode"] is None


def test_e2e_with_estimate_size_real_output(tmp_path):
    """E2E: verifica che estimate_size.py emetta REALMENTE tier+priority,
    e che plan_batches.py possa consumarli senza fixture hand-written.
    Previene regressione: fixture pre-cotti potrebbero mascherare un
    estimate_size che non emette i campi.
    """
    import subprocess

    # Crea micro-repo con file in dirs riconoscibili
    (tmp_path / "src" / "services").mkdir(parents=True)
    (tmp_path / "src" / "utils").mkdir(parents=True)
    (tmp_path / "src" / "handlers").mkdir(parents=True)
    (tmp_path / "src" / "services" / "payment.ts").write_text("export class P {}")
    (tmp_path / "src" / "utils" / "format.ts").write_text("export const f = (x) => x")
    (tmp_path / "src" / "handlers" / "api.ts").write_text(
        "import { Handler } from 'aws-lambda'; export const handler: Handler = async () => {}"
    )

    # Run estimate_size.py
    estimate_script = SCRIPT.parent / "estimate_size.py"
    result = subprocess.run(
        ["python3", str(estimate_script), str(tmp_path), "--file-list"],
        capture_output=True, text=True, check=True,
    )
    size_data = json.loads(result.stdout)

    # Verifica che TUTTI i file abbiano tier+priority popolati (not fallback "T4"/"P3")
    assert size_data["file_list"], "file_list vuoto"
    for f in size_data["file_list"]:
        assert "tier" in f, f"tier mancante in {f['path']}"
        assert "priority" in f, f"priority mancante in {f['path']}"
        assert f["tier"] in {"T1", "T2", "T3", "T4"}, f"tier invalido: {f['tier']}"
        assert f["priority"] in {"P1", "P2", "P3"}, f"priority invalida: {f['priority']}"

    # Sanity check classifier output reale
    by_path = {f["path"]: f for f in size_data["file_list"]}
    assert by_path["src/handlers/api.ts"]["tier"] == "T4"
    assert by_path["src/handlers/api.ts"]["priority"] == "P1"
    assert by_path["src/utils/format.ts"]["tier"] == "T1"
    assert by_path["src/utils/format.ts"]["priority"] == "P2"

    # Run plan_batches.py con questo size_data reale (no fixture pre-cotti)
    stack_data = {"module_coverage": [{"path": "src/utils/format.ts", "lines_pct": 0}]}
    rules = pb.load_priority_rules()
    plan = pb.build_plan(size_data, stack_data, rules)

    # Con module_coverage non-empty → tier-first
    assert plan["ordering_strategy"] == "tier-first"
    # Primo batch deve essere T1 (tier-first ordering)
    assert plan["batches"][0]["tier"] == "T1"
