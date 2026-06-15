"""Task 01 — adoption-analyzer.py --task-adoption-meta: legge il ledger di un task
e produce il meta JSON dell'evento task_adoption. Riusa CORE_SKILLS (single source)."""
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
ANALYZER = REPO_ROOT / "lib" / "adoption-analyzer.py"


def _run(task_id, home):
    return subprocess.run(
        [sys.executable, str(ANALYZER), "--task-adoption-meta", task_id],
        capture_output=True, text=True, env={"HOME": str(home), "PATH": "/usr/bin:/bin"},
    )


def _seed_ledger(home, task_id, invoked, validated, metadata=None):
    d = home / ".claude" / ".devforge-task-skills" / task_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "skills_invoked").write_text("\n".join(invoked) + ("\n" if invoked else ""))
    (d / "skills_validated").write_text("\n".join(validated) + ("\n" if validated else ""))
    if metadata:
        (d / "metadata").write_text(metadata)


def test_meta_shape_with_core_bools(tmp_path):
    _seed_ledger(
        tmp_path, "abc123def456",
        invoked=["siae-brainstorming", "siae-tdd"],
        validated=["siae-tdd"],
        metadata="branch_name=feat/x\ndesign_doc=docs/plans/x-design.md\n",
    )
    r = _run("abc123def456", tmp_path)
    assert r.returncode == 0, r.stderr
    meta = json.loads(r.stdout)
    assert meta["task_id"] == "abc123def456"
    assert meta["task_branch"] == "feat/x"
    assert meta["design_doc"] == "docs/plans/x-design.md"
    assert meta["skills_invoked"] == ["siae-brainstorming", "siae-tdd"]
    assert meta["skills_validated"] == ["siae-tdd"]
    csv = meta["core_skills_validated"]
    # 5 core keys present, bool, tdd=True others=False
    assert set(csv.keys()) == {
        "siae-brainstorming", "siae-tdd", "siae-git-workflow",
        "siae-verification", "siae-blind-review",
    }
    assert csv["siae-tdd"] is True
    assert csv["siae-brainstorming"] is False


def test_empty_ledger_prints_nothing(tmp_path):
    # AC3: ledger esiste ma vuoto → nessun output
    _seed_ledger(tmp_path, "emptytask001", invoked=[], validated=[])
    r = _run("emptytask001", tmp_path)
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_missing_task_prints_nothing(tmp_path):
    # AC2: task_id non esistente (fuori scope a monte) → nessun output
    r = _run("nonexistent99", tmp_path)
    assert r.returncode == 0
    assert r.stdout.strip() == ""


def test_core_list_is_single_source(tmp_path):
    # AC8: le chiavi core derivano da CORE_SKILLS del modulo, non da una lista duplicata.
    src = ANALYZER.read_text()
    assert "CORE_SKILLS" in src
    _seed_ledger(tmp_path, "t1", invoked=["siae-verification"], validated=["siae-verification"])
    meta = json.loads(_run("t1", tmp_path).stdout)
    assert meta["core_skills_validated"]["siae-verification"] is True
