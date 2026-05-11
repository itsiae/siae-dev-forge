# Skill Alignment Baseline 2026-05-03

Branch: feat/devforge-agents-mcp-toolloading
Commit: 4a9eb57c5339f00f42e9c2d3ac61dd0015ef29b6

## Line counts (backbone)

| Skill | Lines |
|---|---|
| siae-brainstorming |      214 |
| siae-tdd |      179 |
| siae-debugging |      428 |
| siae-verification |      179 |
| siae-writing-plans |      422 |
| siae-executing-plans |      344 |
| siae-finishing-branch |      520 |
| using-devforge |       90 |

## Leakage grep count (SIAE-specific in backbone)

```
=== siae-brainstorming ===
(no match)
=== siae-tdd ===
23:NESSUN CODICE DI PRODUZIONE SENZA UN TEST FALLENTE PRIMA
=== siae-debugging ===
(no match)
=== siae-verification ===
(no match)
=== siae-writing-plans ===
(no match)
=== siae-executing-plans ===
(no match)
=== siae-finishing-branch ===
(no match)
=== using-devforge ===
(no match)
```

## Description frontmatter snapshot (first 15 lines each)

### siae-brainstorming
```yaml
---
name: siae-brainstorming
description: >
  Guida il processo di design da idea a design doc approvato, prima di QUALSIASI
  implementazione. Nessuna eccezione. Anche refactoring, bug fix, config change.
  Trigger: feature nuova, design, come procediamo, come progettiamo, quale approccio,
  valutare opzioni, trade-off, prima dell'implementazione, aggiungi feature,
  costruisci, crea componente, nuovo servizio, refactoring architetturale, migrazione,
  bug fix, refactoring, ottimizzazione, modifica codice, qualsiasi task implementativo.
validates_via:
  predicate: design_doc_produced
  evidence_type: file_pattern
  evidence_check: "docs/plans/*-design.md mtime > DEVFORGE_SESSION_START_S"
---

```

### siae-tdd
```yaml
---
name: siae-tdd
description: >
  Guida il ciclo TDD per qualsiasi scrittura di codice di produzione. Test PRIMA
  del codice, sempre.
  Trigger: implementazione feature, bug fix, refactoring, qualsiasi scrittura di
  codice, aggiungi metodo, crea classe, modifica logica, nuovo endpoint, scrivi
  funzione, implementa, codifica, sviluppa.
validates_via:
  predicate: tdd_red_green_observed
  evidence_type: state_file
  evidence_path: ~/.claude/.devforge-tdd-state
  evidence_check: "phase in (GREEN, REFACTOR), transitioned from RED"
---

```

### siae-debugging
```yaml
---
name: siae-debugging
description: >
  Esegue root cause investigation prima di proporre qualsiasi fix.
  Trigger: bug, errore, incident, test che fallisce, comportamento inatteso,
  eccezione, stacktrace, crash, errore di compilazione, build failure, 500,
  timeout, NullPointerException, TypeError, non funziona, rotto, fallisce, non va.
---

# SIAE Debugging Sistematico

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
```

### siae-verification
```yaml
---
name: siae-verification
description: >
  Verifica con evidenza prima di qualsiasi dichiarazione di completamento.
  Nessun "fatto" senza prova.
  Trigger: prima di commit, PR, task complete, dichiarazioni di successo, "fatto",
  "fixato", "funziona", "completato", "pronto", "implementato", "risolto",
  "test passano", "build verde", "tutto ok", "finito".
validates_via:
  predicate: verification_run_passed
  evidence_type: log_event
  evidence_check: "DEVFORGE_LOG_FILE contains verification_run event with exit=0 for current sid"
---

# SIAE Verification — Protocollo di Verifica Pre-Completamento
```

### siae-writing-plans
```yaml
---
name: siae-writing-plans
description: >
  Trasforma un design approvato in un piano implementativo step-by-step concreto
  e bite-sized.
  Trigger: scrivi piano implementativo, trasforma design in task, decomposizione
  step, piano bite-sized, aggiorna piano, task implementativi, docs/plans/.
---

# SIAE Writing Plans — Da Design a Piano Implementativo

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
```

### siae-executing-plans
```yaml
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
```

### siae-finishing-branch
```yaml
---
name: siae-finishing-branch
description: >
  Chiude un branch in sicurezza prima di aprire qualsiasi PR.
  Trigger: "pronto per PR", "finisco il branch", "ready to merge", "apro la PR",
  gh pr create, git push + PR, apertura pull request, branch completato,
  implementazione finita, lavoro completato su branch, pre-merge checklist.
---

# SIAE Finishing Branch — Chiusura Sicura di un Branch

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
```

### using-devforge
```yaml
---
name: using-devforge
description: >
  Stabilisce il backbone core di discovery e invocazione skill DevForge
  all'inizio di ogni conversazione.
  Trigger: inizio sessione, apertura nuovo progetto, prima interazione.
---

## SUBAGENT-STOP — Gate Check

<SUBAGENT-STOP>
Sei un subagent con un task specifico assegnato dal tuo orchestratore?

SE SI: fermati qui. Non applicare la regola dell'1%. Segui solo il prompt del
tuo orchestratore e la tua allowlist.
```

