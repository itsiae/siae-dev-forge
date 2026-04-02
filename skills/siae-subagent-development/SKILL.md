---
name: siae-subagent-development
description: >
  Dispatcha task implementativi a subagent paralleli da un piano validato nella
  sessione corrente.
  Trigger: /forge-implement, implementa il piano, dispatcha task, lancia implementer,
  subagent, controller-subagent, orchestrazione implementazione.
---

# SIAE Subagent Development — Orchestratore Implementazione

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║              🔨 DevForge · SUBAGENT DEVELOPMENT               ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 4. Implementation (orchestrazione)

---

## LA LEGGE DI FERRO

```
OGNI TASK VIENE IMPLEMENTATO DA UN SUBAGENT FRESCO, REVISIONATO DA DUE REVIEWER INDIPENDENTI
```

Nessun task viene dichiarato completo senza:
1. Implementazione da subagent con contesto fresco
2. Review di conformita' alla specifica (spec-reviewer)
3. Review di qualita' del codice (code-quality-reviewer)

<EXTREMELY-IMPORTANT>
Stai per implementare codice direttamente invece di dispatchare un subagent?
FERMATI. Ogni task va implementato da un subagent fresco — nessuna eccezione.
Stai per dichiarare un task completo senza PASS da entrambi i reviewer?
FERMATI. Nessun completamento senza spec-review + code-quality-review.

"Posso implementare io, conosco il codice" = bias accumulato = bug invisibili.
"La review e' eccessiva per questo task" = i bug peggiori vengono dai task "semplici".

**Orchestrator Boundary:**
L'orchestratore NON implementa codice, NON fa review di codice, NON modifica file
di produzione. Ruolo esclusivo: caricare task, dispatchare subagent, raccogliere
risultati, aggiornare stato piano.
"Posso farlo io velocemente" = bias accumulato = il motivo per cui esistono i subagent.
</EXTREMELY-IMPORTANT>

---

> 📊 **Dai repo itsiae:** Il 28% dei task implementati da subagent senza spec-review conteneva drift rispetto al design doc originale.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

## Quando si Applica

**Prerequisiti obbligatori:**
- Un piano implementativo esiste in `docs/plans/` (prodotto da `siae-brainstorming`)
- Il piano contiene task indipendenti o ordinabili
- Siamo nella stessa sessione di lavoro

**NON usare quando:**
- Il task e' singolo e semplice (usa le skill standard)
- Non esiste un piano implementativo (prima `siae-brainstorming`)
- I task sono troppo interdipendenti per essere parallelizzati

---

## Processo di Orchestrazione

### Step 1 — Carica il Piano

🟢 SICURO

1. Identifica il design doc piu' recente in `docs/plans/`
2. Estrai la lista dei task dal piano
3. Determina l'ordine di esecuzione (rispetta le dipendenze)
4. Presenta il piano all'utente per conferma

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

**Output:**
```
PIANO DI IMPLEMENTAZIONE:
  Design doc:  docs/plans/YYYY-MM-DD-<topic>-design.md
  Task totali: N
  Ordine:      [lista ordinata dei task]
```

**Inizializza Accumulated Discoveries:**

Crea un blocco vuoto che verra' popolato durante l'esecuzione:

```
ACCUMULATED DISCOVERIES:
(nessuna — primo task)
```

Questo blocco si azzera ogni volta che viene caricato un nuovo piano.
Non persiste tra sessioni o tra piani diversi.

### Step 2 — Per Ogni Task: Dispatch Implementer

Costruisci la card come MARKDOWN TABLE direttamente nella risposta testuale.

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-subagent-development |
|:---|
| 🤖 Task: `<nome task dal piano>` · 📋 Piano: `docs/plans/<file>.md` |
| **▼ Azione** |
| 1. 🚀 Dispatch subagent implementer → `docs/plans/<file>.md` |
| 💡 Perche': Subagent con contesto fresco modifichera file reali |
| 🚫 Se NO: Il task non viene implementato, piano resta in attesa |

Per ogni task nel piano, lancia un subagent implementer con il prompt definito
in [implementer-prompt.md](implementer-prompt.md).

