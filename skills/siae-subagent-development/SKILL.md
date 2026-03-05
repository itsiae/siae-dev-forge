---
name: siae-subagent-development
description: >
  Esecuzione piani implementativi con subagent freschi per task indipendenti.
  Trigger: piano implementativo presente, task indipendenti, /forge-implement.
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

---

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

**Output:**
```
PIANO DI IMPLEMENTAZIONE:
  Design doc:  docs/plans/YYYY-MM-DD-<topic>-design.md
  Task totali: N
  Ordine:      [lista ordinata dei task]
```

### Step 2 — Per Ogni Task: Dispatch Implementer

🟡 MEDIO — Mostra pre-flight card prima di lanciare ogni subagent

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

```
REQUIRED SUB-SKILL: siae-verification
```

Esegui il protocollo di verifica completo (IDENTIFICA-ESEGUI-LEGGI-VERIFICA-AFFERMA)
prima di dichiarare il task completato.

### Step 6 — Final Review Complessiva

🟢 SICURO

Dopo che tutti i task sono completati:

1. Verifica che l'intero piano sia coperto (nessun task dimenticato)
2. Esegui test suite completa del progetto
3. Verifica che non ci siano conflitti tra i task implementati
4. Produce report finale

**Output:**
```
IMPLEMENTAZIONE COMPLETATA:
  Piano:       docs/plans/YYYY-MM-DD-<topic>-design.md
  Task totali: N
  Task completati: N
  Review PASS: N/N spec + N/N quality
  Test suite:  [risultato]
  Verdetto:    [COMPLETO | PARZIALE]
```

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

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura piano implementativo | 🟢 Sicuro | No |
| Analisi dipendenze task | 🟢 Sicuro | No |
| Dispatch subagent implementer | 🟡 Medio | Si |
| Dispatch subagent spec-reviewer | 🟢 Sicuro | No |
| Dispatch subagent code-quality-reviewer | 🟢 Sicuro | No |
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

---

## Risorse Aggiuntive

- [implementer-prompt.md](implementer-prompt.md) — Prompt per subagent implementer
- [spec-reviewer-prompt.md](spec-reviewer-prompt.md) — Prompt per subagent spec reviewer
- [code-quality-reviewer-prompt.md](code-quality-reviewer-prompt.md) — Prompt per subagent code quality reviewer
