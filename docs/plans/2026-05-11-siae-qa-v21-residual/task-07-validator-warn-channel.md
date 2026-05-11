# Task 07 — Validator WARN channel + check_neg_numeric_has_edge_low (ADR-006)

**Goal:** Estendere `validate_outputs.py` con un livello di severity intermedio `WARN` (oltre `PASS`/`FAIL`), e aggiungere il check `check_neg_numeric_has_edge_low(m_final)` che emette WARN se esiste una row NEG con `condition` numerica strict (`> X` / `< X`) senza una row EDGE corrispondente alla frontiera bassa.

**SP:** 1.5 (Umano) / 0.5 (Augmented)

**File coinvolti:**
- Modifica: `skills/siae-qa/reference/scripts/validate_outputs.py` (funzione `_report` + `main` + nuova `check_neg_numeric_has_edge_low`)

## Step 1 — Read del file validator

```bash
wc -l skills/siae-qa/reference/scripts/validate_outputs.py
sed -n '180,255p' skills/siae-qa/reference/scripts/validate_outputs.py
```

**Output atteso:** funzione `_report(label, errors)` alla riga ~194; `main()` con `argparse`; exit code binario via `sys.exit(main())`.

## Step 2 — Edit `_report`: aggiungere parametro `severity`

Localizza la funzione `_report`:
```python
def _report(label: str, errors: list[str]) -> bool:
    ...
```

Modificare la firma per accettare un parametro opzionale `severity` (default `"FAIL"`):

```python
def _report(label: str, errors: list[str], severity: str = "FAIL") -> bool:
    """Emette il report di un check. Ritorna True se PASS o WARN; False solo se FAIL con errori.

    severity = "FAIL": exit code 1 se ci sono errori; print [FAIL] su stderr.
    severity = "WARN": exit code 0 anche con errori; print [WARN] su stderr.
    """
    import sys
    if not errors:
        print(f"[PASS] {label}")
        return True
    tag = "[WARN]" if severity == "WARN" else "[FAIL]"
    out = sys.stderr if severity == "WARN" else sys.stdout
    for err in errors:
        print(f"{tag} {label}: {err}", file=out)
    return severity == "WARN"
```

## Step 3 — Edit `main()`: tracking warnings vs failures separato

Modificare `main()` per distinguere tra `ok` (failures) e `warned` (warnings):

```python
def main() -> int:
    """Entrypoint: parse args, validate inputs, run cross-checks, return exit code."""
    parser = argparse.ArgumentParser(...)
    args = parser.parse_args()

    ok = True   # diventa False solo su FAIL
    # ... (codice esistente con _report() per gli schemi)

    # NUOVO: check NEG numeric has EDGE low (ADR-006, WARN level)
    if args.m_final and m_final_obj:
        warnings = check_neg_numeric_has_edge_low(m_final_obj)
        # severity="WARN" → exit code resta 0 anche se ci sono warnings
        _report("CHECK: NEG numeric strict has EDGE low (ADR-006)", warnings, severity="WARN")

    return 0 if ok else 1
```

## Step 4 — Implementare `check_neg_numeric_has_edge_low`

Aggiungere PRIMA della funzione `main()` la nuova funzione:

```python
def check_neg_numeric_has_edge_low(m_final: dict) -> list[str]:
    """ADR-006: ogni NEG con condition numerica strict (> X / < X) deve avere
    una row EDGE corrispondente alla frontiera bassa sullo stesso (entity, field).

    Ritorna lista di warnings (vuota se tutto OK).
    """
    import re
    warnings: list[str] = []
    if not m_final or "rows" not in m_final:
        return warnings

    rows = m_final["rows"]
    # Index NEG rows con vincolo strict
    strict_neg_pattern = re.compile(r"[<>]\s*[\-+]?\d+(?:\.\d+)?")
    neg_strict: list[tuple[str, str, str]] = []  # (entity, field, condition)
    for r in rows:
        if r.get("test_type") == "NEG" and strict_neg_pattern.search(r.get("condition", "")):
            neg_strict.append((r["entity"], r["field"], r["condition"]))

    # Index EDGE rows per (entity, field)
    edge_keys = {
        (r["entity"], r["field"])
        for r in rows
        if r.get("test_type") == "EDGE"
    }

    for entity, field, condition in neg_strict:
        if (entity, field) not in edge_keys:
            warnings.append(
                f"NEG strict numerica su {entity}.{field} (condition: {condition}) "
                f"NON ha row EDGE corrispondente alla frontiera bassa. "
                f"Suggerimento ADR-001/002: aggiungere row EDGE type-aware."
            )

    return warnings
```

