#!/usr/bin/env python3
"""count_branch_operators.py — conta ??/||/&&/?: in un file TS/JS (regex AST-lite).

Esclude righe di commento singola (//), import/export e blocchi /* */.
NON gestisce annidamenti profondi: accettabile per DAO/mapper (post-mortem R6).
Soglia branch_heavy: count > 20.

Usage: count_branch_operators.py <source_file>
Output JSON: {"file": path, "count": N, "by_operator": {...}, "branch_heavy": bool}
"""
import json
import re
import sys
from pathlib import Path

BRANCH_HEAVY_THRESHOLD = 20

# ternario: ? ... : (escludendo ?. optional chaining e ?? )
_RE = {
    "??": re.compile(r"\?\?"),
    "||": re.compile(r"\|\|"),
    "&&": re.compile(r"&&"),
    "?:": re.compile(r"(?<![?.])\?(?!\.)[^?]"),  # ? non seguito/preceduto da ? o .
}


def _strip_block_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def count_operators(text: str) -> dict:
    text = _strip_block_comments(text)
    by_op = {"??": 0, "||": 0, "&&": 0, "?:": 0}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("import ") or stripped.startswith("export "):
            continue
        # rimuovi commento inline
        code = line.split("//", 1)[0]
        by_op["??"] += len(_RE["??"].findall(code))
        # || conteggia escludendo le occorrenze dentro ?? già contate non serve: operatori distinti
        by_op["||"] += len(_RE["||"].findall(code))
        by_op["&&"] += len(_RE["&&"].findall(code))
        # ternario: conta i "?" che non sono ?? né ?. — approssimazione
        q = code.replace("??", "").replace("?.", "")
        by_op["?:"] += q.count("?")
    count = sum(by_op.values())
    return {"count": count, "by_operator": by_op,
            "branch_heavy": count > BRANCH_HEAVY_THRESHOLD}


def main() -> None:
    src = Path(sys.argv[1])
    text = src.read_text(encoding="utf-8", errors="ignore")
    result = count_operators(text)
    result["file"] = str(src)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
