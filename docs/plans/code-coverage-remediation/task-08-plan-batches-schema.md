# Task 08 — `plan_batches.py` schema + Phase 3 step 3b

**Goal:** `plan_batches.py` aggiunge a ogni file dei batch i campi `branch_operator_count` (null) e `coverage_mode` (null), e a ogni batch `status`/`assigned_to`/`completed_by`/`completed_at` (default null/"pending"). Documenta in `phase-3-sizing.md` lo "step 3b" (scan operatori + classify mode). Prepara il terreno per WS-2 (branch-aware) e WS-5 (multi-agente).

**WS:** WS-2 · **Dipendenze:** Task 05, Task 06.

## File coinvolti
- Modifica: `skills/code-coverage/scripts/plan_batches.py` (`build_plan`/`build_batches`)
- Modifica: `skills/code-coverage/references/phase-3-sizing.md` (sezione "Step 3b" + Batch Plan File Format)
- Modifica: `skills/code-coverage/scripts/tests/test_plan_batches.py`

## Prerequisito di lettura
Leggi `skills/code-coverage/scripts/plan_batches.py` per individuare la funzione che costruisce ogni dict batch e ogni dict file (le righe dove si emette `{"id":..., "files":[...]}`).

## Step TDD

### Step 1 — Test fallente
In `skills/code-coverage/scripts/tests/test_plan_batches.py` aggiungi:

```python
def test_batch_has_multiagent_and_branch_fields(tmp_path):
    import plan_batches
    # costruisci un input minimo coerente con la firma reale di build_plan
    # (adatta agli helper realmente usati nel file di test esistente)
    plan = plan_batches.build_plan_for_test(  # usa l'helper/firma reale
        files=[{"path": "src/dao/LocaleDao.ts", "tier": "T2", "priority": "P2", "loc": 300}]
    )
    batch = plan["pending_batches"][0]
    assert batch["status"] == "pending"
    assert batch["assigned_to"] is None
    assert batch["completed_by"] is None
    assert batch["completed_at"] is None
    f = batch["files"][0]
    assert "branch_operator_count" in f and f["branch_operator_count"] is None
    assert "coverage_mode" in f and f["coverage_mode"] is None
```
(Se `test_plan_batches.py` ha già helper per costruire piani, riusali invece di `build_plan_for_test`; l'importante è asserire i nuovi campi sul batch e sui file.)

### Step 2 — Verifica che fallisce
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_plan_batches.py -v`
Output atteso: il nuovo test FALLISce (KeyError su `status` / `branch_operator_count`).

### Step 3 — Implementa
In `scripts/plan_batches.py`, dove viene costruito ogni **batch** dict, aggiungi i campi default:
```python
batch = {
    "id": batch_id,
    "priority": priority,
    "tier": tier,
    "files": files,
    "status": "pending",
    "assigned_to": None,
    "completed_by": None,
    "completed_at": None,
}
```
Dove viene costruito ogni **file** entry, aggiungi:
```python
    "branch_operator_count": None,   # popolato da count_branch_operators.py + classify_coverage_mode.py
    "coverage_mode": None,           # popolato da classify_coverage_mode.py
```
(Inserisci le chiavi nel dict file mantenendo invariati i campi esistenti `path/tier/priority/loc/...`.)

### Step 4 — Verifica che passa
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_plan_batches.py -v`
Output atteso: tutti `passed`.

## Step 5 — Documenta Phase 3 step 3b
In `references/phase-3-sizing.md`, dopo la generazione del batch-plan, aggiungi:

```markdown
### Step 3b — Branch operator scan + coverage mode (JS/TS only)

Dopo `plan_batches.py`, per ogni file target esegui:
    python3 skills/code-coverage/scripts/count_branch_operators.py <file> \
      > .code-coverage/branch-count/<file_safe>.json
Poi classifica la modalità per-file:
    python3 skills/code-coverage/scripts/classify_coverage_mode.py <repo>
Questo popola `branch_operator_count` e `coverage_mode` in batch-plan.json.
File con coverage_mode=branch-priority useranno il template branch-matrix in Phase 5.
```

Nella sezione "Batch Plan File Format", aggiorna l'esempio JSON dei `pending_batches` includendo i nuovi campi `status/assigned_to/completed_by/completed_at` sul batch e `branch_operator_count/coverage_mode` sui file.

### Step 6 — Commit
```
git add skills/code-coverage/scripts/plan_batches.py skills/code-coverage/references/phase-3-sizing.md skills/code-coverage/scripts/tests/test_plan_batches.py
git commit -m "feat(code-coverage): extend batch-plan schema (branch fields + multi-agent status)"
```

## Criteri di accettazione
- [ ] Ogni batch ha `status="pending"`, `assigned_to/completed_by/completed_at=null`.
- [ ] Ogni file ha `branch_operator_count=null` e `coverage_mode=null` di default.
- [ ] `phase-3-sizing.md` documenta lo Step 3b.
- [ ] `test_plan_batches.py` (esistenti + nuovo) tutti verdi.
