# Task 09 — Aggiungere step "side-effect not occurred" ai 4 TC error mutating (ADR-005)

**Goal:** Aggiungere uno step esplicito di **side-effect NOT occurred** ai 4 TC error mutating identificati dallo spec-reviewer iter 2: 3 in `functional_be` (autore_id 404, opera_id 400, body malformato 400) + 1 in `role_based` (viewer DELETE 403). `enumerative_spec` già conforme (no expansion necessaria).

**SP:** 0.5 (Umano) / 0 (Augmented)

**File coinvolti:**
- Modifica: `evals/eval-sets/siae-qa/golden/functional_be/expected_tc_draft.json` (3 TC)
- Modifica: `evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json` (1 TC)

## Step 1 — Identifica i 4 TC target

### functional_be

```bash
python3 -c "
import json
with open('evals/eval-sets/siae-qa/golden/functional_be/expected_tc_draft.json') as f:
    data = json.load(f)
for tc in data['test_cases']:
    title = tc['title']
    n_steps = len(tc.get('steps', []))
    if '[NEG]' in title and n_steps < 3:
        print(f\"TC-{tc['id']}: {title} | {n_steps} steps\")
"
```

**Output atteso:** 3 TC con prefisso `[NEG]` e meno di 3 step (autore_id 404, opera_id 400, body malformato 400).

### role_based

```bash
python3 -c "
import json
with open('evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json') as f:
    data = json.load(f)
for tc in data['test_cases']:
    title = tc['title']
    n_steps = len(tc.get('steps', []))
    if 'viewer' in title.lower() and 'DELETE' in title and n_steps < 3:
        print(f\"TC-{tc['id']}: {title} | {n_steps} steps\")
"
```

**Output atteso:** 1 TC `[ROLE] viewer DELETE 403` con 2 step.

## Step 2 — Aggiungere step di verifica side-effect NOT su functional_be

Per ogni TC NEG di functional_be identificato, aggiungere uno step finale.

Eseguire script:

```bash
cat > /tmp/expand_mutating_neg.py <<'EOF'
import json
import sys

path = sys.argv[1]

# Trigger lessicali derivati empiricamente dai title reali dei TC golden v2.0.0.
# Verifica preliminare (Step 1 di questo task): grep esatti dei title prima di applicare.
# Note esplicite (vincolanti):
# - TC2 (functional_be `[NEG] importo=0`) gia' a 3 step (SELECT COUNT) — NON in trigger list.
# - TC6 (role_based `[ROLE] editor DELETE /opere/{id} -> 403`) e TC7 (`[ROLE] viewer POST /opere -> 403`)
#   sono GIA' a 3 step in golden v2.0.0 (verificato dal plan-review iter 1).
#   NON aggiungere trigger per questi TC — sono compliant.
side_effect_steps_by_title = {
    # functional_be — title reali verificati con grep su expected_tc_draft.json:
    # TC5: "[NEG] POST con autore_id inesistente -> 404"
    "autore_id inesistente": {
        "action": "Verifica che nessun nuovo record sia stato inserito in ripartizioni per il payload tentato",
        "expected_result": "SELECT COUNT(*) FROM ripartizioni WHERE autore_id='UUID-AUTORE-NON-ESISTENTE' restituisce 0; nessun side-effect (404 prima dell'inserimento)"
    },
    # TC7: "[NEG] POST con opera_id mancante -> 400" (missing field, NON wrong format)
    "opera_id mancante": {
        "action": "Verifica che nessun nuovo record sia stato inserito in ripartizioni",
        "expected_result": "SELECT COUNT(*) FROM ripartizioni WHERE created_at > NOW() - INTERVAL '1 second' restituisce 0; validazione 'opera_id is required' respinge il payload pre-inserimento"
    },
    # TC8: "[NEG] POST con body malformato JSON -> 400"
    "body malformato": {
        "action": "Verifica che nessun nuovo record sia stato inserito in ripartizioni",
        "expected_result": "SELECT COUNT(*) FROM ripartizioni WHERE created_at > NOW() - INTERVAL '1 second' restituisce 0; body invalido respinto da parsing JSON pre-controller"
    },
    # role_based — solo TC9 da espandere (TC6/TC7 gia' a 3 step v2.0.0)
    # TC9: "[ROLE] viewer DELETE /opere/{id} -> 403 forbidden"
    "viewer delete": {  # match su lowercased title
        "action": "Verifica che l'opera target non sia stata eliminata (re-query come admin)",
        "expected_result": "GET /opere/{id} come admin restituisce 200 con il record ancora presente; nessuna eliminazione effettuata (403 blocca pre-DELETE)"
    },
}

with open(path) as f:
    data = json.load(f)

expanded = 0
for tc in data["test_cases"]:
    title_lower = tc["title"].lower()
    for trigger, step_template in side_effect_steps_by_title.items():
        if trigger.lower() in title_lower:
            existing = tc.get("steps", [])
            # Check if already has 3+ steps with side-effect verification
            has_side_effect = any(
                "count(*)" in s.get("expected_result", "").lower()
                or "non sia stata eliminata" in s.get("expected_result", "").lower()
                or "ancora presente" in s.get("expected_result", "").lower()
                or "side-effect" in s.get("expected_result", "").lower()
                for s in existing
            )
            if not has_side_effect:
                next_n = len(existing) + 1
                existing.append({
                    "step_number": next_n,
                    "action": step_template["action"],
                    "expected_result": step_template["expected_result"]
                })
                tc["steps"] = existing
                expanded += 1
                print(f"  Expanded TC-{tc['id']}: {tc['title']} → {next_n} steps")
            break

with open(path, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")

print(f"Updated {path}: {expanded} TC expanded with side-effect verification")
EOF

echo "=== functional_be ==="
python3 /tmp/expand_mutating_neg.py evals/eval-sets/siae-qa/golden/functional_be/expected_tc_draft.json

echo "=== role_based ==="
python3 /tmp/expand_mutating_neg.py evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json
```

