#!/usr/bin/env python3
"""
e2e_eval.py — L3 end-to-end evaluation: conversazione multi-turn + grading.

Simula workflow completi con turn user predefiniti,
poi usa grader.py per valutare lo stato finale.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .grader import grade


def run_conversation(
    turns: list[dict],
    setup: dict,
    eval_set_dir: Path,
    skill_name: str,
    timeout: int = 300,
    model: str | None = None,
) -> str:
    """Esegue conversazione multi-turn con claude --resume."""
    with tempfile.TemporaryDirectory(prefix=f"e2e_{skill_name}_") as tmpdir:
        if setup and setup.get("files"):
            fixture_base = eval_set_dir / setup.get("cwd", "fixtures")
            for fname in setup["files"]:
                src = fixture_base / fname
                if src.exists():
                    dst = Path(tmpdir) / fname
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)

        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        session_id = None
        last_output = ""

        for i, turn in enumerate(turns):
            cmd = [
                "claude", "-p", turn["content"],
                "--output-format", "text",
                "--permission-mode", "bypassPermissions",
                "--max-turns", "5",
            ]
            if model:
                cmd.extend(["--model", model])
            if session_id:
                cmd.extend(["--resume", session_id])

            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True,
                    timeout=timeout, env=env, cwd=tmpdir,
                )
                last_output = result.stdout.strip()

                if not session_id:
                    for line in (result.stderr or "").split("\n"):
                        if "session:" in line.lower() or "id:" in line.lower():
                            parts = line.strip().split()
                            if parts:
                                session_id = parts[-1]
                                break

            except subprocess.TimeoutExpired:
                return f"[TIMEOUT at turn {i}]"
            except Exception as e:
                return f"[ERROR at turn {i}: {e}]"

        return last_output


def run_e2e_eval(
    skill_name: str,
    eval_set: list[dict],
    eval_set_dir: Path,
    timeout: int = 300,
    model: str | None = None,
) -> dict:
    """Esegue L3 e2e eval: conversazione multi-turn + grading finale.

    Nessun runs_per_query — L3 e' costoso, 1 run per scenario.
    """
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    t0 = time.time()
    results = []

    for scenario in eval_set:
        turns = scenario["turns"]
        setup = scenario.get("setup", {})
        final_checks = scenario["final_checks"]
        pass_threshold = scenario.get("pass_threshold", 0.75)

        output = run_conversation(
            turns=turns, setup=setup, eval_set_dir=eval_set_dir,
            skill_name=skill_name, timeout=timeout, model=model,
        )

        if output.startswith("[TIMEOUT") or output.startswith("[ERROR"):
            results.append({
                "name": scenario.get("name", "unnamed"),
                "query": turns[0]["content"][:200] if turns else "",
                "scores": [],
                "weighted_score": 0.0,
                "pass": False,
                "error": output,
            })
            continue

        try:
            grade_result = grade(agent_output=output, criteria=final_checks)
            is_pass = grade_result["weighted_score"] >= pass_threshold
            results.append({
                "name": scenario.get("name", "unnamed"),
                "query": turns[0]["content"][:200] if turns else "",
                "scores": grade_result["scores"],
                "weighted_score": grade_result["weighted_score"],
                "pass": is_pass,
                "grader_reasoning": "; ".join(
                    s.get("reasoning", "") for s in grade_result.get("scores", [])
                ),
            })
        except RuntimeError as e:
            results.append({
                "name": scenario.get("name", "unnamed"),
                "query": turns[0]["content"][:200] if turns else "",
                "scores": [],
                "weighted_score": 0.0,
                "pass": False,
                "error": str(e),
            })

    elapsed = time.time() - t0
    passed = sum(1 for r in results if r["pass"])

    return {
        "skill": skill_name,
        "level": "L3",
        "timestamp": timestamp,
        "model": model or "default",
        "results": results,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
        },
        "metadata": {
            "timeout": timeout,
            "elapsed_s": round(elapsed, 1),
        },
    }
