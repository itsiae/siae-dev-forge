# Accumulated Learnings + Split Plans — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Aggiungere accumulated learnings tra subagent e split plans in directory per ridurre token waste
**Architettura:** Modifiche a 4 file Markdown (skill) — nessun codice runtime, solo prompt engineering
**Stack:** Markdown
**SP:** 3 SP-Umano / 1 SP-Augmented
**Design doc:** `docs/plans/2026-03-18-accumulated-learnings-split-plans-design.md`

---

## Task 1: Aggiungere Project Discoveries al report implementer [DONE]

**File coinvolti:**
- Modifica: `skills/siae-subagent-development/implementer-prompt.md` (righe 186-200, report di completamento)

**Step 1: Aggiungere sezione Project Discoveries al Report di Completamento**

Dopo la riga `Note:` (riga ~199) nel blocco `IMPLEMENTER REPORT`, aggiungere:

```markdown
  Project Discoveries:
    - [quirk/gotcha 1 scoperto durante l'implementazione]
    - [quirk/gotcha 2 ...]
    - [nessuna: se non hai scoperto nulla di rilevante]
```

**Step 2: Aggiungere guida su cosa riportare come discovery**

Prima del blocco "Report di Completamento" (dopo la sezione Self-Review Checklist, riga ~180), aggiungere una sezione guida:

```markdown
## Project Discoveries — Cosa Riportare

Dopo ogni task, riporta le scoperte utili per i task successivi.

**Riporta:**
- Quirk del codebase (es. "L'ORM wrappa errori DB in tipo custom XyzException")
- Pattern non documentati che hai scoperto implementando
- Gotcha di configurazione o dipendenze inattese
- Workaround necessari non previsti dal piano

**NON riportare:**
- Cose ovvie dal piano o dalla documentazione
- Best practice generiche (es. "usare try-catch")
- Dettagli specifici del tuo task che non impattano gli altri
```

**Step 3: Verifica**

```bash
grep -n "Project Discoveries" skills/siae-subagent-development/implementer-prompt.md
```
Output atteso: 2+ match (sezione guida + report template)

**Step 4: Commit**

```bash
git add skills/siae-subagent-development/implementer-prompt.md
git commit -m "feat(subagent): add Project Discoveries section to implementer report"
```

---

## Task 2: Aggiungere accumulo discoveries nell'orchestratore [DONE]

**Dipende da:** Task 1

**File coinvolti:**
- Modifica: `skills/siae-subagent-development/SKILL.md` (Step 1, Step 2, Step 5)

**Step 1: Aggiungere inizializzazione discoveries in Step 1 (Carica il Piano)**

Dopo il blocco `Output:` dello Step 1 (riga ~86), aggiungere:

```markdown
**Inizializza Accumulated Discoveries:**

Crea un blocco vuoto che verra' popolato durante l'esecuzione:

```
ACCUMULATED DISCOVERIES:
(nessuna — primo task)
```

Questo blocco si azzera ogni volta che viene caricato un nuovo piano.
Non persiste tra sessioni o tra piani diversi.
```

**Step 2: Aggiungere iniezione discoveries in Step 2 (Dispatch Implementer)**

Nel testo di Step 2 (riga ~100-108), dopo la descrizione del subagent implementer, aggiungere:

```markdown
**Contesto arricchito:** oltre al task description e al contesto progetto,
inietta nel prompt del subagent il blocco accumulated discoveries:

```
**Discoveries dai task precedenti (usale, non riscoprirle):**

{accumulated_discoveries}
```

Per il primo task il blocco e' vuoto. Per i task successivi contiene
le scoperte accumulate dai task precedenti.
```

**Step 3: Aggiungere estrazione discoveries in Step 5 (Mark Task Complete)**

In Step 5 (riga ~155-166), dopo l'aggiornamento del marker `[PENDING]` → `[DONE]`, aggiungere:

