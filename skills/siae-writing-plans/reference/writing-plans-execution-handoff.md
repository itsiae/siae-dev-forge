# siae-writing-plans — Execution Handoff

> Reference linked da `../SKILL.md`. Pattern dettagliato per Step 5 (execution
> handoff dopo che il piano e' stato salvato e committato).

Dopo aver salvato e committato il piano, offri all'utente la scelta di
esecuzione. **NON invocare `siae-subagent-development` senza la scelta esplicita
dell'utente.**

---

## Prompt da emettere

```
Piano salvato in docs/plans/<topic>/. Come vuoi procedere?

1. Subagent (questa sessione) — dispatcho subagent freschi per ogni task,
   review spec + quality tra i task, iterazione rapida

2. Sessione separata — apri una nuova sessione con il file piano,
   esecuzione a batch con checkpoint umani

Quale preferisci?
```

---

## Opzione 1 — Subagent (stessa sessione)

```
REQUIRED SUB-SKILL: siae-subagent-development
```

**Quando preferirla:**
- Iterazione rapida, contesto sessione gia' caldo
- Piani con dipendenze fra task complesse (review tra task aiuta)
- L'utente vuole vedere il flusso completo in una sola sessione
- Task piccoli/medi (< 15 task)

**Comportamento:** rimani nella sessione corrente.
`siae-subagent-development` gestisce l'orchestrazione: dispatch subagent
implementer paralleli/sequenziali, review tra task, aggiornamento stato in
`overview.md`.

---

## Opzione 2 — Sessione separata

```
REQUIRED SUB-SKILL: siae-executing-plans
```

**Quando preferirla:**
- Piani lunghi (> 15 task), il context budget di una singola sessione non basta
- Esecuzione a batch con checkpoint umani fra blocchi
- L'utente vuole separare la fase "design+plan" dalla fase "execute"
- Vuoi un Claude fresco senza il context del brainstorming

**Comportamento:**
1. Guida l'utente ad aprire una nuova sessione Claude Code nella directory del
   progetto
2. Istruisci: "Carica il piano con: `cat docs/plans/<topic>/overview.md` e
   inizia l'implementazione seguendo la skill `siae-executing-plans`"
3. Il piano ha l'header `REQUIRED SUB-SKILL: siae-subagent-development` (per
   subagent dispatch dentro la nuova sessione) embedded nell'`overview.md` —
   il nuovo Claude lo trovera' automaticamente

---

## Decisione: quale scegliere

```
Domanda 1 — Quanti task ha il piano?
  ├── ≤ 15 task                              → Opzione 1 (subagent stessa sessione)
  └── > 15 task                              → Opzione 2 (sessione separata)

Domanda 2 — Il context della sessione attuale e' "caldo" sul dominio?
  ├── SI (brainstorming appena finito)       → Opzione 1
  └── NO (piano scritto giorni fa)           → Opzione 2

Domanda 3 — L'utente vuole checkpoint umani fra task?
  ├── SI (review manuale fra batch)          → Opzione 2
  └── NO (full autonomy con review subagent) → Opzione 1

Default se nessuna preferenza: Opzione 1 (subagent stessa sessione).
```

---

## Permission Denied Handling (Step 5)

**Se Write viene negato (salvataggio piano):**
1. Presenta il piano completo come output testuale formattato in chat
2. Indica il path suggerito: `docs/plans/<topic>/overview.md` + task files
3. L'utente puo' copiare il contenuto manualmente
4. Procedi all'execution handoff normalmente

**Se Bash (git commit) viene negato:**
1. Il file e' stato scritto ma non committato
2. Informa: `git add docs/plans/<topic>/ && git commit -m "docs(plans): aggiungi piano per <feature>"`
3. Procedi all'execution handoff normalmente

---

## Integrazione SDLC

```
siae-brainstorming (Step 6: design approvato)
    └── REQUIRED SUB-SKILL: siae-writing-plans
        └── piano bite-sized salvato in docs/plans/<topic>/
            └── execution handoff:
                ├── subagent → REQUIRED SUB-SKILL: siae-subagent-development
                └── sessione separata → REQUIRED SUB-SKILL: siae-executing-plans
```

**Skill correlate:**
- `siae-brainstorming` — produce il design doc che questa skill consuma
- `siae-subagent-development` — esegue il piano nella stessa sessione
- `siae-executing-plans` — esegue il piano in sessione separata
- `siae-tdd` — ogni subagent implementer usa TDD per ogni task del piano
