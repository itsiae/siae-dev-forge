# Rimozione bypass discrezionali dei quality gate — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Eliminare tutti i 9 bypass discrezionali (env var) + 2 state-file dei quality gate DevForge, introducendo un breakglass ibrido *scoped* (ADR-1 = Opzione C) attivo solo sui 5 fallimenti di tooling reali in `review-evidence`.
**Architettura:** Hook bash extensionless in `hooks/` + lib in `lib/`. Ogni gate legge una env var di skip → si rimuove il branch di bypass + il counter associato. In `review-evidence` lo skip discrezionale (env var + state-file) viene rimosso e sostituito da un breakglass dedicato che agisce solo nei path di tool-failure, mai sui verdetti di qualità.
**Stack:** Bash, test bash (`tests/hooks/*.test.sh`, `tests/run-all.sh`) e Python (`tests/*.py`).
**SP:** Umano 5 / AI-augmented 2
**Design doc:** `docs/plans/2026-06-12-remove-discretionary-skip-bypasses-design.md`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Rimuovi `SKIP_BRAINSTORMING` da brainstorming-gate | `task-01-brainstorming-gate.md` | [PENDING] |
| 2 | Rimuovi `SKIP_BLIND_REVIEW` da pr-blind-review-gate | `task-02-blind-review-gate.md` | [PENDING] |
| 3 | Rimuovi `SKIP_PREMORTEM` da pr-premortem-gate | `task-03-premortem-gate.md` | [PENDING] |
| 4 | Rimuovi `SKIP_GIT_GATE` da pre-commit | `task-04-pre-commit-git-gate.md` | [PENDING] |
| 5 | Rimuovi `SKIP_RETRO_GATE` + `FORCE_STOP` da stop-gate | `task-05-stop-gate.md` | [PENDING] |
| 6 | Rimuovi skip discrezionale da review-evidence | `task-06-review-evidence-remove.md` | [PENDING] |
| 7 | Aggiungi breakglass ibrido scoped (5 path tool-fail) | `task-07-review-evidence-breakglass.md` | [PENDING] |
| 8 | Rimuovi `SKIP_UPDATE` + timeout + `SKIP_TRAILER_HOOK` | `task-08-session-start-trailer.md` | [PENDING] |
| 9 | Pulisci `ENV_VARS.md` + nuovo test doc↔code | `task-09-env-vars-doc.md` | [PENDING] |
| 10 | Suite completa verde (verification gate) | `task-10-suite-green.md` | [PENDING] |

## Dipendenze

- Task 7 dipende da Task 6 (stesso file `hooks/review-evidence`: prima rimozione, poi aggiunta breakglass — evita conflitti).
- Task 1-5 sono indipendenti tra loro e da 6-8.
- Task 9 dipende da Task 1-8 (ENV_VARS.md riflette le rimozioni; il nuovo test grep-a il codice già ripulito).
- Task 10 dipende da TUTTI i task precedenti (è il gate finale: `tests/run-all.sh` interamente verde).

## Note trasversali (valide per ogni task hook)

- Gli hook sono file **senza estensione** in `hooks/`. Per leggerli/testarli si invoca `bash hooks/<nome>`.
- Pattern test hook: si pipe-a un envelope JSON su stdin e si asserisce l'output JSON. Vedi i test esistenti in `tests/hooks/*.test.sh` per il formato dell'envelope.
- `date -u`, `mktemp`, quoting: mantenere lo stile bash esistente del file.
- Dopo ogni rimozione: NON lasciare variabili orfane (es. `BYPASS_FILE`) né commenti che referenziano la var rimossa.