## Step 5 — Test su input synthetic

Creare un file di test ad-hoc per verificare WARN funziona:

```bash
cat > /tmp/test_mfinal_warn.json <<'EOF'
{
  "story_id": "TEST-001",
  "timestamp": "2026-05-11T10:00:00Z",
  "rows": [
    {
      "matrix_row_id": "A-001",
      "entity": "Test",
      "field": "importo",
      "condition": "importo > 0",
      "test_type": "POS",
      "source_ref": "AC-01"
    },
    {
      "matrix_row_id": "A-002",
      "entity": "Test",
      "field": "importo",
      "condition": "importo <= 0 rifiutato",
      "test_type": "NEG",
      "source_ref": "AC-01"
    }
  ]
}
EOF

python3 skills/siae-qa/reference/scripts/validate_outputs.py --m-final /tmp/test_mfinal_warn.json
echo "Exit code: $?"
```

**Output atteso:**
```
[PASS] M_FINAL (/tmp/test_mfinal_warn.json)
[WARN] CHECK: NEG numeric strict has EDGE low (ADR-006): NEG strict numerica su Test.importo (condition: importo <= 0 rifiutato) NON ha row EDGE corrispondente alla frontiera bassa. Suggerimento ADR-001/002: aggiungere row EDGE type-aware.
Exit code: 0
```

Nota: exit code 0 (perché solo WARN, no FAIL).

## Step 6 — Test idempotenza: input con EDGE già presente non triggera WARN

```bash
cat > /tmp/test_mfinal_ok.json <<'EOF'
{
  "story_id": "TEST-002",
  "timestamp": "2026-05-11T10:00:00Z",
  "rows": [
    {
      "matrix_row_id": "A-001",
      "entity": "Test",
      "field": "importo",
      "condition": "importo > 0 POS",
      "test_type": "POS",
      "source_ref": "AC-01"
    },
    {
      "matrix_row_id": "A-002",
      "entity": "Test",
      "field": "importo",
      "condition": "importo <= 0 rifiutato",
      "test_type": "NEG",
      "source_ref": "AC-01"
    },
    {
      "matrix_row_id": "A-003",
      "entity": "Test",
      "field": "importo",
      "condition": "importo = 0.01 frontiera bassa",
      "test_type": "EDGE",
      "source_ref": "AC-01"
    }
  ]
}
EOF

python3 skills/siae-qa/reference/scripts/validate_outputs.py --m-final /tmp/test_mfinal_ok.json
echo "Exit code: $?"
```

**Output atteso:**
```
[PASS] M_FINAL (/tmp/test_mfinal_ok.json)
Exit code: 0
```

(Nessun WARN: EDGE row presente per `(Test, importo)`.)

## Step 7 — Test sulle 3 golden fixture (non devono regredire)

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

**Output atteso:** 5/5 `[PASS]` per ogni fixture + (eventuali) `[WARN]` per gap noti pre-existing. Exit code = 0 per tutte.

## Step 8 — Commit

```bash
git add skills/siae-qa/reference/scripts/validate_outputs.py
rm -f /tmp/test_mfinal_warn.json /tmp/test_mfinal_ok.json
git commit -m "feat(siae-qa): ADR-006 — validator WARN channel + check_neg_numeric_has_edge_low

Estende validate_outputs.py con livello severity WARN intermedio:
- _report() accetta severity={'FAIL', 'WARN'}; WARN non triggera exit 1
- main() tracking separato ok (FAIL) vs warned (WARN)
- Nuova funzione check_neg_numeric_has_edge_low(m_final): WARN se row NEG strict numerica senza EDGE corrispondente sullo stesso (entity, field)
- [WARN] emesso su stderr; exit code 0 con solo warnings

Compatibilita': chi controlla exit_code != 0 non vede regressione (FAIL invariato).

Co-Authored-By: SIAE DevForge"
```

## Criteri di Accettazione

- [ ] `python3 -c "from skills.siae_qa.reference.scripts.validate_outputs import check_neg_numeric_has_edge_low"` (oppure run del file) non solleva ImportError
- [ ] Test Step 5 produce `[WARN] CHECK: NEG numeric strict has EDGE low` + Exit code = 0
- [ ] Test Step 6 produce solo `[PASS]` + Exit code = 0 (no false-positive)
- [ ] Test Step 7: 3 golden fixture validate con exit code 0 (no regressione)
- [ ] `grep -c "severity.*WARN\|def check_neg_numeric_has_edge_low" skills/siae-qa/reference/scripts/validate_outputs.py` ≥ 2
- [ ] Commit conventional commits
