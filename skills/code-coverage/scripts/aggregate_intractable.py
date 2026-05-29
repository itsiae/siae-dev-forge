#!/usr/bin/env python3
"""aggregate_intractable.py — fonde intractable_flags (subagent + Phase 7) in intractable.json.

Dedup su path (primo vince). Usage: aggregate_intractable.py <repo> <fragment.json> [...]
Ogni fragment è una lista di {path, reason, suggested_strategy}.
"""
import json
import sys
from pathlib import Path


def merge(fragments: list[list[dict]]) -> dict:
    seen: dict[str, dict] = {}
    for frag in fragments:
        if not isinstance(frag, list):
            continue  # fragment malformato (non-lista) → nessuna entry spuria
        for item in frag:
            if not isinstance(item, dict):
                continue  # item non-dict → ignora silenziosamente
            p = item.get("path")
            if p and p not in seen:
                seen[p] = {
                    "path": p,
                    "reason": item.get("reason", ""),
                    "suggested_strategy": item.get("suggested_strategy", ""),
                }
    return {"files": list(seen.values())}


def write_intractable(repo: Path, fragments: list[list[dict]]) -> dict:
    cc = repo / ".code-coverage"
    cc.mkdir(parents=True, exist_ok=True)
    merged = merge(fragments)
    (cc / "intractable.json").write_text(json.dumps(merged, indent=2))
    return merged


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: aggregate_intractable.py <repo> [fragment...]"}),
              file=sys.stderr)
        sys.exit(1)
    repo = Path(sys.argv[1]).resolve()
    fragments = []
    for fp in sys.argv[2:]:
        try:
            fragments.append(json.loads(Path(fp).read_text(encoding="utf-8", errors="replace")))
        except Exception:
            continue
    merged = write_intractable(repo, fragments)
    print(json.dumps({"intractable_count": len(merged["files"])}))


if __name__ == "__main__":
    main()
