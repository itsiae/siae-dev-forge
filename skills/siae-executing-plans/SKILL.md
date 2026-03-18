---
name: siae-executing-plans
description: >
  Esegue un piano implementativo esistente in una sessione separata da quella
  in cui il piano e' stato scritto (per la stessa sessione usa siae-subagent-development).
  Trigger: sessione nuova/separata con piano in docs/plans/, batch execution
  richiesta, piano con REQUIRED SUB-SKILL siae-executing-plans.
---

# SIAE Executing Plans — Esecuzione Piano in Sessione Separata

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║              🔨 DevForge · EXECUTING PLANS                    ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

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

> 📊 **Dai repo itsiae:** Sessioni che seguono il piano step-by-step hanno 82% completion rate vs 34% per sessioni ad-hoc.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

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

- Stai aprendo una nuova sessione con un piano in `docs/plans/`
- Il piano contiene `REQUIRED SUB-SKILL: siae-executing-plans`
- L'utente ha scelto "sessione separata" da `siae-writing-plans`

**NON usare quando:**
- Sei nella sessione originale con l'orchestratore (usa `siae-subagent-development`)
- Il piano non esiste ancora (prima `siae-brainstorming`)

---

## Processo

### Step 0 — Setup Workspace Isolato (opzionale)

🟢 SICURO

Se il progetto richiede un branch dedicato o workspace isolato, invoca `siae-git-worktrees`
prima di iniziare l'implementazione. Previene conflitti con lavoro in corso su altri branch.

```
REQUIRED SUB-SKILL: siae-git-worktrees (opzionale)
```

### Step 1 — Carica e Rivedi il Piano

🟢 SICURO

1. Leggi il file piano in `docs/plans/`
2. Rivedi criticamente — identifica domande o problemi
3. **Se hai dubbi:** Solleva PRIMA di iniziare. Non procedere alla cieca.
4. **Se nessun dubbio:** Crea task per ogni item e procedi

**Detect formato piano:**

1. Cerca directory in `docs/plans/` che contiene `overview.md`
   → formato split. Leggi `overview.md` per lista task e stato.
2. Se non trovata: cerca file `*-plan.md` in `docs/plans/`
   → formato legacy monolitico.

**Annuncia:**
```
PIANO CARICATO: docs/plans/<topic>/overview.md (formato split)
               oppure docs/plans/<filename>.md (formato legacy)
Task totali: N
Primo batch: Task 1-3
Domande/problemi: [nessuno | lista]
```

### Step 2 — Esegui Batch (default: 3 task)

🟡 MEDIO — Pre-flight prima di ogni task con modifica file

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-executing-plans |
|:---|
| 📋 Piano: `<filename>.md` · 🔢 Batch: Task `<N>-<M>` di `<totale>` |
| **▼ Azione** |
| 1. ✏️ Azione: Implementazione batch con TDD → `<file coinvolti>` |
| 💡 Perche': Batch pronto, piano validato |
| 🚫 Se NO: Il batch non viene eseguito, attende feedback |

**Formato split:** per ogni task nel batch, leggi solo
`docs/plans/<topic>/task-NN-<nome>.md`. Non rileggere overview o altri task.

**Formato legacy:** estrai la sezione task dal file monolitico.

Per ogni task nel batch:
1. Segna come in_progress
2. Segui ogni step esattamente come scritto nel piano
3. Esegui le verifiche specificate nel piano
4. Segna come completato
5. Aggiorna il marker nel piano: `[PENDING]` → `[DONE]`
6. Se bloccato: `[PENDING]` → `[BLOCKED]` — motivo
7. Committa il piano aggiornato:

```bash
git add docs/plans/<filename>.md
git commit -m "docs(plans): mark task N as DONE in <piano>"
```

**Per ogni task, usa:**

```
REQUIRED SUB-SKILL: siae-tdd
```

**Stop immediato se:**
- Blocco a meta' task (dipendenza mancante, test che fallisce ripetutamente)
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

**Aggiornamento stato (formato split):**
Aggiorna la colonna `Stato` nella tabella indice di `overview.md`:
`[PENDING]` → `[DONE]` o `[BLOCKED]`

**Aggiornamento stato (formato legacy):**
Aggiorna il marker nel file monolitico come prima.

**Attendi** risposta dell'utente prima di procedere.

### Step 4 — Continua o Correggi

In base al feedback:
- **Applica le correzioni** se richiesto
- **Esegui il batch successivo** se OK
- **Ripeti** fino al completamento di tutti i task

### Step 4b — Plan Completion Gate

Prima di dichiarare il piano completato, verifica:

```bash
grep -c "\[PENDING\]" docs/plans/<filename>.md
grep -c "\[BLOCKED\]" docs/plans/<filename>.md
grep -c "\[DONE\]" docs/plans/<filename>.md
```

