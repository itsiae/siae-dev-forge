# Task 08 — Verifica entity naming `Opera` nelle 3 golden role_based (ADR-004 compliance check)

**Goal:** Verificare che le 3 fixture golden `role_based` siano già conformi a ADR-004 (`entity: "Opera"` PascalCase singolare). Le golden sono state aggiornate in una sessione precedente — questo task è un **verification gate**, non un rename. Se la verifica fallisce, il task ridiventa un rename task (vedi sezione Fallback).

**SP:** 0.5 (Umano) / 0 (Augmented) [scalato da 1/0.5 — solo verifica empirica, no edit]

**File coinvolti:**
- Verifica: `evals/eval-sets/siae-qa/golden/role_based/expected_mfinal.json`
- Verifica: `evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json`
- Verifica: `evals/eval-sets/siae-qa/golden/role_based/expected_certificate.json`

## Step 1 — Verifica: 0 occorrenze `"entity": "opere"`

```bash
grep -c '"entity": "opere"' evals/eval-sets/siae-qa/golden/role_based/expected_mfinal.json
grep -c '"entity": "opere"' evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json
```

**Output atteso:** `0` per entrambi i file.

## Step 2 — Verifica: 9 occorrenze `"entity": "Opera"` per ogni file

```bash
grep -c '"entity": "Opera"' evals/eval-sets/siae-qa/golden/role_based/expected_mfinal.json
grep -c '"entity": "Opera"' evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json
```

**Output atteso:** `9` per entrambi i file (9 rows / 9 TC).

## Step 3 — Verifica cascade `entity: Opera` nel field `description` dei TC

```bash
grep -c "entity: Opera" evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json
```

**Output atteso:** ≥ 9 (cascade nel campo description di ogni TC).

## Step 4 — Verifica zero residui lowercase `"opera"` come entity

```bash
grep -c '"entity": "opera"' evals/eval-sets/siae-qa/golden/role_based/expected_mfinal.json
grep -c '"entity": "opera"' evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json
```

**Output atteso:** `0` per entrambi (no occorrenze lowercase residue).

Nota: URL endpoint che contengono `/opere` (es. `POST /opere`, `GET /opere/{id}`) sono **conservati** — sono path HTTP, non entity logiche. Verifica controllo selettivo:

```bash
grep '"/opere' evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json | head -3
```

**Output atteso:** righe contenenti URL path `/opere` o `/opere/{id}` — questi sono validi e non vanno rinominati.

## Step 5 — Validator integrità schema

```bash
python3 skills/siae-qa/reference/scripts/validate_outputs.py \
  --m-final evals/eval-sets/siae-qa/golden/role_based/expected_mfinal.json \
  --tc-draft evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json \
  --certificate evals/eval-sets/siae-qa/golden/role_based/expected_certificate.json
```

**Output atteso:** 5/5 `[PASS]` (schema + bijection + certificate consistency); exit code 0.

## Step 6 — Documenta compliance in audit log

Aggiungi una entry in `audit-reports/siae-qa-v21-simulation-report.md` (o crea il file se non esiste ancora):

```bash
mkdir -p audit-reports
cat >> audit-reports/siae-qa-v21-task08-compliance-check.md <<EOF
# Task 08 — ADR-004 Compliance Check (role_based)

Verificato il $(date -u +"%Y-%m-%dT%H:%M:%SZ"):
- expected_mfinal.json: 9/9 rows con entity="Opera" (PascalCase singolare) ✅
- expected_tc_draft.json: 9/9 TC con entity="Opera" + 9 description cascade ✅
- 0 occorrenze residue di "opere"/"opera" come entity (URL endpoint /opere conservati come path HTTP)
- Validator: 5/5 PASS

ADR-004 chiuso senza edit (golden già conformi da sessione precedente di refactor v2.0.0).
EOF

cat audit-reports/siae-qa-v21-task08-compliance-check.md
```

## Step 7 — Commit (compliance log only, no JSON change)

```bash
git add audit-reports/siae-qa-v21-task08-compliance-check.md
git commit -m "docs(siae-qa): ADR-004 compliance verified — role_based golden già conformi

Task 08 ridotto a verification gate dopo plan-review iter 1:
- Le 3 golden role_based hanno gia' entity='Opera' da sessione precedente
- 0 occorrenze 'opere'/'opera' come entity logica
- URL path /opere conservati (HTTP endpoint, non entity)
- Validator: 5/5 PASS

Closure ADR-004 senza edit JSON. Logged compliance check.

Co-Authored-By: SIAE DevForge"
```

## Fallback (se Step 1/2/3/4 falliscono)

Se uno dei criteri di accettazione fallisce (es. occorrenze residue di `"opere"`), il task ridiventa un **rename task**. Procedere come segue:

```bash
cat > /tmp/rename_entity.py <<'EOF'
import json
import re
import sys

path = sys.argv[1]
with open(path) as f:
    data = json.load(f)

count_entity = 0
count_desc = 0

# M_FINAL format
for row in data.get("rows", []):
    if row.get("entity") in ("opere", "opera"):
        row["entity"] = "Opera"
        count_entity += 1

# TC_DRAFT format
for tc in data.get("test_cases", []):
    if tc.get("entity") in ("opere", "opera"):
        tc["entity"] = "Opera"
        count_entity += 1
    if "description" in tc:
        new_desc = re.sub(r"entity:\s*(opere|opera)\b", "entity: Opera", tc["description"])
        if new_desc != tc["description"]:
            tc["description"] = new_desc
            count_desc += 1

with open(path, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"Updated {path}: {count_entity} entity + {count_desc} description")
EOF

python3 /tmp/rename_entity.py evals/eval-sets/siae-qa/golden/role_based/expected_mfinal.json
python3 /tmp/rename_entity.py evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json
rm /tmp/rename_entity.py

# Poi ri-esegui Step 5 (validator) e ripeti Step 1-4.
```

In caso di fallback, aggiornare SP a `1 / 0.5` e committare come `fix(siae-qa-golden): ADR-004 — entity opere → Opera in role_based fixture`.

## Criteri di Accettazione

- [ ] `grep -c '"entity": "opere"' evals/eval-sets/siae-qa/golden/role_based/expected_*.json` = 0 per ogni file
- [ ] `grep -c '"entity": "Opera"' evals/eval-sets/siae-qa/golden/role_based/expected_mfinal.json` = 9
- [ ] `grep -c '"entity": "Opera"' evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json` = 9
- [ ] `grep -c "entity: Opera" evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json` ≥ 9
- [ ] Validator Step 5 esce con 5/5 PASS + exit 0
- [ ] `audit-reports/siae-qa-v21-task08-compliance-check.md` creato con timestamp UTC
- [ ] Commit conventional commits (docs: compliance log)
- [ ] **Se fallback eseguito:** commit aggiuntivo come `fix(siae-qa-golden)` con conteggi rename documentati