**Output atteso:**
```
=== functional_be ===
  Expanded TC-X: [NEG] ... autore_id non esistente ... → 3 steps
  Expanded TC-Y: [NEG] ... opera_id formato non valido ... → 3 steps
  Expanded TC-Z: [NEG] ... body malformato ... → 3 steps
Updated ...: 3 TC expanded with side-effect verification

=== role_based ===
  Expanded TC-W: [ROLE] viewer DELETE 403 ... → 3 steps
Updated ...: 1 TC expanded with side-effect verification
```

Se l'output script trova un numero diverso di TC (perché i title non matchano i trigger), aggiornare i trigger nello script per matchare i title reali — verificarli prima con Step 1.

## Step 3 — Verifica counts post-edit

```bash
python3 -c "
import json

for fx, expected_extra in [('functional_be', 3), ('role_based', 1)]:
    path = f'evals/eval-sets/siae-qa/golden/{fx}/expected_tc_draft.json'
    with open(path) as f:
        data = json.load(f)
    tc_with_3plus_neg_role = sum(
        1 for tc in data['test_cases']
        if ('[NEG]' in tc['title'] or '[ROLE]' in tc['title'])
        and any(t in tc['title'].lower() for t in ['autore_id', 'opera_id', 'body malformato', 'viewer delete'])
        and len(tc.get('steps', [])) >= 3
    )
    print(f'{fx}: {tc_with_3plus_neg_role} TC mutating error con >=3 steps (atteso: >={expected_extra})')
"
```

**Output atteso:** count >= expected_extra per ogni fixture.

## Step 4 — Validator re-run sulle 2 fixture aggiornate

```bash
for fx in functional_be role_based; do
  echo "=== $fx ==="
  python3 skills/siae-qa/reference/scripts/validate_outputs.py \
    --m-final evals/eval-sets/siae-qa/golden/$fx/expected_mfinal.json \
    --tc-draft evals/eval-sets/siae-qa/golden/$fx/expected_tc_draft.json \
    --certificate evals/eval-sets/siae-qa/golden/$fx/expected_certificate.json
  echo "Exit code: $?"
done
```

**Output atteso:** 5/5 PASS per entrambe; exit code 0.

## Step 5 — Cleanup + commit

```bash
rm -f /tmp/expand_mutating_neg.py

git add evals/eval-sets/siae-qa/golden/functional_be/expected_tc_draft.json \
        evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json

git commit -m "fix(siae-qa-golden): ADR-005 — 4 TC error mutating con step side-effect-not-occurred

Aggiunge step esplicito di verifica side-effect NOT occurred ai TC error mutating:
- functional_be: 3 TC NEG (autore_id 404, opera_id 400, body malformato 400)
- role_based: 1 TC viewer DELETE 403
- enumerative_spec: gia' conforme (no expansion necessaria)

Ogni TC error mutating ha ora minimo 3 step:
1. Action mutating
2. Verify error response (status + body)
3. Verify side-effect NOT occurred (SELECT COUNT / GET con admin / etc.)

Validator post-edit: 5/5 PASS per le 2 fixture toccate.

Co-Authored-By: SIAE DevForge"
```

## Criteri di Accettazione

- [ ] 3 TC di `functional_be` (autore_id, opera_id, body malformato) hanno `len(steps) >= 3`
- [ ] 1 TC di `role_based` (viewer DELETE) ha `len(steps) >= 3`
- [ ] Validator Step 4 PASS su entrambe le fixture
- [ ] Ogni step aggiunto contiene parole chiave `SELECT COUNT` / `GET ... admin` / `non sia stata eliminata` / `nessun side-effect`
- [ ] Commit conventional commits
