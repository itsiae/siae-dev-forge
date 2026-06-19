# Fix lifecycle stop-gate / session_end — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: usa `siae-subagent-development` (stessa sessione)
> o `siae-executing-plans` (sessione separata) per implementare task per task in TDD.

**Goal:** Lo `Stop` per-turno smette di cancellare lo stato di sessione (sblocca il git
gate) e `session_end` viene emesso a fine-sessione reale via un nuovo hook `SessionEnd`
con conteggi accurati.

**Architettura:** Separazione responsabilità lifecycle — `Stop` = solo gate bloccanti;
`SessionEnd` (nuovo) = emette `session_end` senza toccare lo stato; `SessionStart` =
unico owner del reset/preserve. Nessuna dipendenza dall'ordine di esecuzione hook.

**Stack:** Bash hooks (siae-dev-forge plugin) + JSONL telemetry + test bash.

**SP:** Umano 5 · Augmented 2

**Design doc:** `docs/plans/2026-06-19-stop-gate-session-lifecycle-fix-design.md` (status: approved)

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Nuovo hook `hooks/session-end` (emit senza rm) | `task-01-session-end-hook.md` | [PENDING] |
| 2 | Registra `SessionEnd` in hooks.json + fix contatori test | `task-02-register-hook-counters.md` | [PENDING] |
| 3 | Strip `hooks/stop-gate` (rimuovi rm + emit, solo gate) | `task-03-stop-gate-strip.md` | [PENDING] |

## Dipendenze

- Task 1 è standalone (nuovo file, non ancora registrato → zero impatto sul runtime).
- Task 2 dipende da Task 1 (registra il hook creato in Task 1).
- Task 3 è indipendente da 1-2 a livello di codice, ma va **dopo** Task 2 nell'ordine di
  commit così che `SessionEnd` sia già attivo quando `Stop` smette di emettere
  `session_end` (evita una finestra senza alcun emit).

## Mappa AC → Task (10 AC del design)

| AC | Descrizione | Task |
|----|-------------|------|
| AC-1 | session-skills NON cancellato dopo Stop no-completion | 3 |
| AC-2 | session-commits/start-ns NON cancellati (stdin vuoto) | 3 |
| AC-3 | completion+no-verification → block (no-regression) | 3 |
| AC-4 | completion+verification → allow (no-regression) | 3 |
| AC-5 | SessionEnd emette session_end con conteggi corretti | 1 |
| AC-6 | idempotenza: seconda invocazione → no doppio emit | 1 |
| AC-7 | SessionEnd NON fa rm dei file di stato | 1 |
| AC-8 | conteggi accumulati (non parziali) | 1 |
| AC-9 | hooks.json valido + contatori hardcoded aggiornati | 2 |
| AC-10 | reason=resume → file di stato presenti dopo SessionEnd | 1 |
