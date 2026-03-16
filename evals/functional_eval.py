#!/usr/bin/env python3
"""
functional_eval.py — L2 functional evaluation: executor + grader.

Esegue claude -p con query realistiche, cattura output,
poi usa grader.py (Opus 4.5) per valutare la qualita'.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .grader import grade


def run_executor(
    query: str,
    setup: dict,
    skill_name: str,
    eval_set_dir: Path,
    timeout: int = 120,
    model: str | None = None,
) -> str:
    """Esegue claude -p con la query in un temp dir con fixtures."""
    with tempfile.TemporaryDirectory(prefix=f"eval_{skill_name}_") as tmpdir:
        if setup and setup.get("files"):
            fixture_base = eval_set_dir / setup.get("cwd", "fixtures")
            for fname in setup["files"]:
                src = fixture_base / fname
                if src.exists():
                    dst = Path(tmpdir) / fname
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)

        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        cmd = [
            "claude", "-p", query,
            "--output-format", "text",
            "--permission-mode", "bypassPermissions",
            "--max-turns", "3",
        ]
        if model:
            cmd.extend(["--model", model])

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=timeout, env=env, cwd=tmpdir,
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return "[TIMEOUT]"
        except Exception as e:
            return f"[ERROR: {e}]"


def run_functional_eval(
    skill_name: str,
    eval_set: list[dict],
    eval_set_dir: Path,
    runs_per_query: int = 3,
    timeout: int = 120,
    model: str | None = None,
) -> dict:
    """Esegue L2 functional eval: executor + grader per ogni scenario."""
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    t0 = time.time()
    results = []

    for scenario in eval_set:
        query = scenario["query"]
        setup = scenario.get("setup", {})
        criteria = scenario["criteria"]
        pass_threshold = scenario.get("pass_threshold", 0.70)

        scenario_scores = []
        for run_idx in range(runs_per_query):
            output = run_executor(
                query=query, setup=setup, skill_name=skill_name,
                eval_set_dir=eval_set_dir, timeout=timeout, model=model,
            )

            if output.startswith("[TIMEOUT]") or output.startswith("[ERROR"):
                scenario_scores.append({
                    "scores": [],
                    "weighted_score": 0.0,
                    "pass": False,
                    "error": output,
                })
                continue

            try:
                grade_result = grade(agent_output=output, criteria=criteria)
                is_pass = grade_result["weighted_score"] >= pass_threshold
                grade_result["pass"] = is_pass
                scenario_scores.append(grade_result)
            except RuntimeError as e:
                scenario_scores.append({
                    "scores": [],
                    "weighted_score": 0.0,
                    "pass": False,
                    "error": str(e),
                })

        valid_scores = [s for s in scenario_scores if "error" not in s]
        if valid_scores:
            avg_weighted = sum(s["weighted_score"] for s in valid_scores) / len(valid_scores)
            best_run = max(valid_scores, key=lambda s: s["weighted_score"])
        else:
            avg_weighted = 0.0
            best_run = scenario_scores[0] if scenario_scores else {"scores": [], "weighted_score": 0.0}

        results.append({
            "query": query[:200],
            "scores": best_run.get("scores", []),
            "weighted_score": round(avg_weighted, 3),
            "pass": avg_weighted >= pass_threshold,
            "grader_reasoning": "; ".join(
                s.get("reasoning", "") for s in best_run.get("scores", [])
            ),
            "runs": len(scenario_scores),
            "errors": [s["error"] for s in scenario_scores if "error" in s],
        })

    elapsed = time.time() - t0
    passed = sum(1 for r in results if r["pass"])
    avg_score = (sum(r["weighted_score"] for r in results) / len(results)) if results else 0

    return {
        "skill": skill_name,
        "level": "L2",
        "timestamp": timestamp,
        "model": model or "default",
        "results": results,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "avg_score": round(avg_score, 3),
        },
        "metadata": {
            "runs_per_query": runs_per_query,
            "timeout": timeout,
            "elapsed_s": round(elapsed, 1),
        },
    }
