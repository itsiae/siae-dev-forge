# Task 18 — batch-plan schema multi-agente + state-schema

**Goal:** Formalizzare nello `state-schema.json` i campi multi-agente del batch-plan (`status/assigned_to/completed_by/completed_at`, già aggiunti in Task 08) e dichiarare i nuovi file di stato `intractable.json` e `agent-N.log`. Prerequisito schema per l'orchestrazione parallela.

**WS:** WS-5 · **Dipendenze:** Task 08 (campi già nel plan_batches output).

## File coinvolti
- Modifica: `skills/code-coverage/lib/state-schema.json`
- Modifica: `skills/code-coverage/scripts/tests/test_plan_batches.py` (validazione schema, opzionale)

## Prerequisito di lettura
Leggi `skills/code-coverage/lib/state-schema.json` per capire il formato (probabile JSON con descrizione dei file di stato in `.code-coverage/`).

## Step 1 — Test fallente
In `skills/code-coverage/scripts/tests/test_plan_batches.py` aggiungi:

```python
import json
from pathlib import Path


def test_state_schema_declares_multiagent_files():
    p = Path(__file__).resolve().parents[2] / "lib" / "state-schema.json"
    text = p.read_text()
    assert "intractable.json" in text
    assert "agent-" in text  # agent-N.log o agent-{id}.log
    # batch-plan deve documentare i campi multi-agente
    assert "assigned_to" in text
    assert "completed_by" in text
```

### Step 2 — Verifica che fallisce
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_plan_batches.py::test_state_schema_declares_multiagent_files -v`
Output atteso: FAILED (stringhe assenti).

### Step 3 — Implementa
In `lib/state-schema.json`, nella descrizione di `batch-plan.json`, aggiungi i campi per ogni batch: `status` (enum `pending|in-progress|agent-timeout|partial|failed|completed`, default `pending`), `assigned_to` (string|null), `completed_by` (string|null), `completed_at` (string ISO|null). Aggiungi due nuove entry di file di stato:

```json
"intractable.json": {
  "description": "File marcati intractable da subagent/Phase 7 (aggregati dal coordinatore). Surfacati in Block 9.",
  "properties": {
    "files": {
      "type": "array",
      "items": {"type": "object", "properties": {
        "path": {"type": "string"},
        "reason": {"type": "string"},
        "suggested_strategy": {"type": "string"}
      }}
    }
  }
},
"agent-N.log": {
  "description": "Log temporaneo per subagent N (0-3): contiene i decisions_log_fragment. Merged in decisions.log dal coordinatore al join, poi rimosso.",
  "type": "string"
}
```
(Adatta alla struttura JSON reale del file — se è uno schema con `properties` top-level per ciascun file, inserisci le due chiavi lì.)

### Step 4 — Verifica che passa
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_plan_batches.py -v`
Output atteso: tutti `passed`.
Run: `python3 -c "import json; json.load(open('skills/code-coverage/lib/state-schema.json')); print('valid JSON')"` → `valid JSON`.

### Step 5 — Commit
```
git add skills/code-coverage/lib/state-schema.json skills/code-coverage/scripts/tests/test_plan_batches.py
git commit -m "feat(code-coverage): declare multi-agent batch fields + intractable.json/agent-N.log in state schema"
```

## Criteri di accettazione
- [ ] `state-schema.json` documenta `status/assigned_to/completed_by/completed_at` per batch.
- [ ] Dichiara `intractable.json` e `agent-N.log`.
- [ ] Resta JSON valido.
