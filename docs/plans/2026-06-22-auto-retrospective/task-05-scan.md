# Task 05 — `lib/retro/scan.py` (DETECT light + soglia + staging)

**Goal:** Orchestratore DETECT: legge il transcript (bounded), conta error tool-result e pattern `(tool,category)` ripetuti, applica la soglia (≥3 errori OPPURE pattern ripetuto ≥2), e scrive un **record leggero** (conteggi+categorie+transcript_path, NO digest) in `~/.claude/devforge-state/retro-pending/<sid>.json`. Esegue come CLI (invocato dall'hook) ed esce 0 sempre.

**Dipende da:** Task 02 (classifier) + Task 04 (`iter_tool_events`). **File coinvolti:** crea `lib/retro/scan.py`, `tests/test_retro_scan.py`.

## Step TDD bite-sized

### Step 1 — Test fallente
Crea `tests/test_retro_scan.py`:
```python
import json
from pathlib import Path

from lib.retro.scan import build_record, write_record


def _make_transcript(tmp_path, n_errors):
    lines = []
    for i in range(n_errors):
        lines.append(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": f"t{i}", "name": "Bash", "input": {}}]}}))
        lines.append(json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": f"t{i}",
             "content": "bash: ENOENT no such file", "is_error": True}]}}))
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def test_below_threshold_returns_none(tmp_path):
    # 2 errori, nessun pattern ripetuto ≥2 di categorie diverse → sotto soglia
    p = tmp_path / "t.jsonl"
    p.write_text(
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "a", "name": "Bash", "input": {}}]}}) + "\n" +
        json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "a", "content": "Permission denied", "is_error": True}]}}) + "\n" +
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "b", "name": "Read", "input": {}}]}}) + "\n" +
        json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "b", "content": "command not found", "is_error": True}]}}),
        encoding="utf-8",
    )
    assert build_record(p, "sid1") is None     # 2 errori, categorie diverse, nessun ripetuto ≥2


def test_three_errors_triggers(tmp_path):
    p = _make_transcript(tmp_path, 3)
    rec = build_record(p, "sid2")
    assert rec is not None
    assert rec["error_count"] == 3
    assert rec["session_id"] == "sid2"
    assert rec["transcript_path"] == str(p)
    assert "digest" not in rec                  # record LEGGERO
    assert rec["top_categories"]["FILE_NOT_FOUND"] == 3


def test_repeated_pattern_triggers_under_three(tmp_path):
    p = _make_transcript(tmp_path, 2)           # 2x (Bash, FILE_NOT_FOUND) → pattern ripetuto ≥2
    rec = build_record(p, "sid3")
    assert rec is not None
    assert ["Bash", "FILE_NOT_FOUND", 2] in [list(x) for x in rec["repeated_patterns"]]


def test_write_record(tmp_path):
    rec = {"session_id": "sidW", "error_count": 3}
    out = write_record(rec, tmp_path / "retro-pending")
    assert out.name == "sidW.json"
    assert json.loads(out.read_text(encoding="utf-8"))["error_count"] == 3
```

### Step 2 — Verifica fallimento
Run: `python3 -m pytest tests/test_retro_scan.py -q`
Output atteso: `FAILED` — `ModuleNotFoundError: No module named 'lib.retro.scan'`.

### Step 3 — Implementa
Crea `lib/retro/scan.py`:
```python
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
```

### Step 4 — Verifica passa
Run: `python3 -m pytest tests/test_retro_scan.py -q`
Output atteso: `4 passed`.

### Step 5 — Commit
`git add lib/retro/scan.py tests/test_retro_scan.py && git commit -m "feat(retro): DETECT scan light con soglia errori/pattern + staging record"`

## Criteri di accettazione
- [ ] 2 errori di categorie diverse → `None` (sotto soglia). 3 errori → record con `error_count==3`.
- [ ] Pattern `(tool,category)` ripetuto ≥2 → record anche sotto i 3 errori.
- [ ] Record LEGGERO: contiene `session_id`, `transcript_path`, `error_count`, `top_categories`, `repeated_patterns`; NON contiene `digest`.
- [ ] `write_record` scrive `<session_id>.json`. `main()` esce sempre 0 (anche con transcript mancante/eccezioni).
- [ ] `tests/test_retro_scan.py` passa (4 test).
