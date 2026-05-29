import json
import subprocess
import sys
from pathlib import Path

import classify_coverage_mode as ccm
import plan_batches as pb

SCRIPTS_DIR = Path(__file__).resolve().parents[1]


def test_branch_heavy_forces_branch_priority():
    assert ccm.classify(branch_operator_count=30, current_line=10, current_branch=10,
                         target_line=70, target_branch=60) == "branch-priority"


def test_line_done_branch_far():
    # line quasi al target (60 >= 70*0.85=59.5), branch lontana (40 < 60*0.8=48)
    assert ccm.classify(branch_operator_count=5, current_line=60, current_branch=40,
                        target_line=70, target_branch=60) == "branch-priority"


def test_default_line_priority():
    assert ccm.classify(branch_operator_count=0, current_line=10, current_branch=10,
                        target_line=70, target_branch=60) == "line-priority"


# ---------------------------------------------------------------------------
# Integration tests for main() — BLOCKER fix (batch-plan key "batches" vs
# "pending_batches") and missing-file graceful handling
# ---------------------------------------------------------------------------

def _build_real_batch_plan(tmp_path: Path) -> dict:
    """Build a real batch-plan via plan_batches.build_plan() so we use the actual key."""
    size_data = {
        "file_list": [
            {"path": "src/dao/LocaleDao.ts", "tier": "T2", "priority": "P2", "loc": 300},
            {"path": "src/services/payment.ts", "tier": "T1", "priority": "P1", "loc": 500},
        ]
    }
    stack_data = {"module_coverage": []}
    rules = pb.load_priority_rules()
    return pb.build_plan(size_data, stack_data, rules)


def test_main_classifies_files_from_real_batch_plan(tmp_path):
    """main() deve classificare i file usando la chiave 'batches' prodotta da build_plan."""
    cc_dir = tmp_path / ".code-coverage"
    cc_dir.mkdir()

    plan = _build_real_batch_plan(tmp_path)
    # Verifica precondizione: il piano usa "batches", NON "pending_batches"
    assert "batches" in plan, "build_plan deve produrre la chiave 'batches'"
    assert plan["batches"], "il piano deve contenere almeno un batch"

    (cc_dir / "batch-plan.json").write_text(json.dumps(plan))
    (cc_dir / "stack.json").write_text(json.dumps({
        "pre_existing_coverage_pct": 10,
        "pre_existing_branch_pct": 5,
    }))
    (cc_dir / "user-choice.json").write_text(json.dumps({
        "target_line": 70,
        "target_branch": 60,
    }))

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "classify_coverage_mode.py"), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"main() ha crashato: {result.stderr}"

    updated_plan = json.loads((cc_dir / "batch-plan.json").read_text())
    all_files = [f for b in updated_plan.get("batches", []) for f in b.get("files", [])]
    assert all_files, "nessun file nel batch-plan aggiornato"
    for f in all_files:
        assert f.get("coverage_mode") is not None, (
            f"coverage_mode è None per {f.get('path')}: main() ha iterato 0 batch "
            f"(usa 'pending_batches' invece di 'batches'?)"
        )


def test_main_no_crash_when_batch_plan_missing(tmp_path):
    """main() NON deve crashare con FileNotFoundError se batch-plan.json è assente."""
    cc_dir = tmp_path / ".code-coverage"
    cc_dir.mkdir()
    # Niente batch-plan.json — solo stack e user-choice minimi
    (cc_dir / "stack.json").write_text(json.dumps({}))
    (cc_dir / "user-choice.json").write_text(json.dumps({}))

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "classify_coverage_mode.py"), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"main() ha terminato con exit {result.returncode} invece di 0:\n{result.stderr}"
    )
    # L'output deve essere JSON valido con un campo "error" o simile
    out = result.stdout.strip()
    assert out, "main() non ha prodotto output"
    data = json.loads(out)
    assert isinstance(data, dict), "l'output deve essere un oggetto JSON"


# ---------------------------------------------------------------------------
# ISSUE-8: argv guard — classify_coverage_mode.py senza argv deve uscire con 1
# ---------------------------------------------------------------------------

def test_argv_guard_no_args():
    """classify_coverage_mode.py senza argomenti deve scrivere JSON su stderr e uscire con 1."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "classify_coverage_mode.py")],
        capture_output=True, text=True,
    )
    assert result.returncode == 1, (
        f"atteso exit 1 senza argv, got {result.returncode}"
    )
    err = json.loads(result.stderr)
    assert "error" in err, "stderr deve contenere JSON con chiave 'error'"
