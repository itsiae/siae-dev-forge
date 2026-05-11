# Task 08 — ADR-004 Compliance Check (role_based)

Verificato il 2026-05-11T08:56:35Z:
- expected_mfinal.json: 9/9 rows con entity="Opera" (PascalCase singolare) OK
- expected_tc_draft.json: 9/9 TC con entity="Opera" + 9 description cascade OK
- 0 occorrenze residue di "opere"/"opera" come entity (URL endpoint /opere conservati come path HTTP)
- Validator: 5/5 PASS

ADR-004 chiuso senza edit (golden gia' conformi da sessione precedente di refactor v2.0.0).

## Comandi di verifica (output reali)

```
$ grep -c '"entity": "opere"' evals/eval-sets/siae-qa/golden/role_based/expected_mfinal.json
0
$ grep -c '"entity": "opere"' evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json
0
$ grep -c '"entity": "Opera"' evals/eval-sets/siae-qa/golden/role_based/expected_mfinal.json
9
$ grep -c '"entity": "Opera"' evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json
9
$ grep -c "entity: Opera" evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json
9
$ grep -c '"entity": "opera"' evals/eval-sets/siae-qa/golden/role_based/expected_mfinal.json
0
$ grep -c '"entity": "opera"' evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json
0

$ python3 skills/siae-qa/reference/scripts/validate_outputs.py \
    --m-final evals/eval-sets/siae-qa/golden/role_based/expected_mfinal.json \
    --tc-draft evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json \
    --certificate evals/eval-sets/siae-qa/golden/role_based/expected_certificate.json
[PASS] M_FINAL (evals/eval-sets/siae-qa/golden/role_based/expected_mfinal.json)
[PASS] TC_DRAFT (evals/eval-sets/siae-qa/golden/role_based/expected_tc_draft.json)
[PASS] CERTIFICATE (evals/eval-sets/siae-qa/golden/role_based/expected_certificate.json)
[PASS] CROSS: M_FINAL<->TC_DRAFT bijection
[PASS] CROSS: certificate consistency
Exit: 0
```
