# Task 11 — BUG FIX G-DB-5: regex `matrix_row_id` schema troppo restrittiva

**Goal:** Estendere la regex del campo `matrix_row_id` in `m_final.schema.json` per supportare prefissi di entità oltre `[ABC]` (necessario per spec con 4+ entità logiche, scoperto dalla simulazione `database_migration` DB-678).

**SP:** 0.5 (Umano) / 0.5 (Augmented)

**File coinvolti:**
- Modifica: `skills/siae-qa/reference/schemas/m_final.schema.json` (pattern matrix_row_id)
- Modifica: `skills/siae-qa/reference/scripts/validate_outputs.py` (eventuali check pattern interni)

## Background

La simulazione di siae-qa v2.0.0 su `database_migration` (Story DB-678) ha generato 8 entità logiche (MigrationScript, AutoriTable, IndexCreation, RollbackScript, FlywayHistory, LockImpact, Timing, FKIntegrity) → l'agent ha dovuto rimappare manualmente `D-NNN → C-NNN` ed `E-NNN → B-NNN` perché lo schema regex `^[ABC]-[0-9]{3}$|^J5-gap-G[0-9]{2}$|^developer-[0-9]{3}$` rigetta `[DEFGHIJ]-NNN`. Il rimapping perde la semantica entity-namespace.

## Step 1 — Verifica regex attuale

```bash
grep -A 2 '"matrix_row_id"' skills/siae-qa/reference/schemas/m_final.schema.json | head -5
```

**Output atteso:** linea contenente `"pattern": "^[ABC]-[0-9]{3}$|^J5-gap-G[0-9]{2}$|^developer-[0-9]{3}$"` o equivalente.

## Step 2 — Edit: estendi regex a `[A-Z]-\d{3}`

Sostituire il pattern attuale con il pattern esteso:

```python
import json, sys

path = "skills/siae-qa/reference/schemas/m_final.schema.json"
with open(path) as f:
    schema = json.load(f)

# Naviga al pattern di matrix_row_id (può essere in $defs o inline)
def patch_pattern(obj):
    if isinstance(obj, dict):
        if "pattern" in obj and "ABC" in obj.get("pattern", ""):
            obj["pattern"] = r"^[A-Z]-\d{3}$|^J5-gap-G\d{2}$|^developer-\d{3}$"
            return True
        for v in obj.values():
            if patch_pattern(v):
                return True
    elif isinstance(obj, list):
        for v in obj:
            if patch_pattern(v):
                return True
    return False

patched = patch_pattern(schema)
if patched:
    with open(path, "w") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Patched {path}: regex extended to [A-Z]-\\d{{3}}")
else:
    print(f"WARNING: pattern non trovato — verifica manuale richiesta")
    sys.exit(1)
```

Salvare come `/tmp/patch_schema.py` ed eseguire:

```bash
cat > /tmp/patch_schema.py <<'EOF'
import json, sys
path = "skills/siae-qa/reference/schemas/m_final.schema.json"
with open(path) as f:
    schema = json.load(f)
def patch_pattern(obj):
    if isinstance(obj, dict):
        if "pattern" in obj and "ABC" in obj.get("pattern", ""):
            obj["pattern"] = r"^[A-Z]-\d{3}$|^J5-gap-G\d{2}$|^developer-\d{3}$"
            return True
        for v in obj.values():
            if patch_pattern(v): return True
    elif isinstance(obj, list):
        for v in obj:
            if patch_pattern(v): return True
    return False
patched = patch_pattern(schema)
if patched:
    with open(path, "w") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("Patched: regex extended to [A-Z]-d{3}")
else:
    print("WARNING: pattern not found")
    sys.exit(1)
EOF
python3 /tmp/patch_schema.py
```

## Step 3 — Verifica regex post-edit

```bash
grep '"pattern"' skills/siae-qa/reference/schemas/m_final.schema.json | head -3
```

**Output atteso:** pattern contiene `[A-Z]-\\d{3}` (escaped JSON form).

## Step 4 — Update validator fallback (se ha logica regex hardcoded)

```bash
grep -n "ABC\|\\[A-C\\]\\|\\[A-Z\\]" skills/siae-qa/reference/scripts/validate_outputs.py
```

Se trovi pattern hardcoded `[ABC]` nel codice Python (fallback semantici quando `jsonschema` non disponibile), aggiornali a `[A-Z]`.

Se nessuno match → validator usa solo lo schema JSON, già aggiornato in Step 2. Nessuna modifica Python richiesta.