```markdown
**Aggiorna Accumulated Discoveries:**

Dopo che l'implementer produce il report, estrai la sezione `Project Discoveries`.
Se contiene discoveries (non solo "nessuna"), aggiungile al blocco accumulato:

```
ACCUMULATED DISCOVERIES:
- [Task 1] Drizzle ORM wrappa PostgresError dentro DrizzleQueryError
- [Task 2] Il config loader ignora .env.local in test environment
- [Task 3] (nessuna nuova discovery)
```

Ogni discovery e' prefissata con `[Task N]` per tracciabilita'.
```

**Step 4: Verifica**

```bash
grep -n "ACCUMULATED DISCOVERIES" skills/siae-subagent-development/SKILL.md
```
Output atteso: 3+ match (init in Step 1, inject in Step 2, update in Step 5)

**Step 5: Commit**

```bash
git add skills/siae-subagent-development/SKILL.md
git commit -m "feat(subagent): accumulate and inject project discoveries across tasks"
```

---

## Task 3: Convertire siae-writing-plans a formato directory [DONE]

**File coinvolti:**
- Modifica: `skills/siae-writing-plans/SKILL.md` (Step 3, Step 4)

**Step 1: Aggiornare Step 3 (Scrivi il Piano Bite-Sized) con formato directory**

Sostituire il template monolitico in Step 3 (riga ~100-183) con il nuovo formato directory.

L'header obbligatorio diventa il contenuto di `overview.md`:

````markdown
**Il piano viene scritto come directory:**

```
docs/plans/<topic>/
  overview.md          # header + indice task con stato
  task-01-<nome>.md    # task completo
  task-02-<nome>.md
  ...
  task-NN-<nome>.md
```

**`overview.md` — template:**

```markdown
# [Nome Feature] — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** [Una frase]
**Architettura:** [2-3 frasi]
**Stack:** [Tecnologie]
**SP:** [Stima]
**Design doc:** [path al design doc]

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | [Nome task 1] | `task-01-<nome>.md` | [PENDING] |
| 2 | [Nome task 2] | `task-02-<nome>.md` | [PENDING] |
| N | [Nome task N] | `task-NN-<nome>.md` | [PENDING] |

## Dipendenze

- Task 2 dipende da Task 1
- Task 3-4 sono indipendenti
```

**Ogni `task-NN-<nome>.md`** contiene il task completo con il template
TDD esistente (file coinvolti, step 1-5, codice, comandi, output atteso).
````

**Step 2: Aggiornare Step 4 (Salva il Piano) con commit directory**

Sostituire il comando commit (riga ~204-207) con:

```markdown
```bash
git add docs/plans/<topic>/
git commit -m "docs(plans): aggiungi piano implementativo per [feature]"
```
```

**Step 3: Aggiungere sezione retrocompatibilita'**

Dopo Step 4, aggiungere:

