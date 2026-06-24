# SIAE Global Rules Injection — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development` (stessa sessione)
> oppure `siae-executing-plans` (sessione separata) per implementare task per task.

**Goal:** rendere le "SIAE Global Rules" una fonte unica versionata, iniettata da session-start in ogni sessione (distribuzione team-wide).
**Architettura:** un solo file markdown versionato (`skills/using-devforge/reference/siae-global-rules.md`) letto live da `hooks/session-start` e iniettato nel blocco `<EXTREMELY_IMPORTANT>` (riga 305) come nuova sezione, mirror del read di `using-devforge/SKILL.md`. Allineamento per costruzione (fonte unica) + test di guardia che fallisce se il link si rompe.
**Stack:** bash (hook), markdown (regole), bash test, JSON (version manifest).
**SP:** Umano 3 / Augmented 1
**Design doc:** `docs/plans/2026-06-24-siae-global-rules-injection-design.md`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Crea la fonte unica versionata delle regole | `task-01-create-rules-file.md` | [PENDING] |
| 2 | TDD: test + wiring iniezione in session-start | `task-02-wire-session-start.md` | [PENDING] |
| 3 | Bump versione plugin + CHANGELOG | `task-03-version-bump.md` | [PENDING] |
| 4 | Gate finale: verifica aderenza e allineamento | `task-04-verify-adherence-alignment.md` | [PENDING] |

## Dipendenze

- Task 2 dipende da Task 1 (il test funzionale `(B)` asserisce un sentinel del file regole; il fail-safe `(C)` rinomina quel file).
- Task 3 dipende da Task 1+2 (bump solo dopo che il comportamento è completo e testato).
- Task 4 dipende da Task 1+2+3 (gate finale: chiude il goal utente *"verifica aderenza e allineamento"*).

## Precondizioni (branch hygiene — risolvere PRIMA di Task 1)

`hooks/session-start` è già modificato sul branch corrente `feat/integrity-gate-fail-closed`
per la feature integrity-gate (+ untracked `hooks/integrity-gate`, `lib/integrity-state.sh`,
`tests/...`). **Non impilare questa feature qui.** Prima di eseguire:
1. Committare/stashare il lavoro integrity-gate sul suo branch, poi
2. creare branch dedicato da `main` via `siae-git-workflow` (es. `feat/siae-global-rules-injection`),
3. eseguire i task su quel branch pulito.
Riferimento memoria: [[feedback_branch_hop_during_push]], [[feedback_concurrent_sessions_branch_hop]].
