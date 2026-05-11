# siae-qa Golden Fixtures

Set di reference output validati per la skill `siae-qa`. Ogni directory
rappresenta un cover-case rappresentativo del workflow Phase 0 -> 5.

## Fixture incluse

| Directory             | Cover case                                                         | Story ID  | M_FINAL rows | Test cases |
|-----------------------|---------------------------------------------------------------------|-----------|--------------|------------|
| `enumerative_spec/`   | Migrazione CSV con 10 campi (lookup, mandatory, ISO8601, val fisso) | MIG-101   | 25           | 25         |
| `functional_be/`      | User story BE standard: POST /ripartizioni con 4 AC                 | RIP-205   | 8            | 8          |
| `role_based/`         | Auth con 3 ruoli (admin/editor/viewer) x 3 azioni                   | AUTH-330  | 9            | 9          |

Ogni fixture contiene esattamente 4 file:

- `input.md` -> specifica sorgente fornita al modello (input del workflow).
- `expected_mfinal.json` -> M_FINAL atteso (conforme a `m_final.schema.json`).
- `expected_tc_draft.json` -> TC_DRAFT atteso (conforme a `tc_draft.schema.json`).
- `expected_certificate.json` -> coverage_certificate atteso
  (conforme a `coverage_certificate.schema.json`, sempre `FULL_PASS` per
  le fixture golden).

## Uso: validare una fixture

Lo script `skills/siae-qa/reference/scripts/validate_outputs.py` esegue:
1. validation contro JSON Schema draft 2020-12 (richiede `jsonschema`,
   fallback a check semantici se non installato);
2. cross-check M_FINAL <-> TC_DRAFT (bijection 1:1);
3. cross-check certificate (tc_generated = m_final_rows + tc_added_post_j5;
   FULL_PASS implica gate_1+gate_2 PASS e coverage_score >= 90).

Esempio:

```bash
python3 skills/siae-qa/reference/scripts/validate_outputs.py \
  --m-final    evals/eval-sets/siae-qa/golden/enumerative_spec/expected_mfinal.json \
  --tc-draft   evals/eval-sets/siae-qa/golden/enumerative_spec/expected_tc_draft.json \
  --certificate evals/eval-sets/siae-qa/golden/enumerative_spec/expected_certificate.json
```

Exit code `0` se PASS, `1` se almeno una validazione FAIL.

## Estendere il set

Per aggiungere una nuova fixture:

1. crea `evals/eval-sets/siae-qa/golden/<nome_caso>/`;
2. scrivi `input.md` con la spec sorgente (story ID nel formato `[A-Z]+-[0-9]+`);
3. genera manualmente i 3 file `expected_*.json` rispettando gli schemi;
4. esegui il validator e verifica `[PASS]` su tutte le righe;
5. aggiungi una entry in `evals/eval-sets/siae-qa/functional.json`.

## Riferimenti

- Schemi JSON: `skills/siae-qa/reference/schemas/*.schema.json`
  (M_FINAL, TC_DRAFT, coverage_certificate, xray_id_mapping).
- Validator: `skills/siae-qa/reference/scripts/validate_outputs.py`.
- Workflow di provenienza: `skills/siae-qa/SKILL.md` (Phase 1.5 -> 4d -> 5).