## Step 5 — Unit test: spec con 8 entità (workaround DB-678)

Crea file di test temporaneo:

```bash
cat > /tmp/test_8_entities.json <<'EOF'
{
  "story_id": "DB-678",
  "timestamp": "2026-05-11T10:00:00Z",
  "rows": [
    {"matrix_row_id": "A-001", "entity": "MigrationScript", "field": "version", "condition": "V20260511 valido", "test_type": "POS", "source_ref": "AC1"},
    {"matrix_row_id": "B-001", "entity": "AutoriTable", "field": "email_secondaria", "condition": "nullable ADD COLUMN", "test_type": "POS", "source_ref": "AC2"},
    {"matrix_row_id": "C-001", "entity": "IndexCreation", "field": "CONCURRENTLY", "condition": "no AccessExclusiveLock", "test_type": "POS", "source_ref": "AC3"},
    {"matrix_row_id": "D-001", "entity": "RollbackScript", "field": "DROP COLUMN", "condition": "post-write 1000 rows", "test_type": "NEG", "source_ref": "AC7"},
    {"matrix_row_id": "E-001", "entity": "FlywayHistory", "field": "audit_log", "condition": "entry success=true", "test_type": "POS", "source_ref": "AC9"},
    {"matrix_row_id": "F-001", "entity": "LockImpact", "field": "duration", "condition": "< 1s", "test_type": "EDGE", "source_ref": "AC5"},
    {"matrix_row_id": "G-001", "entity": "Timing", "field": "create_index_duration", "condition": "< 30 min", "test_type": "EDGE", "source_ref": "AC8"},
    {"matrix_row_id": "H-001", "entity": "FKIntegrity", "field": "opere.codice_autore", "condition": "COUNT = 0 orphan", "test_type": "POS", "source_ref": "AC4"}
  ]
}
EOF

python3 skills/siae-qa/reference/scripts/validate_outputs.py --m-final /tmp/test_8_entities.json
echo "Exit code: $?"
```

**Output atteso:**
```
[PASS] M_FINAL (/tmp/test_8_entities.json)
Exit code: 0
```

Pre-fix: questo input avrebbe prodotto `[FAIL] M_FINAL: matrix_row_id 'D-001' does not match pattern ...`. Post-fix: PASS.

## Step 6 — Regression: 3 golden originali non devono regredire

```bash
for fx in enumerative_spec functional_be role_based; do
  echo "=== $fx ==="
  python3 skills/siae-qa/reference/scripts/validate_outputs.py \
    --m-final evals/eval-sets/siae-qa/golden/$fx/expected_mfinal.json \
    --tc-draft evals/eval-sets/siae-qa/golden/$fx/expected_tc_draft.json \
    --certificate evals/eval-sets/siae-qa/golden/$fx/expected_certificate.json
  echo "Exit code: $?"
done
```

**Output atteso:** 5/5 PASS per ogni fixture (golden usano A/B/C prefissi, sono comunque compatibili con `[A-Z]`).

## Step 7 — Cleanup + commit

```bash
rm -f /tmp/patch_schema.py /tmp/test_8_entities.json

git add skills/siae-qa/reference/schemas/m_final.schema.json
git commit -m "fix(siae-qa-schemas): G-DB-5 estendi regex matrix_row_id a [A-Z]-d{3}

La regex precedente accettava solo prefissi [ABC]-NNN, costringendo a workaround
manuale per spec con >3 entita' logiche (es. database_migration DB-678 ha 8
entita': MigrationScript/AutoriTable/IndexCreation/RollbackScript/FlywayHistory/
LockImpact/Timing/FKIntegrity).

Estensione retrocompatibile: i golden esistenti (A/B/C-NNN) restano validi.
Nuovo supporto: D-NNN, E-NNN, ..., Z-NNN per namespacing per entita'.

Regression test: 5/5 PASS su 3 golden fixture.

Bug scoperto dalla 5-case simulation (database_migration agent rilevato workaround).

Co-Authored-By: SIAE DevForge"
```

## Criteri di Accettazione

- [ ] `grep -c '\[A-Z\]' skills/siae-qa/reference/schemas/m_final.schema.json` ≥ 1
- [ ] `grep -c '\[ABC\]' skills/siae-qa/reference/schemas/m_final.schema.json` = 0 (pattern vecchio rimosso)
- [ ] Step 5 test 8-entità PASS + exit 0
- [ ] Step 6 regression 3 golden tutti PASS
- [ ] Commit conventional commits
