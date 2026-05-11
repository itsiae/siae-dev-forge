# Task 05 — Entity naming gerarchia in XRAY-TEMPLATES.md (ADR-004)

**Goal:** Aggiungere alla sezione "Template M_FINAL (output Phase 1.5)" di `XRAY-TEMPLATES.md` la gerarchia normativa per il campo `entity`: SCREAMING_SNAKE_CASE per tabelle/section name, PascalCase singolare per business entity, eccezioni esplicite.

**SP:** 0.5 (Umano) / 0.5 (Augmented)

**File coinvolti:**
- Modifica: `skills/siae-qa/XRAY-TEMPLATES.md` (sezione "Template M_FINAL")

## Step 1 — Localizza la sezione Template M_FINAL

```bash
grep -n "Template M_FINAL\|## Template" skills/siae-qa/XRAY-TEMPLATES.md
```

**Output atteso:** numero di riga della sezione `## Template M_FINAL (output Phase 1.5)`.

## Step 2 — Read della sezione completa

```bash
sed -n '$(grep -n "Template M_FINAL" skills/siae-qa/XRAY-TEMPLATES.md | head -1 | cut -d: -f1),+30p' skills/siae-qa/XRAY-TEMPLATES.md
```

**Output atteso:** sezione "Template M_FINAL" con schema 6 colonne (matrix_row_id, entity, field, condition, test_type, source_ref).

## Step 3 — Edit: aggiungere sottosezione "Convenzione naming `entity`" alla fine della sezione Template M_FINAL

Inserire **subito prima** della chiusura della sezione "Template M_FINAL" (prima del separatore `---` successivo), il seguente blocco:

```

### Convenzione naming `entity` (ADR-004)

Il campo `entity` segue una gerarchia di scelta deterministica:

1. **Se la spec ha tabelle DB o CSV section name** (es. `GENERAL_DATA`, `TITLES`, `CONTRIBUTORS`, `RIPARTIZIONI_RAW`): usa il nome **as-is** in SCREAMING_SNAKE_CASE. Mantenere il nome originale della spec.

2. **Altrimenti** (REST resource, business entity senza section name): usa il **nome logico singolare in PascalCase**. Esempi validi: `Opera`, `Ripartizione`, `Utente`, `Contratto`.

3. **Mai usare** come `entity`:
   - Nome endpoint: `POST /opere`, `POST_/opere`
   - Nome metodo: `createOpera`, `deleteOpera`
   - Plurale di resource: `opere`, `utenti`, `contratti`
   - Lowercase: `opera`, `ripartizione`

**Eccezioni esplicite (non sono violazioni):**
- `GENERAL_DATA` (CSV section): caso 1, mantenuto in SCREAMING_SNAKE_CASE.
- `EVERGREEN+EXPIRY` (composite field name): non e' un valore di `entity`, e' un valore della colonna `field`. La regola entity non si applica.

**Test sintattico:**

```python
# entity valida:
re.match(r'^[A-Z][A-Z0-9_]*[A-Z0-9]$', entity)  # SCREAMING_SNAKE_CASE
# OPPURE
re.match(r'^[A-Z][a-zA-Z0-9]*$', entity)  # PascalCase

# entity INVALIDA:
entity.startswith(('POST', 'GET', 'PUT', 'DELETE'))  # nome endpoint
entity.endswith(('s', 'i'))  # plurale (heuristic; vedi eccezioni esplicite)
entity == entity.lower()  # tutto lowercase
```
```

## Step 4 — Verifica edit

```bash
grep -c "Convenzione naming\|SCREAMING_SNAKE_CASE\|PascalCase singolare" skills/siae-qa/XRAY-TEMPLATES.md
```

**Output atteso:** ≥ 3.

## Step 5 — Verifica integrita' ToC

Se XRAY-TEMPLATES.md ha una Table of Contents, aggiornarla con la nuova sottosezione:

```bash
grep -n "## Table of Contents\|^- \[" skills/siae-qa/XRAY-TEMPLATES.md | head -15
```

Se la ToC esiste e non include "Convenzione naming entity", aggiungere una entry:
```
- [Convenzione naming entity (ADR-004)](#convenzione-naming-entity-adr-004)
```

## Step 6 — Commit

```bash
git add skills/siae-qa/XRAY-TEMPLATES.md
git commit -m "feat(siae-qa): ADR-004 — entity naming gerarchia in XRAY-TEMPLATES.md

Aggiunge convenzione normativa per il campo entity di M_FINAL:
1. SCREAMING_SNAKE_CASE per tabelle DB / CSV section name (es. GENERAL_DATA)
2. PascalCase singolare per business entity (es. Opera, Ripartizione)
3. Mai usare nome endpoint, metodo, plurale, lowercase

Include test sintattico Python e eccezioni esplicite (GENERAL_DATA, composite field name).

Co-Authored-By: SIAE DevForge"
```

## Criteri di Accettazione

- [ ] `grep -c "Convenzione naming \`entity\`" skills/siae-qa/XRAY-TEMPLATES.md` = 1
- [ ] `grep -c "SCREAMING_SNAKE_CASE" skills/siae-qa/XRAY-TEMPLATES.md` ≥ 2
- [ ] `grep -c "PascalCase singolare" skills/siae-qa/XRAY-TEMPLATES.md` ≥ 1
- [ ] Sezione "Eccezioni esplicite" presente con `GENERAL_DATA` e `EVERGREEN+EXPIRY` esempi
- [ ] Test sintattico Python presente (`re.match`)
- [ ] Commit conventional commits
