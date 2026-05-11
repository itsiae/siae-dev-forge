# Task 03 — Multi-step per azioni mutating in Phase 4b (ADR-005)

**Goal:** Aggiungere in `SKILL.md` Phase 4b una prescrizione esplicita: ogni TC mutating richiede minimo 2 step (read-back/SELECT/audit per 2xx) e minimo 3 step per error 4xx/5xx (side-effect-not-occurred).

**SP:** 1 (Umano) / 0.5 (Augmented)

**File coinvolti:**
- Modifica: `skills/siae-qa/SKILL.md` Phase 4b (sezione ~riga 540-580)

## Step 1 — Localizza la sezione Phase 4b

```bash
grep -n "### Phase 4b\|^#### 4b" skills/siae-qa/SKILL.md
```

**Output atteso:** numero di riga della sezione Phase 4b "Generazione Test Case da M_FINAL".

## Step 2 — Read del blocco Phase 4b

```bash
sed -n '540,575p' skills/siae-qa/SKILL.md
```

**Output atteso:** vincoli di specificità e tracciabilità di Phase 4b.

## Step 3 — Edit: aggiungere sezione "Multi-step per azioni mutating" subito DOPO "Vincolo di specificità (obbligatorio)" e PRIMA di "Tracciabilità obbligatoria"

Cercare nel file il blocco:
```
**Tracciabilita' obbligatoria:** ogni TC deve riportare il `matrix_row_id` corrispondente nel campo `Description` (non nel titolo).
```

Inserire **subito prima** di questo blocco:

```
**Multi-step per azioni mutating (ADR-005, obbligatorio):**

Identifica TC che testano azioni mutating: HTTP `POST`/`PUT`/`PATCH`/`DELETE`, SQL `INSERT`/`UPDATE`/`DELETE`, CSV write su target.

Per TC mutating con status atteso 2xx:
- **Minimo 2 step:** (1) Action mutating con dati concreti; (2) **Side-effect verification** = read-back (`GET /resource/{id}`, `SELECT WHERE id = ...`) OR count (`SELECT COUNT(*) FROM table WHERE ... → incremento atteso`) OR audit log query.
- Response code 2xx **NON e' sufficiente** da solo come step 2, salvo che il body 2xx includa esplicitamente i campi creati (allora step 2 = "assert body fields == expected values").

Per TC mutating con status atteso 4xx/5xx (error mutating):
- **Minimo 3 step:** (1) Action mutating; (2) Verify error response (status code + error message specifico); (3) **Side-effect NOT occurred** = `SELECT COUNT(*) → invariato`, `GET /resource/{id} → 404`, o audit log assente.

Per TC read-only (HTTP `GET`, SQL `SELECT`):
- Minimo 1 step (azione + assertion sullo stesso step).

**Esempi:**

```
[POS] POST /ripartizioni happy path (3 step):
  Step 1: POST /ripartizioni body {importo=100.50, autore_id=UUID} → 201
  Step 2: GET /ripartizioni/{id_returned} → body contiene importo=100.50
  Step 3: SELECT stato FROM ripartizioni WHERE id={id_returned} → "PENDING"

[NEG] POST /ripartizioni importo=0 (3 step):
  Step 1: POST /ripartizioni body {importo=0, autore_id=UUID} → 400 con error.code="IMPORTO_NON_VALIDO"
  Step 2: Verify body contiene error.code="IMPORTO_NON_VALIDO" AND error.message contiene "importo deve essere > 0"
  Step 3: SELECT COUNT(*) FROM ripartizioni WHERE autore_id=UUID → invariato (record NON inserito)
```
```

## Step 4 — Verifica edit

```bash
grep -c "Multi-step per azioni mutating\|Side-effect verification\|Side-effect NOT occurred" skills/siae-qa/SKILL.md
```

**Output atteso:** ≥ 3.

## Step 5 — Verifica posizionamento

```bash
awk '/Vincolo di specificità/,/Tracciabilita.*obbligatoria/' skills/siae-qa/SKILL.md | head -50
```

**Output atteso:** blocco "Multi-step per azioni mutating" presente tra "Vincolo di specificità" e "Tracciabilità obbligatoria".

## Step 6 — Commit

```bash
git add skills/siae-qa/SKILL.md
git commit -m "feat(siae-qa): ADR-005 — Phase 4b prescription multi-step per azioni mutating

Aggiunge in Phase 4b regola obbligatoria:
- TC mutating 2xx: minimo 2 step (action + read-back/SELECT/audit)
- TC mutating 4xx/5xx: minimo 3 step (action + verify error + side-effect NOT occurred)
- TC read-only: 1 step sufficiente
- Response code 2xx NON sufficiente come step 2 (no degradation vs golden)

ADR-005 di docs/plans/2026-05-11-siae-qa-v21-residual-design.md.

Co-Authored-By: SIAE DevForge"
```

## Criteri di Accettazione

- [ ] `grep -c "Multi-step per azioni mutating" skills/siae-qa/SKILL.md` = 1
- [ ] `grep -c "Side-effect verification" skills/siae-qa/SKILL.md` ≥ 1
- [ ] `grep -c "Side-effect NOT occurred" skills/siae-qa/SKILL.md` ≥ 1
- [ ] Esempi di TC con 3 step concreti presenti (verifica `grep "Step 3.*SELECT\|Step 3.*GET"` ≥ 2)
- [ ] Commit conventional commits