```markdown
### Retrocompatibilita'

I piani esistenti in formato file unico (`docs/plans/*-plan.md`) restano validi.
Le skill di esecuzione (`siae-subagent-development`, `siae-executing-plans`)
detectano automaticamente il formato:

- **Directory** (`docs/plans/<topic>/overview.md` esiste) → formato split
- **File** (`docs/plans/*-plan.md`) → formato legacy monolitico

Nessun piano esistente richiede migrazione.
```

**Step 4: Verifica**

```bash
grep -n "overview.md" skills/siae-writing-plans/SKILL.md
```
Output atteso: 3+ match (struttura directory, template, retrocompatibilita')

**Step 5: Commit**

```bash
git add skills/siae-writing-plans/SKILL.md
git commit -m "feat(writing-plans): output split directory format with overview + task files"
```

---

## Task 4: Aggiornare orchestratori per detect formato split [DONE]

**Dipende da:** Task 3

**File coinvolti:**
- Modifica: `skills/siae-subagent-development/SKILL.md` (Step 1, Step 2)
- Modifica: `skills/siae-executing-plans/SKILL.md` (Step 1, Step 2, Step 3)

**Step 1: Aggiornare Step 1 di siae-subagent-development (Carica il Piano)**

In Step 1 (riga ~71-86), dopo "Identifica il design doc", aggiungere logica di detect:

```markdown
**Detect formato piano:**

1. Cerca directory in `docs/plans/` che contiene `overview.md`
   → se trovata: formato split. Leggi `overview.md` per lista task.
2. Se non trovata: cerca file `*-plan.md` in `docs/plans/`
   → formato legacy monolitico. Procedi come prima.

```
# Formato split
Piano:    docs/plans/<topic>/overview.md
Task:     docs/plans/<topic>/task-01-*.md ... task-NN-*.md

# Formato legacy
Piano:    docs/plans/<topic>-plan.md (file unico)
```
```

**Step 2: Aggiornare Step 2 di siae-subagent-development (Dispatch Implementer)**

In Step 2 (riga ~88-108), specificare cosa passa al subagent nel formato split:

```markdown
**Contesto per il subagent (formato split):**

Il subagent riceve SOLO:
- `overview.md` — per contesto generale (goal, architettura, stack)
- `task-NN-<nome>.md` — il task specifico da implementare
- Accumulated discoveries (se presenti)

NON passare gli altri file task. Il subagent non ha bisogno di leggere task
che non gli competono → risparmio token significativo.

**Contesto per il subagent (formato legacy):**

Estrai dal file monolitico la sezione del task corrente e passala al subagent
insieme all'header del piano.
```

**Step 3: Aggiornare Step 1 di siae-executing-plans (Carica e Rivedi il Piano)**

In Step 1 (riga ~91-106), aggiungere la stessa logica di detect:

```markdown
**Detect formato piano:**

1. Cerca directory in `docs/plans/` che contiene `overview.md`
   → formato split. Leggi `overview.md` per lista task e stato.
2. Se non trovata: cerca file `*-plan.md` in `docs/plans/`
   → formato legacy monolitico.

**Annuncia:**
```
PIANO CARICATO: docs/plans/<topic>/overview.md (formato split)
Task totali: N
Primo batch: Task 1-3
Domande/problemi: [nessuno | lista]
```
```

**Step 4: Aggiornare Step 2 di siae-executing-plans (Esegui Batch)**

In Step 2 (riga ~108-133), specificare che nel formato split si legge solo il task file:

```markdown
**Formato split:** per ogni task nel batch, leggi solo
`docs/plans/<topic>/task-NN-<nome>.md`. Non rileggere overview o altri task.

**Formato legacy:** estrai la sezione task dal file monolitico.
```

**Step 5: Aggiornare Step 3 di siae-executing-plans (Report Post-Batch)**

In Step 3, specificare dove aggiornare lo stato:

```markdown
**Aggiornamento stato (formato split):**
Aggiorna la colonna `Stato` nella tabella indice di `overview.md`:
`[PENDING]` → `[DONE]` o `[BLOCKED]`

**Aggiornamento stato (formato legacy):**
Aggiorna il marker nel file monolitico come prima.
```

**Step 6: Verifica**

```bash
grep -n "formato split\|formato legacy\|overview.md" skills/siae-subagent-development/SKILL.md skills/siae-executing-plans/SKILL.md
```
Output atteso: match multipli in entrambi i file

**Step 7: Commit**

```bash
git add skills/siae-subagent-development/SKILL.md skills/siae-executing-plans/SKILL.md
git commit -m "feat(orchestrators): detect split/legacy plan format, read only relevant task files"
```

---

## Riepilogo

| Task | File | Feature | Dipende da |
|------|------|---------|------------|
| 1 | implementer-prompt.md | Accumulated Learnings | — |
| 2 | siae-subagent-development/SKILL.md | Accumulated Learnings | Task 1 |
| 3 | siae-writing-plans/SKILL.md | Split Plans | — |
| 4 | siae-subagent-development/SKILL.md + siae-executing-plans/SKILL.md | Split Plans (detect) | Task 3 |

**Parallelismo possibile:** Task 1 e Task 3 sono indipendenti.
**Ordine obbligatorio:** Task 1 → Task 2, Task 3 → Task 4.