**Il subagent implementer:**
1. Riceve il testo completo del task + contesto del progetto
2. Chiede chiarimenti se necessario (risposta dall'orchestratore)
3. Implementa seguendo `REQUIRED SUB-SKILL: siae-tdd` (RED-GREEN-REFACTOR)
4. Esegue self-review con checklist
5. Produce un report di completamento

**Contesto del subagent:** fresco. Nessun bagaglio dalla sessione corrente.
Questo previene bias e assunzioni accumulate.

**Contesto arricchito:** oltre al task description e al contesto progetto,
inietta nel prompt del subagent il blocco accumulated discoveries:

```
**Discoveries dai task precedenti (usale, non riscoprirle):**

{accumulated_discoveries}
```

Per il primo task il blocco e' vuoto. Per i task successivi contiene
le scoperte accumulate dai task precedenti.

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

### Step 2b — GATE: Valuta Complessita' Task per Review Scaling

Prima di lanciare i reviewer, valuta la complessita' del task corrente.

| Complessita' | Segnali | Review |
|---|---|---|
| **Bassa** | config, rename, typo, 1-2 file, nessuna logica nuova | Solo code-quality-reviewer (spec-review elidibile con conferma utente) |
| **Media** | CRUD, refactoring, 3-5 file, logica moderata | Entrambi i reviewer (default, non elidibile) |
| **Alta** | Feature nuova, cross-module, integrazione, migrazione | Entrambi i reviewer (non elidibile) |

**Regole GATE:**
- Per complessita' bassa, CHIEDI all'utente: "Task '{nome}' e' a bassa complessita' (N file, nessuna logica nuova). Review completa (spec + code-quality) o ridotta (solo code-quality)?"
- Per complessita' media/alta, procedi con entrambi i reviewer senza chiedere
- L'utente decide SEMPRE — l'orchestratore non salta mai autonomamente
- Code-quality-reviewer non e' MAI elidibile (anche su task banali)
- Se in dubbio sulla complessita', tratta come media (entrambi i reviewer)

### Step 3 — Dispatch Spec-Reviewer

🟢 SICURO

Dopo che l'implementer dichiara il task completato, lancia un subagent spec-reviewer
con il prompt definito in [spec-reviewer-prompt.md](spec-reviewer-prompt.md).

**Il subagent spec-reviewer:**
1. Riceve il design doc + la lista dei file modificati
2. Applica il DISTRUST PATTERN: "L'implementer ha finito sospettosamente in fretta"
3. Verifica conformita': requisiti implementati, test presenti, YAGNI
4. Produce verdetto PASS/FAIL

**Se FAIL:**
- L'orchestratore comunica le discrepanze all'implementer
- L'implementer fixa
- Re-dispatch del spec-reviewer
- Max 2 iterazioni, poi escalation all'utente

### Step 4 — Dispatch Code-Quality-Reviewer

🟢 SICURO

Dopo il PASS del spec-reviewer, lancia un subagent code-quality-reviewer
con il prompt definito in [code-quality-reviewer-prompt.md](code-quality-reviewer-prompt.md).

**Il subagent code-quality-reviewer:**
1. Riceve i file modificati dal task
2. Esegue review a 6 punti SIAE (standard, security, test, architettura, quality, doc)
3. Produce report con severity (CRITICAL / MAJOR / MINOR / INFO)
4. Produce verdetto (APPROVED / CHANGES REQUESTED / BLOCKED)

**Se CHANGES REQUESTED o BLOCKED:**
- L'orchestratore comunica le issue all'implementer
- L'implementer fixa
- Re-dispatch del code-quality-reviewer
- Max 2 iterazioni, poi escalation all'utente

### Step 5 — Mark Task Complete

🟢 SICURO

Dopo il PASS di entrambi i reviewer:

**Aggiorna il piano:**
1. Apri `docs/plans/<filename>.md`
2. Aggiorna il marker del task — **dual format:**
   - Formato marker: `[PENDING]` → `[DONE]` (o `[BLOCKED]`)
   - Formato checkbox: `- [ ] Task description` → `- [x] Task description`
   - Rileva quale formato usa il piano e aggiorna di conseguenza
3. Se il subagent ha fallito dopo 2 retry: `[PENDING]` → `[BLOCKED]` — motivo del fallimento
4. Committa:

```bash
git add docs/plans/<filename>.md
git commit -m "docs(plans): mark task N as DONE in <piano>"
```

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
REQUIRED SUB-SKILL: siae-verification
```

Esegui il protocollo di verifica completo (IDENTIFICA-ESEGUI-LEGGI-VERIFICA-AFFERMA)
prima di dichiarare il task completato.

### Step 5b — Plan Completion Gate

Prima della final review, verifica lo stato completo del piano:

```bash
grep -c "\[PENDING\]" docs/plans/<filename>.md
grep -c "\[BLOCKED\]" docs/plans/<filename>.md
grep -c "\[DONE\]" docs/plans/<filename>.md
```

**Se PENDING > 0 o BLOCKED > 0:** STOP. Non procedere alla final review.

```
🔴 PIANO INCOMPLETO

Stato: X [DONE] / Y [PENDING] / Z [BLOCKED]

Opzioni:
1. Dispatcha subagent per i task [PENDING] rimanenti
2. Chiedi all'utente se i [BLOCKED] vanno risolti o rimossi
3. Solo quando tutti [DONE] → procedi con Step 6
```

**Se tutti [DONE]:** procedi con Step 5c.

### Step 5c — Fresh-Eyes Review (Cross-Task)

🟢 SICURO

Dopo che tutti i task sono [DONE], lancia un subagent fresh-eyes-reviewer
con il prompt definito in [fresh-eyes-reviewer-prompt.md](fresh-eyes-reviewer-prompt.md).

**Il subagent fresh-eyes-reviewer:**
1. Usa `git diff $(git merge-base HEAD origin/main)..HEAD` per TUTTI i cambiamenti
2. Si concentra SOLO su problemi cross-task (6 categorie)
3. NON ri-revisa problemi per-task (gia' approvati da spec + quality reviewer)
4. Produce report con issue count + ready to merge assessment

**Se issue trovate:**
- L'orchestratore comunica le issue all'implementer appropriato
- L'implementer fixa
- Re-dispatch del fresh-eyes-reviewer
- Max 2 iterazioni, poi escalation all'utente

**Se zero issue:** procedi con Step 6 (Final Review).

---

### Step 6 — Final Review Complessiva

Costruisci la card come MARKDOWN TABLE direttamente nella risposta testuale.

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-subagent-development |
|:---|
| 🧪 Suite: `Test suite completa progetto` · ✅ Task completati: `N/N` |
| **▼ Azione** |
| 1. ▶️ Esecuzione test suite finale → `tests/` |
| 💡 Perche': Verifica integrazione post-implementazione |
| 🚫 Se NO: Completamento dichiarato senza verifica test suite |

Dopo che tutti i task sono completati:

1. Verifica che l'intero piano sia coperto (nessun task dimenticato)
2. Esegui test suite completa del progetto
3. Verifica che non ci siano conflitti tra i task implementati
4. Produce report finale

**Output:**
```
IMPLEMENTAZIONE COMPLETATA:
  Piano:       docs/plans/YYYY-MM-DD-<topic>-plan.md
  Task totali: N
  Task [DONE]:    N/N
  Task [BLOCKED]: 0
  Task [PENDING]: 0
  Review PASS: N/N spec + N/N quality
  Test suite:  [risultato]
  Verdetto:    COMPLETO (tutti [DONE])
```

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi max per step | 2 | Fermati. Chiedi all'utente prima di riprovare. |
| Step totali dell'orchestrazione | 4 | Se ne servono di piu', il piano ha troppi task per sessione. |
| Output max per analisi | 300 righe | Sintetizza. L'utente non legge wall-of-text. |

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Posso implementare tutto io senza subagent" | I subagent freschi non hanno bias accumulati. Usali. |
| "La review e' eccessiva per questo task" | Ogni task merita review. I bug peggiori vengono dai task "semplici". |
| "Posso saltare il spec-review se il codice e' ok" | Il codice puo' essere perfetto e non corrispondere alla specifica. |
| "Il code-review e' ridondante dopo il spec-review" | Spec e quality sono ortogonali. Uno verifica il "cosa", l'altro il "come". |
| "Ho gia' fatto self-review" | Il self-review ha bias di conferma. Serve un reviewer esterno. |
| "Troppi round di review rallentano" | I bug in produzione rallentano di piu'. 2 review sono un investimento. |
| "Il task e' troppo piccolo per un subagent" | Contesto fresco = meno errori. Anche per task piccoli. |
| "Conosco gia' la codebase, non serve contesto fresco" | La familiarita' genera cecita'. Il contesto fresco trova bug invisibili. |
| "Questo task e' banale, posso implementarlo io" | L'orchestratore non implementa. Mai. Dispatcha un subagent. |
| "La review spec non serve per un rename" | Chiedi all'utente. Non decidere tu. GATE scaling. |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura piano implementativo | 🟢 Sicuro | No |
| Analisi dipendenze task | 🟢 Sicuro | No |
| Dispatch subagent implementer | 🟡 Medio | Si |
| Dispatch subagent spec-reviewer | 🟢 Sicuro | No |
| Dispatch subagent code-quality-reviewer | 🟢 Sicuro | No |
| Dispatch subagent fresh-eyes-reviewer | 🟢 Sicuro | No |
| Esecuzione test suite finale | 🟡 Medio | Si |
| Report di completamento | 🟢 Sicuro | No |

---

## Permission Denied Handling

**Se Agent tool viene negato (dispatch subagent):**
1. Presenta il prompt completo del subagent come output testuale
2. Suggerisci all'utente di aprire una sessione Claude Code separata con il prompt
3. Fornisci istruzioni per ogni tipo di subagent:
   - **Implementer:** "Apri una nuova sessione nella directory del progetto e incolla questo prompt"
   - **Spec-reviewer:** "Dopo l'implementazione, apri una nuova sessione per la review con questo prompt"
   - **Code-quality-reviewer:** "Dopo la spec-review, usa questo prompt per la quality review"

**Se Bash viene negato (test suite finale — Step 6):**
- Fornisci i comandi test esatti per esecuzione manuale
- Chiedi all'utente di eseguire e riportare l'output

**Fasi completabili senza permessi:** Step 1 (Read piano), analisi dipendenze, generazione prompt
**Fasi che richiedono permessi:** Step 2-4 (Agent per subagent), Step 5-6 (Bash per test)

Se i permessi sono negati:
1. Completa l'analisi del piano e la generazione dei prompt
2. Presenta i prompt come istruzioni per sessioni separate
3. NON entrare in loop di retry su tool negato
4. NON dichiarare completamento per fasi non eseguite

---

## Vincoli

1. **SEMPRE** usare subagent freschi — mai implementare direttamente
2. **SEMPRE** 2 stadi di review per ogni task (spec + quality)
3. **MAX 2** iterazioni fix-review per stadio, poi escalation
4. **REQUIRED SUB-SKILL: siae-tdd** per ogni subagent implementer
5. **REQUIRED SUB-SKILL: siae-verification** prima di dichiarare qualsiasi task completato
6. **PRE-FLIGHT OBBLIGATORIA** per dispatch implementer e test suite
7. **NON** modificare file se non attraverso subagent
8. **NON** dichiarare completamento senza verdetto PASS da entrambi i reviewer
9. **REQUIRED** fresh-eyes review dopo completamento tutti i task — nessuna eccezione

---

## Risorse Aggiuntive

- [implementer-prompt.md](implementer-prompt.md) — Prompt per subagent implementer
- [spec-reviewer-prompt.md](spec-reviewer-prompt.md) — Prompt per subagent spec reviewer
- [code-quality-reviewer-prompt.md](code-quality-reviewer-prompt.md) — Prompt per subagent code quality reviewer
- [fresh-eyes-reviewer-prompt.md](fresh-eyes-reviewer-prompt.md) — Prompt per subagent fresh-eyes reviewer
