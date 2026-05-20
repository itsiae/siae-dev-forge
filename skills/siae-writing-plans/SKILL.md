---
name: siae-writing-plans
description: >
  Use when transforming an approved design doc into a step-by-step implementation
  plan with bite-sized tasks. Produces docs/plans/<topic>/ directory with overview
  + task-NN files. Examples: "scrivi piano implementativo", "decomponi design in
  task", "trasforma design in piano", "piano bite-sized", "aggiorna piano",
  "task implementativi", "docs/plans/".
validates_via:
  predicate: plan_produced
  evidence_type: file_exists
  evidence_check: "docs/plans/<topic>/overview.md exists with task-NN files AND [PENDING]/[DONE] markers"
---

# SIAE Writing Plans — Da Design a Piano Implementativo

> **Tipo:** Rigid | **Fase SDLC:** 2. Design (output)
>
> 📊 **Dai repo itsiae:** piani con > 13 task hanno 3x piu' probabilita' di essere
> abbandonati a meta'. Decomposizione bite-sized e' critica.
> Fonte: analisi su 816 repository GitHub itsiae.

## HARD-GATE

<EXTREMELY-IMPORTANT>
NON scrivere il piano senza un design approvato. Se non esiste un design doc
validato dall'utente in `docs/plans/`, torna a `siae-brainstorming` prima.

- Esiste un design doc approvato? NO → FERMATI. Torna a `siae-brainstorming`.
- SI → procedi con la decomposizione in task.

Un piano senza design = assunzioni non esaminate = lavoro da rifare.
Un piano con step vaghi ("aggiungi la validazione") = un piano che fallira'.
</EXTREMELY-IMPORTANT>

---

## Quando si applica

**Invocata da `siae-brainstorming`** dopo l'approvazione del design (Step 6).

**Invocata direttamente quando:**
- Hai un design doc gia' approvato e devi produrre il piano
- Devi aggiornare/rivedere un piano esistente dopo feedback
- Hai una spec/requisiti e il design e' implicito o semplice

**NON usare quando:**
- Il design non e' ancora stato approvato (prima `siae-brainstorming`)
- Il piano esiste ed e' gia' valido — non riscriverlo senza motivo

---

## Processo

1. **Leggi design doc** approvato in `docs/plans/YYYY-MM-DD-*-design.md` —
   identifica goal, scope, componenti, stack, criteri di accettazione, dipendenze.
