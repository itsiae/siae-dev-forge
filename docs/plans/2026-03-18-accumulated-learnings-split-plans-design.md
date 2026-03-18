# Accumulated Learnings + Split Plans — Design Doc

> **Data:** 2026-03-18
> **Stato:** Approvato
> **SP:** 3 SP-Umano / 1 SP-Augmented
> **Ispirazione:** Superpowers [#601](https://github.com/obra/superpowers/issues/601) (6 👍) + [#512](https://github.com/obra/superpowers/issues/512) (2 👍)

---

## Problema

### 1. Accumulated Learnings

Quando `siae-subagent-development` dispatcha task 1, 2, 3... ogni subagent parte
da zero. Se il task 3 scopre un quirk del codebase (es. "Drizzle ORM wrappa
PostgresError dentro DrizzleQueryError"), il task 4 non lo sa e perde tempo a
riscoprirlo.

### 2. Split Plans

Un piano monolitico da 48k+ caratteri viene riletto 3-4 volte durante
l'esecuzione, sprecando ~45-60k token in riletture. Ogni subagent riceve
l'intero piano anche se gli serve solo il suo task.

---

## Soluzione

### Feature 1: Accumulated Learnings

**Approccio:** sezione "Project Discoveries" nel report implementer + accumulo nel controller.

**Cambiamenti in `implementer-prompt.md`:**

Aggiungere al "Report di Completamento" una sezione `Project Discoveries`:

```
IMPLEMENTER REPORT:
  Task:           {task_id} — {task_title}
  ...esistente...

  Project Discoveries:
    - [discovery 1: cosa hai scoperto che non era nel piano]
    - [discovery 2: quirk del codebase, gotcha, errore ricorrente]
    - [nessuna: se non hai scoperto nulla di rilevante]
```

Guida su cosa riportare:
- Quirk del codebase (es. "ORM wrappa errori in tipo custom")
- Pattern non documentati scoperti durante l'implementazione
- Gotcha di configurazione o dipendenze
- **NON** riportare: cose ovvie dal piano, best practice generiche

**Cambiamenti in `siae-subagent-development/SKILL.md`:**

- **Step 1** (carica piano): inizializza blocco `ACCUMULATED DISCOVERIES` vuoto. Reset ad ogni nuovo piano.
- **Step 2** (dispatch implementer): inietta il blocco nel prompt del subagent:

```
**Discoveries dai task precedenti (usale, non riscoprirle):**

{accumulated_discoveries}
```

- **Step 5** (mark task complete): dopo il report, estrarre le discoveries dal report implementer e aggiungerle al blocco accumulato.

### Feature 2: Split Plans

**Approccio:** directory plan con overview + task files.

**Cambiamenti in `siae-writing-plans/SKILL.md`:**

Step 3 produce una directory invece di un file unico:

```
docs/plans/<topic>/
  overview.md          # header, goal, architettura, stack, SP, indice task con stato
  task-01-<nome>.md    # step completo con TDD
  task-02-<nome>.md
  ...
  task-NN-<nome>.md
```

- `overview.md`: header con `REQUIRED SUB-SKILL`, goal, architettura, stack, SP,
  lista task con stato `[PENDING]`/`[DONE]`/`[BLOCKED]` e dipendenze
- Ogni `task-NN-<nome>.md`: task completo (file coinvolti, step TDD, codice, comandi)
- Commit: `git add docs/plans/<topic>/ && git commit`

**Retrocompatibilita':** se l'orchestratore trova un file `.md` invece di una
directory, lo tratta come piano monolitico (formato legacy). Nessun piano
esistente si rompe.

**Cambiamenti in `siae-subagent-development/SKILL.md`:**

- **Step 1** (carica piano): detecta formato (directory vs file unico).
  Se directory, legge `overview.md` per la lista task.
- **Step 2** (dispatch implementer): passa al subagent solo `overview.md`
  (contesto) + `task-NN-<nome>.md` (task specifico). Non legge gli altri task → risparmio token.

**Cambiamenti in `siae-executing-plans/SKILL.md`:**

- **Step 1**: stessa logica di detect formato (directory vs file)
- **Step 2**: per ogni task nel batch, legge solo il file task corrispondente
- **Step 3** (report): aggiorna stato in `overview.md` (`[PENDING]` → `[DONE]`)

---

## Decisioni Architetturali

| Decisione | Scelta | Alternativa scartata | Motivo |
|-----------|--------|---------------------|--------|
| Dove accumulare discoveries | In memoria del controller (sessione) | File `discoveries.md` persistente | Le discoveries sono specifiche della sessione, non del progetto |
| Formato piano | Directory con file separati | Piano monolitico con estrazione | Risparmio token reale solo se il subagent non legge tutto |
| Retrocompatibilita' | Detect automatico formato | Flag esplicito | Zero friction per piani esistenti |
| Soglia per split | Sempre directory | Split solo se > 5 task | Un formato unico e' piu' semplice da mantenere |

---

## File Coinvolti

| File | Azione | Feature |
|------|--------|---------|
| `skills/siae-subagent-development/SKILL.md` | Modifica | Entrambe (learnings + split detect) |
| `skills/siae-subagent-development/implementer-prompt.md` | Modifica | Accumulated Learnings |
| `skills/siae-writing-plans/SKILL.md` | Modifica | Split Plans |
| `skills/siae-executing-plans/SKILL.md` | Modifica | Split Plans |

---

## Criteri di Accettazione

1. implementer-prompt.md contiene sezione "Project Discoveries" nel report
2. SKILL.md di subagent-development inietta `ACCUMULATED DISCOVERIES` nel prompt subagent
3. SKILL.md di subagent-development estrae e accumula discoveries dopo ogni task
4. Le discoveries si azzerano al caricamento di un nuovo piano (Step 1)
5. siae-writing-plans produce struttura directory `overview.md` + `task-NN-*.md`
6. siae-subagent-development detecta formato (directory vs file)
7. siae-subagent-development passa solo overview + task file al subagent
8. siae-executing-plans detecta formato e aggiorna stato in `overview.md`
9. Retrocompatibilita': piano monolitico esistente continua a funzionare
10. `run-all.sh` passa senza errori
