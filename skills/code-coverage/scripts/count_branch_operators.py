#!/usr/bin/env python3
"""count_branch_operators.py — conta ??/||/&&/?: in un file TS/JS (regex AST-lite).

Esclude righe di commento singola (//), import e re-export puri, e blocchi /* */.
I re-export puri esclusi sono: `export { ... }`, `export * from ...`,
`export default <identificatore>` (senza corpo con operatori).
Le righe `export const`, `export function`, `export class` con operatori inline
vengono conteggiate normalmente.
NON gestisce annidamenti profondi: accettabile per DAO/mapper (post-mortem R6).
Soglia branch_heavy: count > 20.

Limiti noti (regex AST-lite): operatori dentro string literal possono produrre
falsi positivi; `?` a fine riga e split multi-riga possono dare falsi negativi.
Accettabile per DAO/mapper.

Usage: count_branch_operators.py <source_file>
Output JSON: {"file": path, "count": N, "by_operator": {...}, "branch_heavy": bool}
"""
import json
import re
import sys
from pathlib import Path

BRANCH_HEAVY_THRESHOLD = 20

_RE = {
    "??": re.compile(r"\?\?"),
    "||": re.compile(r"\|\|"),
    "&&": re.compile(r"&&"),
}

# Pattern per righe da escludere: import, re-export puri.
# NON escludi export const/function/class/let/var che possono contenere operatori.
_SKIP_LINE_RE = re.compile(
    r"^(?:"
    r"import\s"                      # import statement
    r"|export\s*\{[^}]*\}"           # export { A, B }
    r"|export\s+\*\s+from\s"         # export * from '...'
    r"|export\s+default\s+\w+\s*;?"  # export default Identifier (no body)
    r")"
)


def _strip_block_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def count_operators(text: str) -> dict:
    text = _strip_block_comments(text)
    by_op = {"??": 0, "||": 0, "&&": 0, "?:": 0}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("//") or _SKIP_LINE_RE.match(stripped):
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
