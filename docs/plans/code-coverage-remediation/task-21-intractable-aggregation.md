# Task 21 — intractable.json aggregation + Block 9 surfacing

**Goal:** Script `aggregate_intractable.py` che fonde gli `intractable_flags` dei subagent (e di Phase 7) in `.code-coverage/intractable.json`, ed estende il Block 9 (Next Actions) di `SKILL.md` per mostrare i file intractable con la `suggested_strategy`. Chiude il loop: ciò che resta scoperto è esplicitato all'utente con l'azione consigliata, invece di sparire in un BEST_EFFORT opaco.

**WS:** WS-5 · **Dipendenze:** Task 14 (classify_intractable), Task 19 (OUTPUT CONTRACT).

## File coinvolti
- Crea: `skills/code-coverage/scripts/aggregate_intractable.py`
- Crea: `skills/code-coverage/scripts/tests/test_aggregate_intractable.py`
- Modifica: `skills/code-coverage/SKILL.md` (Block 9 — Next Actions)

## Step TDD

### Step 1 — Test fallente
Crea `skills/code-coverage/scripts/tests/test_aggregate_intractable.py`:

```python
import json
import aggregate_intractable as ai


def test_merge_dedup(tmp_path):
    fragments = [
        [{"path": "a.ts", "reason": "private", "suggested_strategy": "reflection"}],
        [{"path": "a.ts", "reason": "private", "suggested_strategy": "reflection"},  # dup
         {"path": "b.ts", "reason": "db", "suggested_strategy": "skip"}],
    ]
    merged = ai.merge(fragments)
    paths = sorted(f["path"] for f in merged["files"])
    assert paths == ["a.ts", "b.ts"]  # dedup su path


def test_write_file(tmp_path):
    out = ai.write_intractable(tmp_path, [[{"path": "x.ts", "reason": "r", "suggested_strategy": "s"}]])
    data = json.loads((tmp_path / ".code-coverage" / "intractable.json").read_text())
    assert data["files"][0]["path"] == "x.ts"
```

### Step 2 — Verifica che fallisce
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_aggregate_intractable.py -v`
Output atteso: ImportError → 2 FAILED.

### Step 3 — Implementa `scripts/aggregate_intractable.py`

```python
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
        for item in frag or []:
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
    repo = Path(sys.argv[1]).resolve()
    fragments = []
    for fp in sys.argv[2:]:
        try:
            fragments.append(json.loads(Path(fp).read_text()))
        except Exception:
            continue
    merged = write_intractable(repo, fragments)
    print(json.dumps({"intractable_count": len(merged["files"])}))


if __name__ == "__main__":
    main()
```

### Step 4 — Verifica che passa
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_aggregate_intractable.py -v`
Output atteso: `2 passed`.

## Step 5 — Block 9 in SKILL.md
Trova il Block 9 (Next Actions, riga ~196) e aggiungi la condizione di surfacing:
```markdown
- Block 9 (`Next Actions`): include i file di `.code-coverage/intractable.json` con la
  rispettiva `suggested_strategy`. Esempio:
  "Intractable (manual): src/dao/X.ts → reflection per private methods;
   src/dao/Y.ts → requires DB fixture (skip in unit)."
  Aggiungi anche: follow-up batch attivo, PRESERVE_EXISTING entries, manual tests suggeriti.
```

### Step 6 — Commit
```
git add skills/code-coverage/scripts/aggregate_intractable.py skills/code-coverage/scripts/tests/test_aggregate_intractable.py skills/code-coverage/SKILL.md
git commit -m "feat(code-coverage): aggregate intractable flags + surface in Block 9 with suggested strategy"
```

## Criteri di accettazione
- [ ] `merge` deduplica per path (primo vince).
- [ ] `intractable.json` scritto con `files[]` (path/reason/suggested_strategy).
- [ ] Block 9 di SKILL.md mostra i file intractable con la strategia consigliata.
