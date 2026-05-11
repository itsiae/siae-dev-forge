# Task 02 — Aggiornare prompt Matrix A/B con POS unification + NEG collapse + B-rows conditional (ADR-007)

**Goal:** Modificare i prompt di `Matrix Agent A` (header attualmente alla riga 355) e `Matrix Agent B` (header attualmente alla riga 368) in `SKILL.md` per applicare le 3 regole di ADR-007: POS lookup unification, NEG per-field collapse, composite suppression condizionale.

**SP:** 2 (Umano) / 1 (Augmented)

**File coinvolti:**
- Modifica: `skills/siae-qa/SKILL.md` (sezione Matrix Agent A/B prompts, righe 355-396 in v2.0.0 — verificate empiricamente in Step 0)

## Step 0 — PRECONDIZIONE: verifica empirica posizione prompts

I numeri di riga sono indicativi (lo SKILL.md può essere variato da edit di task precedenti). PRIMA di applicare gli edit, identifica le righe reali:

```bash
grep -n "Matrix Agent A\|Matrix Agent B\|Matrix Agent C" skills/siae-qa/SKILL.md
```

**Output atteso (baseline v2.0.0):**
```
355:**Matrix Agent A — Field/Value Decomposer:**
368:**Matrix Agent B — Rule Composer:**
382:**Matrix Agent C — Role/Permission Mapper:**
```

Se i numeri di riga differiscono da quelli sopra (perché edit di task precedenti hanno spostato le sezioni), **usare i numeri reali** ritornati da grep. Non procedere con sed hardcoded `352,375` — usa sempre `grep -n` per posizionamento robusto.

Verifica anche la presenza della bullet `Lookup enumerato →` letteralmente nel prompt:

```bash
grep -n "Lookup enumerato → 1 riga POS" skills/siae-qa/SKILL.md
```

**Output atteso:** 1 occorrenza nella sezione del prompt Matrix Agent A (riga 360 in v2.0.0 baseline). Se grep non trova nulla, **fermare il task** e ri-leggere il prompt Matrix A integralmente:

```bash
MATRIX_A_LINE=$(grep -n "Matrix Agent A — Field/Value Decomposer" skills/siae-qa/SKILL.md | cut -d: -f1)
sed -n "${MATRIX_A_LINE},+15p" skills/siae-qa/SKILL.md
```

E aggiornare l'edit Step 3 di conseguenza (sostituendo la bullet effettivamente presente).

## Step 1 — Localizza i prompt Matrix A/B/C (già fatto in Step 0)

(Skip — output verificato in Step 0.)

## Step 2 — Read del blocco Matrix A (dinamico)

```bash
MATRIX_A_LINE=$(grep -n "Matrix Agent A — Field/Value Decomposer" skills/siae-qa/SKILL.md | cut -d: -f1)
sed -n "${MATRIX_A_LINE},+25p" skills/siae-qa/SKILL.md
```

**Output atteso:** prompt Matrix Agent A che inizia con `**Matrix Agent A — Field/Value Decomposer:**` seguito da `Sei un QA Matrix Agent specializzato in decomposizione campo-valore.` e contiene la bullet `- Lookup enumerato → 1 riga POS per ogni valore + 1 riga NEG "fuori lookup"`.

## Step 3 — Edit Matrix A: aggiungere regola POS lookup unification

Nel prompt Matrix Agent A, **dopo** la bullet `- Lookup enumerato → 1 riga POS per ogni valore + 1 riga NEG "fuori lookup"`, sostituire con:

```
  - Lookup enumerato (test sintattico per esplosione completa):
    * SE la spec contiene mapping esplicito campo→valore→esito (tabella con header `| Campo | Lookup | Mapping |` o sezione "Mapping CSV → Target"):
      → 1 POS per ogni valore + 1 NEG "fuori lookup" (esplosione completa, default migration)
    * ALTRIMENTI (lookup senza esiti distinti documentati):
      → 1 POS rappresentativa (primo valore in ordine sintattico) `source_ref="lookup_repr"` + 1 POS per ogni valore con comportamento downstream distinto documentato + 1 NEG "fuori lookup"
  - Mandatory non-numerico → POS(valido) + NEG(assente/null)
    * NEG per-field collapse: se piu' campi mandatory dello stesso entity hanno errore simmetrico (stesso status_code + stesso pattern errore lessicale modulo nome campo), genera 1 NEG rappresentativa `source_ref="mandatory_collapsed"` con `condition="<primo campo mandatory>=null"`. Se errori asimmetrici (es. `autore_id → 404`, `opera_id → 400`), 1 NEG per classe-errore distinta.
```

