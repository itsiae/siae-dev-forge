"""DETECT light: rileva fallimenti ripetuti nel transcript e scrive un record di staging.

Invocato dall'hook session-end. Esce 0 sempre (best-effort). Bounded per il budget 10s.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

from lib.retro.digest import iter_tool_events

ERROR_THRESHOLD = 3            # ≥3 error tool-result
REPEAT_THRESHOLD = 2          # stesso (tool,category) ≥2 volte
EVENT_CAP = 2000              # bound: max eventi processati (budget 10s)


def build_record(transcript_path: Path, session_id: str) -> dict | None:
    """Ritorna il record leggero se sopra soglia, altrimenti None."""
    error_count = 0
    cats: Counter[str] = Counter()
    pairs: Counter[tuple[str, str]] = Counter()
    for i, e in enumerate(iter_tool_events(transcript_path)):
        if i >= EVENT_CAP:
            break
        if not e.is_error:
            continue
        error_count += 1
        cats[e.category] += 1
        pairs[(e.tool, e.category)] += 1

    repeated = [[t, c, n] for (t, c), n in pairs.items() if n >= REPEAT_THRESHOLD]
    if error_count < ERROR_THRESHOLD and not repeated:
        return None
    return {
        "session_id": session_id,
        "transcript_path": str(transcript_path),
        "error_count": error_count,
        "top_categories": dict(cats.most_common(5)),
        "repeated_patterns": repeated,
    }


def write_record(record: dict, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{record['session_id']}.json"
    out.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return out


def main(argv: list[str]) -> int:
    """CLI: argv = [transcript_path, session_id]. Best-effort, exit 0 sempre."""
    try:
        transcript_path = Path(argv[1]) if len(argv) > 1 and argv[1] else None
        session_id = argv[2] if len(argv) > 2 and argv[2] else "unknown"
        if not transcript_path or not transcript_path.exists():
            return 0
        rec = build_record(transcript_path, session_id)
        if rec is None:
            return 0
        out_dir = Path(os.environ.get("HOME", "")) / ".claude" / "devforge-state" / "retro-pending"
        write_record(rec, out_dir)
    except Exception:
        return 0       # mai propagare: non bloccare il session-end
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
