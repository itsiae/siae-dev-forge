# Task 15 — max_iter scaling + repair-strategies categoria 13

**Goal:** Sostituire l'hardcode "max 3 iterazioni" di Phase 7 con `max_iter = min(10, max(3, ceil(batches × 1.5)))` (in `phase-7-repair.md` e `SKILL.md`), e aggiungere a `repair-strategies.json` la categoria 13 `branch_gap_stall`. Risolve gap 6.2/R2 (3 iter insufficienti per VERY_LARGE). Convergenza Agent C+D+B.

**WS:** WS-4 · **Dipendenze:** nessuna (isolato).

## File coinvolti
- Modifica: `skills/code-coverage/references/phase-7-repair.md` (riga ~11, budget)
- Modifica: `skills/code-coverage/SKILL.md` (riga ~187, Phase 7)
- Modifica: `skills/code-coverage/assets/repair-strategies.json` (categoria 13)
- Modifica: `skills/code-coverage/scripts/tests/test_categorize_failure.py` (verifica presenza categoria 13 nel JSON)

## Prerequisito di lettura
Leggi `references/phase-7-repair.md` (cerca "max 3 iterazioni" o "Max 3 iter") e `SKILL.md` (cerca "Max 3 iter") per i punti esatti.

## Step 1 — Test fallente (asset JSON)
In `skills/code-coverage/scripts/tests/test_categorize_failure.py` aggiungi:

```python
import json
from pathlib import Path


def test_repair_strategies_has_branch_gap_stall():
    p = Path(__file__).resolve().parents[2] / "assets" / "repair-strategies.json"
    data = json.loads(p.read_text())
    # struttura: lista di categorie o dict con "categories"
    cats = data if isinstance(data, list) else data.get("categories", data.get("strategies", []))
    ids = [c.get("id") for c in cats] if isinstance(cats, list) else list(cats.keys())
    assert 13 in ids or "13" in [str(i) for i in ids], "manca categoria 13 branch_gap_stall"
```

### Step 2 — Verifica che fallisce
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_categorize_failure.py::test_repair_strategies_has_branch_gap_stall -v`
Output atteso: FAILED (categoria 13 assente).

### Step 3 — Implementa

**3a.** In `assets/repair-strategies.json`, aggiungi la categoria (adatta alla struttura reale — lista o dict):
```json
{
  "id": 13,
  "name": "branch_gap_stall",
  "patterns": [],
  "description": "Test passano ma branch coverage non sale dopo N iter. Non è un test failure: gap strutturale. Trigger: progress guard locale stall.",
  "fix_steps": [
    "Run classify_intractable.py per determinare la tecnica",
    "NEEDS_REFLECTION → test reflection su private methods",
    "NEEDS_CLASS_MOCK → vi.mock factory per classi inline",
    "NEEDS_TZ_MOCK → mock Intl/TZ via importOriginal",
    "INTRACTABLE_DB_DEPENDENT → marcare intractable e skippare"
  ],
  "systemic_eligible": false,
  "manual_hints": {
    "NEEDS_REFLECTION": "(inst as unknown as {m:Fn}).m.call(inst, fixture)",
    "NEEDS_CLASS_MOCK": "vi.mock('<path>', () => ({Class: vi.fn().mockImplementation(() => ({...}))}))",
    "NEEDS_TZ_MOCK": "vi.mock utils importOriginal, override getItalyOffset/addItalyOffset",
    "INTRACTABLE_DB_DEPENDENT": "Requires real DB; skip or integration test",
    "INTRACTABLE_UNKNOWN": "Manual investigation required"
  }
}
```

**3b.** In `references/phase-7-repair.md`, sostituisci `max 3 iterazioni totali` (riga ~11) con:
```markdown
- **max_iter = min(10, max(3, ceil(len(batch-plan.json.batches) × 1.5)))**
  (letto all'ingresso Phase 7; batch-plan.json assente → fallback 3)
- **max 1 full coverage run per iterazione**
- **hard cap 10 iter (budget contesto)**

Budget init (eseguire all'ingresso Phase 7, nessun coverage run extra):
```python
import json, math, pathlib
bp = pathlib.Path(".code-coverage/batch-plan.json")
n = len(json.loads(bp.read_text()).get("batches", [])) if bp.exists() else 0
MAX_ITER = min(10, max(3, math.ceil(n * 1.5))) if n else 3
# Log: [phase7] max_iter=<MAX_ITER> batches=<n>
```
```

**3c.** In `SKILL.md` (riga ~187), sostituisci `Max 3 iter, max 1 full coverage run/iter.` con:
```markdown
Max iter = min(10, max(3, ceil(batch_plan.batches.length × 1.5))) — letto da
.code-coverage/batch-plan.json (fallback 3). Max 1 full coverage run/iter.
```

### Step 4 — Verifica che passa
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_categorize_failure.py -v`
Output atteso: tutti `passed`.
Run: `grep -q "min(10, max(3" skills/code-coverage/references/phase-7-repair.md && echo OK` → `OK`.
Run: `grep -q "batch_plan.batches.length × 1.5" skills/code-coverage/SKILL.md && echo OK` → `OK`.

### Step 5 — Commit
```
git add skills/code-coverage/references/phase-7-repair.md skills/code-coverage/SKILL.md skills/code-coverage/assets/repair-strategies.json skills/code-coverage/scripts/tests/test_categorize_failure.py
git commit -m "feat(code-coverage): scale Phase 7 max_iter by batch count + add branch_gap_stall strategy"
```

## Criteri di accettazione
- [ ] `repair-strategies.json` ha categoria 13 `branch_gap_stall` con `manual_hints` per ogni NEEDS_*.
- [ ] `phase-7-repair.md` e `SKILL.md` riportano la formula `min(10, max(3, ceil(batches × 1.5)))`.
- [ ] VERY_LARGE 3 batch → 5 iter; 6 batch → 9 iter; SMALL → 3 (verificabile a mano dalla formula).
