"""Test del breakglass tool-fail di hooks/review-evidence (ADR-1 Opzione C).

Il breakglass (env var DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS=1 OR state-file
~/.claude/.devforge-evidence-toolfail con auto-decremento N=count) rilascia il
block SOLO sui 5 fallimenti di tooling, MAI sui verdetti di qualità.

Trigger deterministico: collector fake via DEVFORGE_EVIDENCE_COLLECTOR_PATH.
- collector che esce 1  → tool-fail (collector crash, path 326)
- collector che scrive verdict.block=true ed esce 0 → verdetto di qualità
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
HOOK = REPO_ROOT / "hooks" / "review-evidence"
TOOLFAIL_FILE = ".devforge-evidence-toolfail"

CRASH_COLLECTOR = "import sys\nsys.exit(1)\n"
BLOCK_COLLECTOR = (
    "import sys, json, argparse\n"
    "p = argparse.ArgumentParser()\n"
    "p.add_argument('--sha'); p.add_argument('--base'); p.add_argument('--dirty')\n"
    "p.add_argument('--out')\n"
    "a, _ = p.parse_known_args()\n"
    "json.dump({'schema_version':'1.0','sha':a.sha,'verdict':{'block':True,"
    "'block_reasons':['coverage_below_threshold:45<60'],'warnings':[]}}, open(a.out,'w'))\n"
    "sys.exit(0)\n"
)


def _run_hook(stdin_json: dict, env: dict | None = None) -> tuple[int, str, str]:
    full_env = os.environ.copy()
    full_env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    if env:
        full_env.update(env)
    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(stdin_json),
        capture_output=True, text=True, env=full_env, timeout=20,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _repo(tmp_path, collector_src: str) -> dict:
    """Git repo pulito + collector fake. Ritorna env+envelope per gh pr edit."""
    _git(["init"], tmp_path)
    _git(["config", "user.email", "x@x"], tmp_path)
    _git(["config", "user.name", "x"], tmp_path)
    _git(["config", "commit.gpgsign", "false"], tmp_path)
    (tmp_path / "f.txt").write_text("x")
    _git(["add", "."], tmp_path)
    _git(["commit", "-m", "x"], tmp_path)
    (tmp_path / ".claude").mkdir(exist_ok=True)
    collector = tmp_path / "fake_collector.py"
    collector.write_text(collector_src)
    return {
        "envelope": {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                     "command": "gh pr edit 1 --add-label x", "cwd": str(tmp_path)},
        "env": {"HOME": str(tmp_path),
                "DEVFORGE_EVIDENCE_COLLECTOR_PATH": str(collector)},
    }


# --- tool-fail: collector crash (path 326) -------------------------------------

def test_breakglass_absent_still_blocks_toolfail(tmp_path):
    ctx = _repo(tmp_path, CRASH_COLLECTOR)
    rc, out, _ = _run_hook(ctx["envelope"], env=ctx["env"])
    parsed = json.loads(out or "{}")
    assert parsed.get("decision") == "block", f"atteso block senza breakglass: {parsed}"


def test_breakglass_env_allows_toolfail(tmp_path):
    ctx = _repo(tmp_path, CRASH_COLLECTOR)
    ctx["env"]["DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS"] = "1"
    rc, out, _ = _run_hook(ctx["envelope"], env=ctx["env"])
    parsed = json.loads(out or "{}")
    assert parsed.get("decision") != "block", f"breakglass env non ha rilasciato: {parsed}"


def test_breakglass_statefile_decrements(tmp_path):
    ctx = _repo(tmp_path, CRASH_COLLECTOR)
    bg = tmp_path / ".claude" / TOOLFAIL_FILE
    bg.write_text("N=2")
    rc, out, _ = _run_hook(ctx["envelope"], env=ctx["env"])
    parsed = json.loads(out or "{}")
    assert parsed.get("decision") != "block", f"state-file non ha rilasciato: {parsed}"
    assert bg.read_text().strip() == "N=1", f"decremento errato: {bg.read_text()!r}"


def test_breakglass_statefile_exhausted_removed(tmp_path):
    ctx = _repo(tmp_path, CRASH_COLLECTOR)
    bg = tmp_path / ".claude" / TOOLFAIL_FILE
    bg.write_text("N=1")
    rc, out, _ = _run_hook(ctx["envelope"], env=ctx["env"])
    parsed = json.loads(out or "{}")
    assert parsed.get("decision") != "block", f"state-file N=1 non ha rilasciato: {parsed}"
    assert not bg.exists(), "state-file esaurito non rimosso"


# --- GUARD: il breakglass NON rilascia i verdetti di qualità -------------------

def test_breakglass_does_not_release_quality_block(tmp_path):
    ctx = _repo(tmp_path, BLOCK_COLLECTOR)
    ctx["env"]["DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS"] = "1"
    rc, out, _ = _run_hook(ctx["envelope"], env=ctx["env"])
    parsed = json.loads(out or "{}")
    assert parsed.get("decision") == "block", \
        f"GUARD violato: breakglass ha rilasciato un verdetto di qualità: {parsed}"


# --- strutturale: helper presente nei 5 path tool-fail + 1 def -----------------

def test_breakglass_helper_wired_in_all_paths():
    src = HOOK.read_text()
    calls = src.count("_devforge_evidence_toolfail_breakglass")
    assert calls >= 6, f"atteso 1 def + 5 call dell'helper, trovati {calls}"
    # Il path jq deve usare un branch builtin (echo), non dipendere da jq.
    assert "DEVFORGE_EVIDENCE_TOOLFAIL_BREAKGLASS" in src