**Nota formato split:** i marker `[PENDING]`/`[DONE]`/`[BLOCKED]` si trovano
nella tabella indice di `overview.md`, non nei file task singoli.

**Se PENDING > 0 o BLOCKED > 0:** STOP. Il piano non e' completo.

```
🔴 PIANO INCOMPLETO — non puoi procedere con siae-verification.

Piano: docs/plans/<filename>.md
Stato: X [DONE] / Y [PENDING] / Z [BLOCKED]

Opzioni:
1. Completa i task [PENDING]
2. Chiedi all'utente se i [BLOCKED] vanno risolti o rimossi dal piano
3. Solo quando tutti sono [DONE] → procedi con Step 5
```

**Se tutti [DONE]:** procedi con Step 5 (Completamento).

---

### Step 5 — Completamento

Dopo tutti i task completati:

```
REQUIRED SUB-SKILL: siae-verification
```

Esegui la suite test completa e verifica l'intero piano. Poi:

```
REQUIRED SUB-SKILL: siae-finishing-branch
```

---

## Quando Fermarsi e Chiedere Aiuto

**STOP immediato quando:**
- Blocco a meta' batch (dipendenza, test fallisce, istruzione poco chiara)
- Il piano ha gap critici che impediscono di iniziare
- Non capisci un'istruzione
- La verifica fallisce ripetutamente

**Chiedi chiarimento invece di indovinare.**

**NON** forzare attraverso i blocchi. Non inventare soluzioni non nel piano.

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi max per step | 2 | Fermati. Chiedi all'utente prima di riprovare. |
| Step totali per batch | 3 | Se ne servono di piu', il batch e' troppo grande. Decomponi. |
| Output max per analisi | 300 righe | Sintetizza. L'utente non legge wall-of-text. |

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Posso implementare tutti i task senza fermarmi" | I batch con checkpoint esistono per un motivo. Fermati e riporta. |
| "E' ovvio cosa fare qui, improvviso" | Se non e' nel piano, non farlo. Chiedi prima. |
| "Ho gia' fatto questo tipo di task, salto la verifica" | Ogni contesto e' diverso. Esegui la verifica. |
| "Il piano dice X ma Y e' meglio" | Il piano e' stato approvato. Implementa X. Proponi Y nel report. |
| "Tre task per batch e' troppo poco" | Il numero di batch e' un parametro di controllo umano, non di efficienza. |
| "Posso saltare il report se il batch e' semplice" | Il report e' il checkpoint umano. Non e' opzionale. |
| "Il plan header dice siae-subagent-development, uso quello" | Se sei in sessione separata, usa questa skill. |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura e revisione piano | 🟢 Sicuro | No |
| Implementazione task (scrittura file) | 🟡 Medio | Si |
| Esecuzione verifica (test, build) | 🟡 Medio | Si |
| Git commit post-task | 🟡 Medio | No (commit locale) |
| Report batch e attesa feedback | 🟢 Sicuro | No |

---

## Vincoli

1. **SEMPRE** leggere e rivedere il piano prima di toccare qualsiasi file
2. **SEMPRE** usare `siae-tdd` per ogni task implementativo
3. **SEMPRE** riportare dopo ogni batch e attendere feedback
4. **STOP** immediato in caso di blocco — non indovinare
5. **REQUIRED SUB-SKILL: siae-verification** prima di dichiarare l'intero piano completato
6. **REQUIRED SUB-SKILL: siae-finishing-branch** per chiusura branch
7. **PRE-FLIGHT OBBLIGATORIA** per modifiche file e test run

---

## Permission Denied Handling

**Se Bash viene negato (test/build):**
1. Presenta i comandi di verifica esatti
2. Chiedi all'utente di eseguirli e riportare l'output
3. Procedi con Step 3 (Report) sui risultati forniti

**Se Write viene negato (implementazione):**
1. Presenta il codice da implementare come output testuale
2. Indica i path esatti e i file da modificare
3. Attendi che l'utente applichi le modifiche
4. Riprendi dal punto di verifica

---

## Integrazione SDLC

```
siae-writing-plans (Step 5: utente sceglie "sessione separata")
    └── utente apre nuova sessione con piano
        └── REQUIRED SUB-SKILL: siae-executing-plans
            ├── batch 1 → report → feedback
            ├── batch 2 → report → feedback
            └── batch N → siae-verification → siae-finishing-branch
```

**Skill correlate:**
- `siae-writing-plans` — produce il piano che questa skill esegue
- `siae-subagent-development` — alternativa per sessione unica con subagent
- `siae-git-worktrees` — setup workspace isolato pre-implementazione (opzionale)
- `siae-tdd` — usata per ogni task implementativo
- `siae-verification` — verifica finale pre-completamento
- `siae-finishing-branch` — chiusura branch post-implementazione
