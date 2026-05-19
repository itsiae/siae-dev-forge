#!/usr/bin/env python3
"""
ab_test.py — A/B testing description per skill.

Confronta description corrente (A) vs candidata (B)
eseguendo lo stesso trigger eval set su entrambe.
"""

import time
from pathlib import Path

from .trigger_eval import run_trigger_eval, read_skill_description


def run_ab_test(
    skill_name: str,
    eval_set: list[dict],
    plugin_root: Path,
    project_root: Path,
    description_b: str,
    runs_per_query: int = 5,
    num_workers: int = 8,
    timeout: int = 60,
    model: str | None = None,
) -> dict:
    """Confronta description A (current) vs B (candidate).

    Returns:
        {"skill", "variant_a": {...}, "variant_b": {...},
         "winner": "A"|"B"|"TIE", "delta": {...}}
    """
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    t0 = time.time()

    description_a = read_skill_description(str(plugin_root), skill_name) or ""

    # Run A (current)
    result_a = run_trigger_eval(
        skill_name=skill_name, eval_set=eval_set,
        plugin_root=plugin_root, project_root=project_root,
        runs_per_query=runs_per_query, num_workers=num_workers,
        timeout=timeout, model=model, description_override=None,
    )

    # Run B (candidate)
    result_b = run_trigger_eval(
        skill_name=skill_name, eval_set=eval_set,
        plugin_root=plugin_root, project_root=project_root,
        runs_per_query=runs_per_query, num_workers=num_workers,
        timeout=timeout, model=model, description_override=description_b,
    )

    sa = result_a["summary"]
    sb = result_b["summary"]

    accuracy_a = (sa.get("precision", 0) + sa.get("recall", 0)) / 2
    accuracy_b = (sb.get("precision", 0) + sb.get("recall", 0)) / 2

    if accuracy_b > accuracy_a + 0.02:
        winner = "B"
    elif accuracy_a > accuracy_b + 0.02:
        winner = "A"
    else:
        winner = "TIE"

    elapsed = time.time() - t0

    return {
        "skill": skill_name,
        "timestamp": timestamp,
        "variant_a": {
            "description": description_a[:200],
            "precision": sa.get("precision", 0),
            "recall": sa.get("recall", 0),
            "accuracy": round(accuracy_a, 3),
        },
        "variant_b": {
            "description": description_b[:200],
            "precision": sb.get("precision", 0),
            "recall": sb.get("recall", 0),
            "accuracy": round(accuracy_b, 3),
        },
        "winner": winner,
        "delta": {
            "precision": f"{sb.get('precision', 0) - sa.get('precision', 0):+.3f}",
            "recall": f"{sb.get('recall', 0) - sa.get('recall', 0):+.3f}",
            "accuracy": f"{accuracy_b - accuracy_a:+.3f}",
        },
        "runs_per_query": runs_per_query,
        "elapsed_s": round(elapsed, 1),
    }
