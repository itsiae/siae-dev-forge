---
name: siae-debugging
description: >
  Use when investigating a bug, errore, incident, test che fallisce, comportamento
  inatteso, eccezione, stacktrace, crash, build failure, 500, timeout,
  NullPointerException, TypeError, "non funziona", "rotto", "fallisce", "non va"
  — prima di proporre qualsiasi fix. Forza root cause analysis a 4 fasi
  (reproduce → pattern → hypothesize → fix) con HARD-GATE su Fase 1.
validates_via:
  predicate: root_cause_identified
  evidence_type: log_event
  evidence_check: "DEVFORGE_LOG_FILE contains debugging_root_cause event with hypothesis_validated=true for current task_id"
---

# SIAE Debugging Sistematico

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨  DevForge  ·  SIAE Debugging Sistematico         ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 6. QA Gate

---

## Panoramica

I fix casuali sprecano tempo e creano nuovi bug. Le patch rapide mascherano problemi profondi.

**Principio fondamentale:** SEMPRE trovare la root cause prima di tentare fix. Risolvere i sintomi e' fallimento.

**Violare la lettera di questo processo significa violare lo spirito del debugging.**

---

## LA LEGGE DI FERRO

```
NESSUN FIX SENZA ROOT CAUSE INVESTIGATION COMPLETATA (FASE 1)
```

<EXTREMELY-IMPORTANT>
Stai per proporre un fix, scrivere una patch, o suggerire una soluzione?
Hai completato la Fase 1 (Root Cause Investigation)?
- NO → FERMATI. Nessun fix senza root cause. Torna alla Fase 1.
- SI → Procedi con la Fase 2 (Pattern Analysis).

Stai pensando "so gia' cos'e'", "e' un fix veloce", "aggiungo un try-catch"?
Stai razionalizzando. Il 95% dei "so gia' cos'e'" si rivela sbagliato.

Conseguenze documentate dello skip:
- Ogni "quick fix" senza root cause ha richiesto in media 2 ulteriori fix
- Il guess-and-check richiede 2-3 ore di thrashing vs 15-30 min del metodo sistematico
- I fix senza root cause hanno un first-time fix rate del 40% vs 90% del metodo sistematico
</EXTREMELY-IMPORTANT>

Se non hai completato la Fase 1, **non puoi proporre fix**. Punto.

---

> 📊 **Dai repo itsiae:** Il tempo medio di risoluzione bug scende da 4.2h a 1.8h quando si segue un protocollo strutturato vs fix diretto.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

## Quando Usare

Usa per QUALSIASI problema tecnico: bug (produzione/collaudo/sviluppo), test che falliscono, comportamento inatteso, performance, build failure, errori di integrazione, incident.

**Usa SOPRATTUTTO quando:** sei sotto pressione di tempo, "un fix veloce" sembra ovvio, hai gia' tentato piu' di un fix, il fix precedente non ha funzionato, non capisci completamente il problema.

---

## 4 Fasi RCA (summary — dettaglio in `reference/debugging-phases.md`)

1. **Fase 1 — Root Cause Investigation (HARD-GATE)**: leggi errori, riproduci deterministicamente, controlla cambi recenti, traccia all'indietro, raccogli evidenze multi-componente. → `reference/debugging-phases.md#fase-1-root-cause-investigation-hard-gate`
2. **Fase 2 — Pattern Analysis**: bug isolato o sistemico? Cerca pattern simili nel repo, confronta con riferimenti funzionanti, mappa dipendenze. → `reference/debugging-phases.md#fase-2-pattern-analysis`
3. **Fase 3 — Hypothesis Testing**: formula ipotesi concrete scritte, testa UNA alla volta col cambiamento minimo, documenta ogni risultato. → `reference/debugging-phases.md#fase-3-hypothesis-testing`
4. **Fase 4 — Implementation**: test di regressione PRIMA del fix (TDD), fix minimale (YAGNI), verifica, commit con riferimento ticket. → `reference/debugging-phases.md#fase-4-implementation`

Checkpoint format obbligatorio per ogni transizione: `[DEBUG:PHASE-N] <esito sintetico> → next: PHASE-N+1`.

---

## Regola dei 3 Tentativi

```
Se 3+ fix falliscono → STOP. Metti in discussione l'architettura.
```

**Pattern che indicano un problema architetturale:**
- Ogni fix rivela nuovo stato condiviso / coupling / problema in un punto diverso
- I fix richiedono "refactoring massiccio" per essere implementati
- Ogni fix crea nuovi sintomi altrove

**Quando scatta la regola:**
1. FERMA tutto
2. Non tentare il Fix #4 senza discussione architetturale
3. Metti in discussione i fondamentali (pattern solido? inerzia? ristrutturare?)
4. Discuti con il team prima di procedere

