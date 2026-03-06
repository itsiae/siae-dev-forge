---
name: siae-executing-plans
description: >
  Use when opening a new session with an implementation plan to execute.
  Trigger: sessione separata con piano in docs/plans/, batch execution richiesta,
  piano con REQUIRED SUB-SKILL siae-executing-plans.
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

- Stai aprendo una nuova sessione con un piano in `docs/plans/`
- Il piano contiene `REQUIRED SUB-SKILL: siae-executing-plans`
- L'utente ha scelto "sessione separata" da `siae-writing-plans`

**NON usare quando:**
- Sei nella sessione originale con l'orchestratore (usa `siae-subagent-development`)
- Il piano non esiste ancora (prima `siae-brainstorming`)

---

## Processo

### Step 1 — Carica e Rivedi il Piano

🟢 SICURO

1. Leggi il file piano in `docs/plans/`
2. Rivedi criticamente — identifica domande o problemi
3. **Se hai dubbi:** Solleva PRIMA di iniziare. Non procedere alla cieca.
4. **Se nessun dubbio:** Crea task per ogni item e procedi

**Annuncia:**
```
PIANO CARICATO: docs/plans/<filename>.md
Task totali: N
Primo batch: Task 1-3
Domande/problemi: [nessuno | lista]
```

### Step 2 — Esegui Batch (default: 3 task)

🟡 MEDIO — Pre-flight prima di ogni task con modifica file

```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-executing-plans",
  "context": [
    {"emoji": "📋", "label": "Piano", "value": "<filename>.md"},
    {"emoji": "🔢", "label": "Batch", "value": "Task <N>-<M> di <totale>"}
  ],
  "actions": [
    {"emoji": "✏️", "label": "Implementazione batch con TDD", "path": "<file coinvolti>"}
  ],
  "reason": "Batch pronto, piano validato",
  "ifno": "Il batch non viene eseguito, attende feedback"
}' | python3 design-system/generate-card.py
```

Per ogni task nel batch:
1. Segna come in_progress
2. Segui ogni step esattamente come scritto nel piano
3. Esegui le verifiche specificate nel piano
4. Segna come completato

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
- `siae-tdd` — usata per ogni task implementativo
- `siae-verification` — verifica finale pre-completamento
- `siae-finishing-branch` — chiusura branch post-implementazione