2. **Decomponi in task** atomici 2-5 minuti — ogni task atomico, TDD, verificabile,
   eseguibile da subagent con contesto fresco. Template completo (overview.md +
   task-NN format + regole di qualita' + anti-pattern):
   `reference/writing-plans-task-template.md`.
3. **Scrivi il piano** come directory `docs/plans/<topic>/` con `overview.md`
   (header + indice task con stato `[PENDING]`) + un file `task-NN-<nome>.md`
   per task. Vedi template per il formato esatto.
4. **Step 3b — Placeholder scan** (gate inline, sotto)
5. **Step 3c — Plan review** (gate inline, sotto)
6. **Salva + commit** + execution handoff — vedi
   `reference/writing-plans-execution-handoff.md`.

---

### Step 3b — Placeholder Scan (Gate Obbligatorio, INLINE)

Prima di salvare il piano, scan completo per placeholder e riferimenti vaghi.
Un piano con placeholder e' un piano che fallira'.

**Pattern vietati — il piano NON e' pronto se contiene:**

| Pattern | Esempio |
|---------|---------|
| `TBD` | "Formato TBD" |
| `TODO` | "TODO: definire schema" |
| `da definire` | "Endpoint da definire" |
| `da decidere` | "Approccio da decidere" |
| `similar to` / `simile a` | "Simile al Task 2" |
| `come sopra` / `vedi sopra` | "Come sopra ma per utenti" |
| `da completare` | "Implementazione da completare" |
| `[...]` / `...` in codice | `function validate(...) { ... }` |
| Riferimenti circolari | "Vedi Task N" senza contenuto inline |

**Procedura:**
1. Scansiona ogni `task-NN-*.md` per i pattern sopra.
2. Se trovi match → lista i match con file e riga.
3. Risolvi OGNI placeholder con contenuto concreto (path, codice, comando).
4. Ri-scansiona fino a zero match.
5. Solo allora procedi a Step 3c.
6. Emetti checkpoint:

```
[WRITING-PLANS:PLACEHOLDER-SCAN] Scan completato
  File scansionati: {N}
  Pattern trovati: {0 = PASS / N = FAIL}
  Iterazioni: {N}
```

Un piano che passa questo gate ha zero ambiguita' per il subagent.

---

### Step 3c — Plan Review (Gate Obbligatorio, INLINE)

Dopo il placeholder scan (pattern testuali), lancia un subagent plan-reviewer
che verifica la qualita' semantica del piano.

**Differenza col placeholder scan (Step 3b):**
- Step 3b: pattern matching testuale (TBD, TODO, ...)
- Step 3c: verifica semantica (path validi, codice completo, coerenza col design)

**Processo:**

1. Lancia subagent con il prompt in [plan-reviewer-prompt.md](plan-reviewer-prompt.md)
   passando `{plan_directory}` e `{design_doc_path}`.
2. Il reviewer analizza ogni `task-NN-*.md` singolarmente (chunk-by-chunk).
3. Leggi il report del reviewer.
4. Se ci sono issue BLOCK:
   a. Fixa le issue nei task file.
   b. Ri-lancia il reviewer (loop max 5 iterazioni).
   c. Se dopo 5 iterazioni ci sono ancora BLOCK → escalation all'utente.
5. Se ci sono solo WARN (zero BLOCK): presenta i WARN all'utente.
6. Se zero issue: procedi a Step 4 (salva + commit).

**Checkpoint:**

```
[WRITING-PLANS:PLAN-REVIEW] Plan review completata
  Task reviewati: {N}
  Issue: {N BLOCK / N WARN}
  Iterazioni: {N}/5
  DECISIONE: {APPROVED / REVISE}
```

---

## Salva e committa il piano

🟡 MEDIO — Mostra pre-flight card prima del commit.

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-writing-plans |
|:---|
| 📋 Piano: `docs/plans/<topic>/` · 🔢 Task: `<N> task definiti` |
| **▼ Azione** |
| 1. 📌 Commit piano implementativo → `docs/plans/<topic>/` |
| 💡 Perche': piano validato (Step 3b + 3c), pronto per commit |
| 🚫 Se NO: il piano resta non committato |

```bash
git add docs/plans/<topic>/
git commit -m "docs(plans): aggiungi piano implementativo per <feature>"
```

Per execution handoff (Subagent stessa sessione vs Sessione separata) vedi
`reference/writing-plans-execution-handoff.md`.

---

## REQUIRED SUB-SKILL

```
REQUIRED SUB-SKILL: siae-verification
```
Verifica che il piano sia coerente col design doc prima di committare.

```
REQUIRED SUB-SKILL: siae-subagent-development
```
Per execution dei task nella stessa sessione (handoff opzione 1).

```
REQUIRED SUB-SKILL: siae-executing-plans
```
Per execution dei task in sessione separata (handoff opzione 2).

---

## Classificazione rischio operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura design doc | 🟢 Sicuro | No |
| Scrittura piano su file | 🟢 Sicuro | No |
| Git commit piano | 🟡 Medio | Si |
| Execution handoff → subagent | 🟡 Medio | Si (in `siae-subagent-development`) |

---

## Reference

- `reference/writing-plans-task-template.md` — overview.md + task-NN template,
  regole di qualita', anti-pattern, retrocompatibilita' file unico
- `reference/writing-plans-execution-handoff.md` — opzione 1 (subagent) vs
  opzione 2 (sessione separata), criteri di scelta, permission denied handling
- `plan-reviewer-prompt.md` — prompt subagent plan-reviewer per Step 3c
