# Task 06 — Aggiungere domanda strict vs non-strict al question-tree Backend

**Goal:** Aggiungere a `reference/question-trees.md` sezione Backend Microservice (L1 — Flusso principale) una domanda esplicita sul tipo di vincolo numerico (strict `>`/`<` vs non-strict `>=`/`<=`/`BETWEEN`), per disambiguare l'inferenza del tipo da Phase 0c.

**SP:** 0.5 (Umano) / 0 (Augmented)

**File coinvolti:**
- Modifica: `skills/siae-qa/reference/question-trees.md` (sezione Backend Microservice, L1)

## Step 1 — Localizza la sezione Backend Microservice

```bash
grep -n "## Backend Microservice\|## BE\|### L1 — Flusso principale" skills/siae-qa/reference/question-trees.md | head -10
```

**Output atteso:** numero di riga del header `## Backend Microservice (BE)` e della sottosezione `### L1 — Flusso principale` corrispondente.

## Step 2 — Read della sezione BE L1

```bash
sed -n '$(grep -n "## Backend Microservice" skills/siae-qa/reference/question-trees.md | head -1 | cut -d: -f1),+25p' skills/siae-qa/reference/question-trees.md
```

**Output atteso:** sezione BE con bullet di L1 (numerati 1, 2).

## Step 3 — Edit: aggiungere domanda #3 (strict vs non-strict) al BE L1

Cercare nel file il blocco BE L1 esistente:
```
### L1 — Flusso principale
1. "Quali metodi HTTP espone questo endpoint? Quali status code restituisce
   per il caso di successo e per ogni caso di errore previsto?"
2. "Quali campi del payload sono obbligatori?
   Ci sono vincoli di formato o range (es. importo > 0, ISRC pattern)?"
```

Aggiungere come **domanda #3** subito dopo:

```
3. "Per i vincoli numerici di range, sono **strict** (es. `importo > 0`,
   esclusivo) o **non-strict** (es. `quantita >= 0`, inclusivo)?
   E qual e' il **tipo** del campo (decimal/integer/date/timestamp)?
   La risposta determina se Matrix A genera un EDGE auto alla frontiera bassa
   (`0.01` per decimal vs `1` per integer vs data successiva)."
```

## Step 4 — Verifica edit

```bash
grep -c "strict.*non-strict\|EDGE auto alla frontiera" skills/siae-qa/reference/question-trees.md
```

**Output atteso:** ≥ 1.

## Step 5 — Verifica posizione della domanda (robusta vs awk range)

Usare un range awk che si chiude al primo `## ` (header H2) successivo, escludendo BE stesso:

```bash
awk '
  /^## Backend Microservice/ { in_section=1; next }
  /^## / && in_section { in_section=0 }
  in_section { print }
' skills/siae-qa/reference/question-trees.md | grep -c "^[0-9]\."
```

**Output atteso:** ≥ 3 (almeno 3 domande nella sezione BE totale, incluse L1+L2+L3; il count specifico per L1 ora include la nuova domanda #3).

Verifica targeted L1 only:

```bash
awk '
  /^## Backend Microservice/ { in_be=1; next }
  /^## / && in_be { in_be=0 }
  /^### L[2-3] —/ && in_be { in_l1=0 }
  /^### L1 — Flusso principale/ && in_be { in_l1=1; next }
  in_be && in_l1 && /^[0-9]\./ { print }
' skills/siae-qa/reference/question-trees.md | wc -l
```

**Output atteso:** `3` (3 domande in L1 della sezione BE post-edit).

## Step 6 — Commit

```bash
git add skills/siae-qa/reference/question-trees.md
git commit -m "feat(siae-qa): aggiungi domanda strict vs non-strict al question-tree Backend (ADR-002)

Phase 0c question tree BE estesa con domanda #3 (L1):
- Vincoli numerici: strict (>, <) vs non-strict (>=, <=, BETWEEN)
- Tipo del campo (decimal/integer/date/timestamp)
- Determina type-aware frontiera bassa per Matrix A (ADR-001 + ADR-002)

Co-Authored-By: SIAE DevForge"
```

## Criteri di Accettazione

- [ ] `grep -c "strict.*non-strict" skills/siae-qa/reference/question-trees.md` ≥ 1
- [ ] `grep -c "decimal/integer/date" skills/siae-qa/reference/question-trees.md` ≥ 1
- [ ] La domanda e' posizionata in L1 della sezione BE (verificare con `awk` Step 5)
- [ ] Commit conventional commits
