# Task 08 — qa-investigator: enum status v2 + mapping legacy v1→v2

**Stato:** [PENDING]
**Dipende da:** Task 07
**Blocca:** Task 09 (smoke test)

## Goal

Estendere l'output structure di qa-investigator con enum status v2 (5 valori) e mapping legacy v1→v2 esplicito (importato da D2 § 2.3).

## File coinvolti

- `agents/qa-investigator.md` (sezione "## Output — REQUIRED FORMAT" riga ~210)

## Step 1 — TDD test pre-modifica

```bash
grep -c "NOT_FOUND_IN_INDEX\|PROVEN_ABSENT_UNDER_SCOPE" agents/qa-investigator.md
```
Output atteso pre-modifica: 0

```bash
grep -c "scope_completeness" agents/qa-investigator.md
```
Output atteso pre-modifica: 0

## Step 2 — Modifica template output

Trova la sezione esistente (riga ~218):

```markdown
**Confidence**: HIGH | MEDIUM | LOW
**Stato hint utente** (se l'utente ha fornito un'ipotesi): CONFIRMED | PARTIAL | REFUTED
```

Sostituisci con:

```markdown
**Confidence**: HIGH | MEDIUM | LOW (inference_type=<value from envelope D1>)
**Freshness**: observed_at=<ISO8601> · ttl_hint=<seconds> (se KG v2 risponde)
**Stato hint utente** (se l'utente ha fornito un'ipotesi): CONFIRMED | PARTIAL | NOT_FOUND_IN_INDEX | PROVEN_ABSENT_UNDER_SCOPE | REFUTED
**scope_completeness**: full | incomplete | n/d (da envelope se presente)
```

## Step 3 — Aggiungi nuova sotto-sezione "Mapping legacy v1 → v2"

Sotto la sezione "### Vincoli del formato" (riga ~243), aggiungi:

```markdown
### Mapping legacy v1 → v2 (dual-format 60gg)

Per la finestra di deprecation 60gg (28-apr → 27-giu 2026), il MCP può ancora
ritornare valori v1 legacy. Mapping da applicare PRIMA di scrivere il report:

| MCP ritorna v1 | scope_completeness | Agent scrive v2 | Nota |
|---|---|---|---|
| `"NOT_EXISTS"` | qualsiasi | `NOT_FOUND_IN_INDEX` | Mapping D2 § 2.3 |
| `"REFUTED"` | `incomplete` | `NOT_FOUND_IN_INDEX` | Aggiungi nota "legacy v1 mapped" |
| `"REFUTED"` | `full` | `REFUTED` | Match diretto |
| `"REFUTED"` | assente (v1 puro) | `NOT_FOUND_IN_INDEX` | Conservativo: assenza non dimostrata |
| `"CONFIRMED"` | qualsiasi | `CONFIRMED` | Match diretto |
| `"PARTIAL"` | qualsiasi | `PARTIAL` | Match diretto |
| valore sconosciuto | qualsiasi | `PARTIAL` + nota "unknown enum value <X>" | Defensive |

### Semantica enum v2

- **`CONFIRMED`**: 2+ fonti concordi, claim verificato
- **`PARTIAL`**: alcune sotto-affermazioni vere, altre n/d (parzialmente verificato)
- **`NOT_FOUND_IN_INDEX`**: KG/ES non hanno la entity, MA scope ricerca limitato. **≠ assenza**, è "fuori dal nostro scope di ricerca"
- **`PROVEN_ABSENT_UNDER_SCOPE`**: `*_prove_absent` variants hanno confermato assenza nel scope
- **`REFUTED`**: evidenze contrarie all'hint utente (KG ha A, hint diceva B)
```

## Step 4 — Aggiungi vincolo operativo

Nella sezione "## Vincoli operativi" (riga ~302), aggiungi:

```markdown
8. **Hint user "non esiste" → preferire `*_prove_absent` variants**: se l'utente afferma "X non esiste", non basta che il default tool non lo trovi. Usa la variant `*_prove_absent` (es. `who_calls_prove_absent`) per disambiguare assenza dimostrata vs ricerca incompleta. Se la variant non è disponibile, scrivi `NOT_FOUND_IN_INDEX` (non `REFUTED`).
9. **Status enum v2 vs v1 legacy**: leggi sempre `scope_completeness` se presente. Se assente (v1 puro), assumi `incomplete` e mappa `REFUTED` → `NOT_FOUND_IN_INDEX` per essere conservativi.
```

## Step 5 — Aggiorna anti-razionalizzazione

Aggiungi righe (riga ~316):

```markdown
| "PARTIAL e NOT_FOUND_IN_INDEX sono sinonimi" | NO — `PARTIAL` = parzialmente verificato; `NOT_FOUND_IN_INDEX` = fuori dal nostro scope di ricerca. Distinzione critica per design downstream. |
| "REFUTED legacy = REFUTED v2" | NO — leggi `scope_completeness`. Se assente o `incomplete`, mappa a `NOT_FOUND_IN_INDEX` (conservativo). |
| "Posso saltare il mapping legacy" | NO — finestra dual-format 60gg attiva (28-apr → 27-giu). Applica sempre il mapping prima di scrivere il report. |
```

## Step 6 — TDD verify

```bash
grep -c "NOT_FOUND_IN_INDEX\|PROVEN_ABSENT_UNDER_SCOPE" agents/qa-investigator.md
```
Output atteso post-modifica: ≥ 6 (template + mapping table + semantica + anti-razionalizzazione)

```bash
grep -c "scope_completeness" agents/qa-investigator.md
```
Output atteso post-modifica: ≥ 5

```bash
grep -c "legacy v1 mapped\|dual-format" agents/qa-investigator.md
```
Output atteso post-modifica: ≥ 2

## Step 7 — Commit

```bash
git add agents/qa-investigator.md
git commit -m "feat(agents): qa-investigator enum status v2 + mapping legacy v1->v2

Output structure:
- Confidence arricchito con inference_type (envelope D1)
- Freshness (observed_at + ttl_hint) se KG v2 risponde
- Stato hint utente esteso a 5 valori enum v2:
  CONFIRMED, PARTIAL, NOT_FOUND_IN_INDEX, PROVEN_ABSENT_UNDER_SCOPE, REFUTED
- scope_completeness aggiunto

Nuova sotto-sezione Mapping legacy v1 -> v2 (D2 § 2.3):
- Tabella completa 7 casi (NOT_EXISTS, REFUTED + scope, CONFIRMED, PARTIAL, unknown)
- Semantica enum v2 documentata (PARTIAL vs NOT_FOUND_IN_INDEX critico)

Vincoli operativi:
- 'non esiste' -> usa *_prove_absent variants
- v1 puro senza scope_completeness -> conservativo NOT_FOUND_IN_INDEX

Anti-razionalizzazione: 3 nuove righe su distinzioni semantiche v2.

Refs: docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md § 6.2 + ADR-4

Co-Authored-By: SIAE DevForge"
```

## Acceptance check

- [ ] Template output ha 5 valori enum v2 esplicitati
- [ ] Mapping legacy v1→v2 ha tabella completa (7 casi)
- [ ] Semantica enum v2 documentata
- [ ] Vincoli operativi ha 2 righe nuove
- [ ] Anti-razionalizzazione ha 3 righe nuove
- [ ] grep checks passano
- [ ] Commit creato