Questo NON e' un'ipotesi fallita — e' un'architettura sbagliata.

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi max per step | 2 | Fermati. Chiedi all'utente prima di riprovare. |
| Step totali del processo di debug | 7 | Bug piu' profondo. Escalation necessaria. |
| Output max per analisi | 300 righe | Sintetizza. L'utente non legge wall-of-text. |

---

REQUIRED SUB-SKILL: siae-tdd

Dopo aver identificato il fix, implementalo seguendo `siae-tdd` (test fallente prima del fix).

---

## Anti-Razionalizzazione

Se ti senti pensare "so gia' cos'e'", "e' un fix veloce", "aggiungo un try-catch", "riavvio e vedo", "fix multipli insieme", "non c'e' tempo per il processo": stai razionalizzando.
Tabella completa con realta' di confronto in `reference/debugging-anti-rationalization.md`.

---

## Integration Observability

Per pattern di filtro log, integrazione con scan statici (Qodana), error tracking frontend (Google Analytics) e collegamento ticket JIRA: `reference/debugging-cloudwatch.md` (esempio AWS CloudWatch SIAE + generalizzazione a qualsiasi stack).

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura messaggi di errore / log | 🟢 Sicuro | No |
| Ricerca pattern nel repo | 🟢 Sicuro | No |
| `git log`, `git diff` | 🟢 Sicuro | No |
| Formula e test ipotesi (Fase 3) | 🟢 Sicuro | No |
| Implementazione fix (Fase 4) | 🟡 Medio | Si |
| Commit fix | 🟡 Medio | No (commit locale) |

---

## Vincoli Non Negoziabili

1. **Nessun fix senza root cause** — La Fase 1 e' un HARD-GATE
2. **Nessun try-catch "preventivo"** — Mascherare errori non e' risolvere
3. **Nessun revert senza capire perche'** — Il revert senza comprensione ricreera' il problema
4. **Nessun fix multiplo in un singolo commit** — Isola i cambiamenti
5. **Nessun "funziona sul mio PC"** — Se non funziona in un ambiente, c'e' un problema

---

## Tecniche di Supporto

- **[defense-in-depth.md](defense-in-depth.md)** — Pattern a 4 layer per validare il fix (Entry Point, Business Logic, Environment Guards, Debug Instrumentation). Da applicare quando un bug riappare dopo il fix o quando opera su sistemi critici.
- **[find-polluter.sh](find-polluter.sh)** — Script per test bisection. Identifica quale test causa "pollution". Uso: `./skills/siae-debugging/find-polluter.sh '<pattern>' '<glob>'`.
- **Template RCA** — Per incident significativi (P1/P2): `skills/siae-debugging/template/rca-template.md`.

---

## Permission Denied Handling

**Fase 1-3 (investigazione):** `Read`/`Grep` permission-free; `git log`/`git diff` e AWS CLI richiedono Bash — se negato, fornisci comandi e chiedi output.
**Fase 4 (fix):** Edit/Write se negato → degrada come siae-tdd (codice in blocco fenced + path); Bash test → fornisci comando e chiedi all'utente di eseguire.

Se i permessi sono negati: completa investigazione con tool nativi, presenta i comandi che l'utente deve eseguire, attendi output, NON entrare in loop di retry, NON dichiarare completamento per fasi non eseguite.

---

## Impatto Reale

| Approccio | Tempo medio a fix | First-time fix rate | Bug reintrodotti |
|-----------|-------------------|---------------------|-----------------|
| **Sistematico** (questa skill) | 15-30 min | ~90% | Quasi zero |
| **Guess-and-check** | 2-3 ore di thrashing | ~40% | Frequente |

Da 24 sessioni documentate: ogni "quick fix" senza root cause ha richiesto in media 2 ulteriori fix; il 95% dei "no root cause found" era investigazione incompleta; gli incident P1 risolti con metodo sistematico non si sono ripresentati.

**La razionalizzazione piu' costosa:** *"E' urgente, non ho tempo per il processo"*. Il debug sistematico e' piu' veloce del thrashing. Sempre.

---

## Quick Reference

| Fase | Attivita' Chiave | Criterio di Successo |
|------|------------------|----------------------|
| **1. Root Cause** (HARD-GATE) | Leggi errori, riproduci, traccia, raccogli evidenze | Capisci COSA e PERCHE' |
| **2. Pattern** | Cerca pattern, confronta, analizza dipendenze | Identifichi differenze |
| **3. Hypothesis** | Formula ipotesi, testa minimamente, documenta | Confermata o nuova ipotesi |
| **4. Implementation** | Test TDD, fix minimale, verifica, commit | Bug risolto, test passano |
