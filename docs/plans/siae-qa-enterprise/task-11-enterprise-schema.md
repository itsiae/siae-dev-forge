# Task 11 — Schema classificazione 5 campi enterprise [PENDING]

**File:** `skills/siae-qa/XRAY-TEMPLATES.md` + `skills/siae-qa/SKILL.md`
**Sezione:** "Formato Test Case Step-Based" + sezione derivazione automatica
**Cluster:** C — Output enterprise

---

## Obiettivo

Aggiungere 5 campi enterprise opzionali al formato TC (retrocompatibili con il CSV Xray)
con regole di derivazione automatica per ogni campo.

---

## Step 1 — Aggiorna "Formato Test Case Step-Based" in XRAY-TEMPLATES.md

Leggi `skills/siae-qa/XRAY-TEMPLATES.md` sezione "Formato Test Case Step-Based".

**Aggiungi** alla tabella dei campi, dopo la riga `| NRT | ...`:

```markdown
| Test Level | `Unit` / `Integration` / `System` / `E2E` / `Performance` / `Security` — derivato automaticamente (vedi regole) |
| Priority | `P1-Critical` / `P2-High` / `P3-Medium` / `P4-Low` — derivato automaticamente (vedi regole) |
| Classification | `Functional` / `Non-Functional` / `Security` / `Regression` — derivato automaticamente |
| Exec Timing | `Pre-Deploy` / `Post-Deploy-Smoke` / `Sprint` / `Nightly` / `Release` — derivato automaticamente |
| Owner | `QA-Manual` / `QA-Automated` / `Dev-Auto` / `DevOps` — derivato automaticamente |
```

Aggiungi **nota** sotto la tabella:
```markdown
> I 5 campi enterprise sono opzionali e retrocompatibili con l'importatore Xray SIAE.
> Vengono aggiunti in coda al CSV — le colonne sconosciute sono ignorate dall'import standard
> ma preservate nel file per filtering, reporting, e configurazione custom field Xray.
```

---

## Step 2 — Aggiungi sezione "Regole di derivazione automatica 5 campi" in XRAY-TEMPLATES.md

Aggiungi dopo la sezione "Regole granularità step":

```markdown
## Regole di Derivazione Automatica — 5 Campi Enterprise

Questi campi vengono popolati automaticamente dalla skill durante la Fase 4b.
Il developer può modificarli nel riepilogo copertura prima dell'export.

### Test Level

| Condizione | Valore |
|-----------|--------|
| Tipo = FE + scenario positivo o EDGE | `E2E` |
| Tipo = FE + scenario NEG (validazione) | `Integration` |
| Tipo = BE + qualsiasi scenario | `Integration` |
| Tipo = ETL o Batch | `System` |
| Tipo = DB | `Integration` |
| Tipo = Auth + categoria profilazione | `Security` |
| Tipo = Auth + scenario positivo/EDGE | `Integration` |
| Scenario derivato da domanda L4 performance | `Performance` |
| Default (nessuna delle sopra) | `System` |

### Priority

| Condizione | Valore |
|-----------|--------|
| Auth + profilazione + accesso non autorizzato → 403 | `P1-Critical` |
| Auth + dati sensibili + isolamento tenant | `P1-Critical` |
| Scenario positivo + tipo Auth | `P1-Critical` |
| Scenario positivo + tipo BE/FE/Integration | `P2-High` |
| Scenario NEG + dipendenza esterna assente | `P2-High` |
| Scenario EDGE + qualsiasi tipo | `P3-Medium` |
| Scenario NEG + input non valido (validazione form) | `P3-Medium` |
| Scenario positivo + tipo ETL/DB/Batch/Report | `P3-Medium` |
| Scenario profilazione (non Auth) | `P3-Medium` |
| Default | `P3-Medium` |

### Classification

| Condizione | Valore |
|-----------|--------|
| NRT = Y | `Regression` (può coesistere con Functional — usa `Functional,Regression`) |
| Scenario derivato da domanda L4 performance | `Non-Functional` |
| Tipo Auth + scenario profilazione accesso negato | `Security` |
| Qualsiasi altro scenario | `Functional` |

### Exec Timing

| Condizione | Valore |
|-----------|--------|
| DB migration + scenario rollback | `Pre-Deploy` |
| Scenario monitoring/observability (L4) | `Post-Deploy-Smoke` |
| Automazione = Y + Test Level in (Unit, Integration) | `Nightly` |
| NRT = Y + Automazione = N | `Sprint` |
| Auth + profilazione con P1-Critical | `Release` |
| Default | `Sprint` |

### Owner

| Condizione | Valore |
|-----------|--------|
| Automazione = Y + Test Level = Unit | `Dev-Auto` |
| Automazione = Y + Test Level in (Integration, E2E, System) | `QA-Automated` |
| Test Level = Performance | `DevOps` |
| Automazione = N | `QA-Manual` |
| Default | `QA-Manual` |

---

### Header CSV esteso (retrocompatibile)

```
ID;Test Type;Team Competenza;ID JIRA Story;User Story Description;Scenario (descrizione);Step scenario;Action;Expceted Result;Data;Automazione;NRT;Test Level;Priority;Classification;Exec Timing;Owner
```

Le ultime 5 colonne sono opzionali. Per generare CSV solo con i campi legacy (compatibile
con il configuratore Xray esistente senza modifiche), omettile. Per generare il CSV esteso
con tutti i campi enterprise, includile.

La skill chiede al developer durante il riepilogo:
"Vuoi includere i 5 campi enterprise nel CSV (Test Level, Priority, Classification, Timing, Owner)?
Sono retrocompatibili con il tuo importatore Xray."
```