## Step 4 — Edit Matrix B: B-001/B-002 conditional

Nel prompt Matrix Agent B (composite), **sostituire** la bullet:
```
  - Aggiungi 1 happy path (tutti i campi nominali validi)
  - Aggiungi 1 worst case (tutti i campi edge contemporaneamente)
```

Con:
```
  - B-001 (composite_happy) e B-002 (composite_worst) SOLO se la spec contiene almeno 1 regola composita cross-field (vincolo che lega 2+ campi con AND/OR di condizioni interdipendenti).
    * SE spec ha composite rules → genera B-001 (POS, tutti campi nominali validi) + B-002 (EDGE, tutti campi edge contemporaneamente). `source_ref="composite_happy"` o `"composite_worst"`.
    * SE spec NO composite rules → NON generare B-001/B-002 (M_B può essere vuoto).
```

## Step 5 — Edit Matrix A: type-aware frontiera bassa per strict-bound

Nel prompt Matrix Agent A, aggiungere **subito dopo** la sezione strict-bound (introdotta in Task 01 nella tabella):

```
  - Strict-bound numerico (`>`, `<`) — EDGE type-aware:
    * Inferire tipo dalla serializzazione Phase 1.5 (`ENTITA E CAMPI ... dominio: decimal/integer/date`)
    * `> 0` decimal → EDGE `0.01`; `> 0` integer → EDGE `1`; `> '2020-01-01'` date → EDGE `2020-01-02`
    * Se tipo non specificato in spec: default `integer`, segnala WARNING `source_ref="type_inferred_default_integer"`
```

## Step 6 — Verifica edit con grep

```bash
grep -c "lookup_repr\|mandatory_collapsed\|composite_happy\|composite_worst\|type_inferred_default_integer" skills/siae-qa/SKILL.md
```

**Output atteso:** `5` (almeno 1 per ogni source_ref token introdotto).

## Step 7 — Verifica integrità prompt

```bash
sed -n '350,400p' skills/siae-qa/SKILL.md
```

**Output atteso:** prompt Matrix A e B coerenti, code-fence chiusi (`` ``` ``), no testo orfano.

## Step 8 — Commit

```bash
git add skills/siae-qa/SKILL.md
git commit -m "feat(siae-qa): ADR-007 — Matrix A/B prompts con POS unification + NEG collapse + B-rows condizionale

Aggiorna i prompt dei 3 agent Matrix di Phase 1.5:
- Matrix A: POS lookup unification con test sintattico per esplosione completa
- Matrix A: NEG per-field collapse per errori simmetrici
- Matrix A: type-aware frontiera bassa (decimal/integer/date)
- Matrix B: B-001/B-002 composite generati SOLO se spec ha regole cross-field

ADR-007 + ADR-001 di docs/plans/2026-05-11-siae-qa-v21-residual-design.md.

Co-Authored-By: SIAE DevForge"
```

## Criteri di Accettazione

- [ ] `grep -c "lookup_repr" skills/siae-qa/SKILL.md` ≥ 1
- [ ] `grep -c "mandatory_collapsed" skills/siae-qa/SKILL.md` ≥ 1
- [ ] `grep -c "composite_happy\|composite_worst" skills/siae-qa/SKILL.md` ≥ 2
- [ ] `grep -c "type_inferred_default_integer" skills/siae-qa/SKILL.md` ≥ 1
- [ ] Code-fence dei prompt Matrix A/B chiusi (`` ``` `` count pari nelle righe del prompt)
- [ ] Commit creato con messaggio conforme
