#!/usr/bin/env python3
"""categorize_failure.py — categorizza failure stderr in Cat 1-6 deterministicamente.

Usage:
    python3 categorize_failure.py <stderr-file>
    python3 categorize_failure.py --stdin < stderr-stream

Output (stdout): JSON con schema:
    {
        "category": int (1-6) | null,
        "category_name": str | null,
        "signature": str,
        "captures": [str],
        "fix_steps": [str],
        "systemic_eligible": bool,
        "systemic_threshold_count": int,
        "raw_first_line": str,
        "error": str | null
    }

Exit code: 0 sempre.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
STRATEGIES_PATH = SKILL_ROOT / "assets" / "repair-strategies.json"


def load_strategies() -> dict:
    with open(STRATEGIES_PATH) as f:
        return json.load(f)


def normalize(error_message: str, normalize_rules: list | None = None) -> str:
    """Normalizza un messaggio d'errore in una signature deterministica.

    Strip path / timestamp / hex / line:col / ANSI escape.
    Tronca a 200 char.

    NOTA (C2 fix): prende le PRIME 3 RIGHE NON-VUOTE concatenate da \\n.
    Rationale: Vitest/Jest stampano line-1 con header tipo
    "FAIL src/foo.test.ts (3 tests | 2 failed)" e la vera assertion arriva
    5-15 righe dopo. Prendere solo line-1 produceva signature broken e
    grouping fallito (systemic-fix mai applicato).
    """
    if normalize_rules is None:
        normalize_rules = load_strategies().get("normalize_regex", [])

    non_empty_lines: list[str] = []
    for line in error_message.split("\n"):
        if line.strip():
            non_empty_lines.append(line)
        if len(non_empty_lines) >= 3:
            break
    sig = "\n".join(non_empty_lines)
    for rule in normalize_rules:
        sig = re.sub(rule["pattern"], rule["replace"], sig)

    sig = re.sub(r"\s+", " ", sig).strip()
    return sig[:200]


def categorize(stderr_content: str, strategies: dict) -> dict:
    """Categorizza in Cat 1-6. Ordine eval: Cat 6 (transient) PRIMA di 1-5
    per evitare false positive (es. ECONNRESET → dependency).
    """
    raw_lines = stderr_content.split("\n")
    raw_first_line = next((line for line in raw_lines if line.strip()), "")

    categories = strategies["categories"]
    cat6 = next((c for c in categories if c["id"] == 6), None)
    others = sorted([c for c in categories if c["id"] != 6], key=lambda c: c["id"])
    eval_order = ([cat6] if cat6 else []) + others

    for cat in eval_order:
        for pattern in cat["patterns"]:
            match = re.search(pattern, stderr_content, flags=re.MULTILINE | re.IGNORECASE)
            if match:
                signature = normalize(stderr_content, strategies.get("normalize_regex"))
                return {
                    "category": cat["id"],
                    "category_name": cat["name"],
                    "signature": signature,
                    "captures": list(match.groups()),
                    "fix_steps": cat["fix_steps"],
                    "systemic_eligible": cat.get("systemic_eligible", False),
                    "systemic_threshold_count": cat.get("systemic_threshold_count", 0),
                    "raw_first_line": raw_first_line[:300],
                    "error": None,
                }

    return {
        "category": None,
        "category_name": None,
        "signature": normalize(stderr_content, strategies.get("normalize_regex")),
        "captures": [],
        "fix_steps": ["Manual investigation required — no automatic categorization"],
        "systemic_eligible": False,
        "systemic_threshold_count": 0,
        "raw_first_line": raw_first_line[:300],
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stderr_file", nargs="?", type=Path,
                        help="File stderr. Se omesso, legge stdin.")
    parser.add_argument("--stdin", action="store_true", help="Forza lettura da stdin")
    args = parser.parse_args()

    if args.stdin or args.stderr_file is None:
        stderr_content = sys.stdin.read()
    else:
        if not args.stderr_file.exists():
            print(json.dumps({
                "category": None,
                "category_name": None,
                "error": f"File not found: {args.stderr_file}",
                "signature": "",
                "captures": [],
                "fix_steps": [],
                "systemic_eligible": False,
                "systemic_threshold_count": 0,
                "raw_first_line": "",
            }, indent=2))
            return 0
        stderr_content = args.stderr_file.read_text()

    strategies = load_strategies()
    result = categorize(stderr_content, strategies)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
