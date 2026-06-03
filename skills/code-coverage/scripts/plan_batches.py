#!/usr/bin/env python3
"""plan_batches.py — produce batch plan ordinato secondo D1 conditional ordering.

Usage:
    python3 plan_batches.py --size <size.json> --stack <stack.json>
    python3 plan_batches.py --size .code-coverage/size.json --stack .code-coverage/stack.json

Output (stdout): JSON batch plan con schema:
    {
        "ordering_strategy": "tier-first" | "p-tier-fallback" | "none",
        "total_files": int,
        "batches": [
            {"id": int, "tier": str, "priority": str, "files": [...], "size": int}
        ],
        "deferred": []
    }
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
PRIORITY_RULES_PATH = SKILL_ROOT / "assets" / "priority-rules.json"


def _glob_to_regex(pattern: str) -> str:
    """Converte glob in regex senza cascade re-replace.

    Strategia sentinel-based: rimpiazza `**/` e `**` con sentinel uniche prima
    di sostituire `*` singolo, poi ripristina le sentinel a `.*/` / `.*`.
    Evita il bug del triple-cascade replace che trasforma `.*` in `.[^/]*`.
    """
    SENT_DSTAR_SLASH = "\x00DSTARSLASH\x00"
    SENT_DSTAR = "\x00DSTAR\x00"
    s = pattern.replace("**/", SENT_DSTAR_SLASH).replace("**", SENT_DSTAR)
    s = s.replace("*", "[^/]*")
    return s.replace(SENT_DSTAR, ".*").replace(SENT_DSTAR_SLASH, ".*/")


def load_priority_rules() -> dict:
    with open(PRIORITY_RULES_PATH) as f:
        return json.load(f)


def build_batches(file_list: list, ceilings: dict) -> list:
    """Raggruppa file_list (già ordinato) in batch rispettando il ceiling per tier."""
    batches = []
    batch_id = 1
    current_batch: list = []
    current_tier = None

    for f in file_list:
        f_tier = f.get("tier", "T4")
        ceiling = ceilings.get(f_tier, 1)

        if current_tier is None:
            current_tier = f_tier

        if f_tier != current_tier or len(current_batch) >= ceiling:
            if current_batch:
                batches.append({
                    "id": batch_id,
                    "tier": current_tier,
                    "priority": current_batch[0].get("priority"),
                    "files": current_batch,
                    "size": len(current_batch),
                    "status": "pending",
                    "assigned_to": None,
                    "completed_by": None,
                    "completed_at": None,
                })
                batch_id += 1
                current_batch = []
            current_tier = f_tier

        current_batch.append(f)

    if current_batch:
        batches.append({
            "id": batch_id,
            "tier": current_tier,
            "priority": current_batch[0].get("priority"),
            "files": current_batch,
            "size": len(current_batch),
            "status": "pending",
            "assigned_to": None,
            "completed_by": None,
            "completed_at": None,
        })

    return batches


def is_skipped(path: str, skip_patterns: list) -> bool:
    for pattern in skip_patterns:
        regex = _glob_to_regex(pattern)
        if re.search(regex, path):
            return True
    return False


def build_plan(size_data: dict, stack_data: dict, rules: dict) -> dict:
    file_list = size_data.get("file_list", [])
    if not file_list:
        return {"ordering_strategy": "none", "total_files": 0, "batches": [], "deferred": []}

    ordering_constants = rules.get("ordering_constants", {})
    tier_order = ordering_constants.get("tier_order", {"T1": 0, "T2": 1, "T3": 2, "T4": 3})
    priority_order = ordering_constants.get("priority_order", {"P1": 0, "P2": 1, "P3": 2})
    ceilings = ordering_constants.get("batch_ceiling_per_tier", {"T1": 3, "T2": 2, "T3": 1, "T4": 1})

    has_module_coverage = bool(stack_data.get("module_coverage"))

    if has_module_coverage:
        sorted_files = sorted(
            file_list,
            key=lambda f: (
                tier_order.get(f.get("tier", "T4"), 4),
                -float(f.get("priority_score", f.get("loc", 0))),
            ),
        )
        ordering_strategy = "tier-first"
    else:
        sorted_files = sorted(
            file_list,
            key=lambda f: (
                priority_order.get(f.get("priority", "P3"), 3),
                -int(f.get("loc", 0)),
            ),
        )
        ordering_strategy = "p-tier-fallback"

    skip_patterns = rules.get("skip_patterns", [])
    deferred = [f for f in sorted_files if is_skipped(f["path"], skip_patterns)]
    eligible = [
        {**f, "branch_operator_count": f.get("branch_operator_count", None),
               "coverage_mode": f.get("coverage_mode", None)}
        for f in sorted_files if not is_skipped(f["path"], skip_patterns)
    ]

    batches = build_batches(eligible, ceilings)

    return {
        "ordering_strategy": ordering_strategy,
        "total_files": len(eligible),
        "batches": batches,
        "deferred": deferred,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=Path, required=True, help="Path a size.json")
    parser.add_argument("--stack", type=Path, required=True, help="Path a stack.json")
    parser.add_argument("--out", type=Path, default=None, help="Output path (default: stdout)")
    args = parser.parse_args()

    if not args.size.exists():
        print(json.dumps({"error": f"size file not found: {args.size}"}), file=sys.stderr)
        return 1
    if not args.stack.exists():
        print(json.dumps({"error": f"stack file not found: {args.stack}"}), file=sys.stderr)
        return 1

    try:
        size_data = json.loads(args.size.read_text())
        stack_data = json.loads(args.stack.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(json.dumps({"error": f"input parse error: {e}"}), file=sys.stderr)
        return 1
    rules = load_priority_rules()

    plan = build_plan(size_data, stack_data, rules)
    output = json.dumps(plan, indent=2)

    if args.out:
        args.out.write_text(output)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
