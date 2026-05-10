---
name: siae-executing-plans
description: >
  Use when executing an approved implementation plan in a separate session
  (different from where plan was written). Reads docs/plans/<topic>/ overview
  + task-NN files, executes batch with human checkpoints. Examples: "esegui il
  piano nella sessione nuova", "carica il piano e implementa", "batch
  execution", piano con REQUIRED SUB-SKILL siae-executing-plans header.
---

# SIAE Executing Plans — Esecuzione Piano in Sessione Separata

> **Tipo:** Rigid | **Fase SDLC:** 4. Implementation (sessione separata)

---

## LA LEGGE DI FERRO

```
LEGGI IL PIANO CRITICAMENTE PRIMA DI TOCCARE QUALSIASI FILE.
ESEGUI PER BATCH. RIPORTA. ATTENDI FEEDBACK.
```

<EXTREMELY-IMPORTANT>
Stai per implementare task da un piano senza aver letto e rivisto il piano completo?
FERMATI. Leggi TUTTO il piano prima di toccare qualsiasi file.

Stai per procedere senza checkpoint umano dopo il batch?
FERMATI. Ogni batch di 3 task richiede report + attesa feedback. Non procedere alla cieca.

Stai per improvvisare qualcosa non previsto dal piano?
FERMATI. Se non e' nel piano, non farlo. Proponi la modifica nel report e attendi.
</EXTREMELY-IMPORTANT>

**Annuncia all'inizio:** "Uso siae-executing-plans per implementare il piano."

---

## Differenza da siae-subagent-development

| Questa skill | siae-subagent-development |
|-------------|--------------------------|
| Sessione separata aperta dall'utente | Stessa sessione dell'orchestratore |
| Claude esegue direttamente i task | Claude dispatcha subagent per ogni task |
| Batch di 3 task + checkpoint umano | 2 reviewer automatici per ogni task |
| Checkpoint: l'utente decide se continuare | Checkpoint: spec-reviewer + code-quality-reviewer |
| Adatto per iterazione lenta/controllata | Adatto per iterazione rapida e automatizzata |

---

## Quando si Applica

Sessione nuova con piano in `docs/plans/` + header `REQUIRED SUB-SKILL:
siae-executing-plans` (oppure scelta "sessione separata" da `siae-writing-plans`).

**NON usare:** sessione originale con orchestratore (`siae-subagent-development`)
o piano inesistente (`siae-brainstorming`).

---

## Processo

### Step 0 — Setup Workspace Isolato (opzionale)

Se il progetto richiede branch dedicato o workspace isolato:

```
REQUIRED SUB-SKILL: siae-git-worktrees (opzionale)
```

Dettagli setup, sync hooks, cleanup → `reference/executing-plans-worktree.md`.

### Step 1 — Carica e Rivedi il Piano

🟢 SICURO

1. Leggi il file piano in `docs/plans/`. Rivedi criticamente.
2. Se hai dubbi: solleva PRIMA di iniziare. Non procedere alla cieca.
3. Se nessun dubbio: crea task per ogni item e procedi.

**Detect formato:** directory con `overview.md` → split (leggi `overview.md`
per lista task + stato); altrimenti file `*-plan.md` → legacy monolitico.

**Annuncia:**
```
PIANO CARICATO: docs/plans/<topic>/overview.md (split)
               | docs/plans/<filename>.md (legacy)
Task totali: N · Primo batch: Task 1-3
Domande/problemi: [nessuno | lista]
```

### Step 2 — Esegui Batch (default: 3 task)

🟡 MEDIO — Pre-flight prima di ogni task con modifica file

**Formato split:** per ogni task nel batch, leggi solo
`docs/plans/<topic>/task-NN-<nome>.md`. Non rileggere overview o altri task.

**Formato legacy:** estrai la sezione task dal file monolitico.

Per ogni task nel batch:
1. Segna come in_progress
2. Segui ogni step esattamente come scritto nel piano
3. Esegui le verifiche specificate nel piano
4. Segna come completato
5. Aggiorna marker piano (`[PENDING]` → `[DONE]`/`[BLOCKED]`) e checkbox
   dual-format → dettagli `reference/executing-plans-sync.md`
6. Committa il piano aggiornato (commit separato dal codice)

**Per ogni task implementativo:**

```
REQUIRED SUB-SKILL: siae-tdd
```

**Stop immediato se:**
- Blocco a meta' task (dipendenza mancante, test fallisce ripetutamente)
- Il piano ha lacune che impediscono di procedere
- Non capisci un'istruzione
- La verifica fallisce piu' di 2 volte sullo stesso step

### Step 3 — Report Post-Batch

🟢 SICURO

Dopo ogni batch completato, riporta:

```
BATCH COMPLETATO: Task [N]-[M]

Implementato:
  - [descrizione task 1]
  - [descrizione task 2]
  - [descrizione task 3]

Stato piano: X/Y [DONE], Z [BLOCKED], W [PENDING]

Verifica:
  [output sintetico dei comandi eseguiti]

Prossimo batch: Task [N+1]-[N+3]

Pronto per feedback.
```

**Attendi** risposta dell'utente prima di procedere.

### Step 4 — Continua o Correggi

In base al feedback:
- **Applica le correzioni** se richiesto
- **Esegui il batch successivo** se OK
- **Ripeti** fino al completamento di tutti i task

### Step 4b — Plan Completion Gate

Verifica marker `[PENDING]`/`[BLOCKED]`/`[DONE]` sull'intero piano (comandi
`grep -c` in `reference/executing-plans-sync.md`).

**Se PENDING > 0 o BLOCKED > 0:** STOP. Piano non completo.
**Se tutti [DONE]:** procedi con Step 5.

### Step 5 — Completamento

```
REQUIRED SUB-SKILL: siae-verification
REQUIRED SUB-SKILL: siae-finishing-branch
```

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi max per step | 2 | Fermati. Chiedi all'utente prima di riprovare. |
| Step totali per batch | 3 | Decomponi se serve di piu'. |
| Output max per analisi | 300 righe | Sintetizza. |

---

## Permission Denied Handling

**Bash negato (test/build):** presenta i comandi esatti, chiedi all'utente
di eseguirli, procedi al Report sui risultati forniti.

**Write negato:** presenta il codice come output testuale con path esatti,
attendi che l'utente applichi, riprendi dalla verifica.

---

## Skill correlate

- `siae-writing-plans` — produce il piano che questa skill esegue
- `siae-subagent-development` — alternativa per sessione unica con subagent
- `siae-git-worktrees` — setup workspace isolato (opzionale)
- `siae-tdd` — per ogni task implementativo
- `siae-verification` — verifica finale pre-completamento
- `siae-finishing-branch` — chiusura branch post-implementazione