---

## Step 3 — Aggiorna il riepilogo copertura in XRAY-TEMPLATES.md

Sostituisci il blocco "Riepilogo copertura" con la versione estesa:

```markdown
## Riepilogo Copertura

**Riepilogo prima dell'export:** mostra la tabella completa al developer.
Il developer può modificare i valori di `Automazione`, `NRT`, e i 5 campi enterprise prima di procedere.

```
Riepilogo copertura:
  Positivi:      N TC  (P2-High: X | P3-Medium: Y)
  Edge case:     N TC  (P2-High: X | P3-Medium: Y)
  Negativi:      N TC  (P2-High: X | P3-Medium: Y)
  Profilazioni:  N TC  (P1-Critical: X | P3-Medium: Y)
  TOTALE:        N TC

  Test Level:    Unit: X | Integration: Y | System: Z | E2E: W | Performance: V | Security: U
  Automazione:   Y: N | N: M
  NRT:           Y: N | N: M
  Owner:         QA-Manual: X | QA-Automated: Y | Dev-Auto: Z | DevOps: W
```
```

---

## Step 4 — Aggiorna "Checklist di Verifica" in XRAY-TEMPLATES.md

Aggiungi:
```markdown
- [ ] 5 campi enterprise derivati automaticamente per ogni TC (Test Level, Priority, Classification, Exec Timing, Owner)
- [ ] Developer ha confermato o modificato i campi enterprise prima dell'export
- [ ] Header CSV include le 5 colonne enterprise (se developer ha scelto CSV esteso)
```

---

## Step 5 — Aggiorna SKILL.md sezione "Fase 4b"

Nella sezione "Fase 4b — Generazione Test Case", aggiungi dopo le regole di granularità:

```markdown
**Derivazione automatica 5 campi enterprise:**
Per ogni TC generato, calcola automaticamente `Test Level`, `Priority`, `Classification`,
`Exec Timing`, `Owner` usando le regole in `XRAY-TEMPLATES.md` sezione
"Regole di Derivazione Automatica — 5 Campi Enterprise".
Mostra i valori nel riepilogo copertura e permetti al developer di modificarli.
```

---

## Step 6 — Commit

```bash
git add skills/siae-qa/XRAY-TEMPLATES.md skills/siae-qa/SKILL.md
git commit -m "feat(siae-qa): add enterprise TC classification schema (Test Level, Priority, Classification, Timing, Owner)"
```
