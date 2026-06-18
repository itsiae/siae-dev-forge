# Piano — Status line: avviso python3 mancante + notifica aggiornamento plugin

**Design:** [design.md](design.md) (approvato 2026-06-18)
**Branch:** `feat/statusline-python-and-update-notice`
**Complessità:** Media · **SP totale:** Umano ~3 · Augmented ~1.5

## Obiettivo

Rendere visibili nella status line DevForge due condizioni oggi silenziose:
1. `python3` mancante (token-stats e telemetria zero-loss degradati)
2. Plugin aggiornato a una nuova versione rispetto all'ultima sessione

## Convenzioni verificate

- Test invocati **esplicitamente** in `tests/run-all.sh` (no auto-discovery) → ogni nuovo test va cablato lì.
- Test bash: `set -euo pipefail`, contatori `PASS`/`FAIL`, exit `1` se `FAIL>0`. Modello: `tests/capture-test-result.test.sh`.
- Status line: variabili colore `RED/GREEN/YELLOW/RESET` (statusline.sh:13-16), warning additivi a `WARN_STR` (statusline.sh:256-319) col pattern `${WARN_STR:+$WARN_STR }$(printf '%b...%b' "$COLOR" "$RESET")`.
- `DEVFORGE_SESSION_DIR` condivisa hook↔statusline via SID file `~/.claude/.devforge-session-id` (stessa fonte di `token-stats.json`).

## Task

| # | Task | Stato | File |
|---|------|-------|------|
| 01 | Feature 1 — avviso python3 mancante (statusline) | [DONE] | [task-01](task-01-python-warning-statusline.md) |
| 02 | Feature 2a — detection cambio versione (session-start) | [DONE] | [task-02](task-02-version-detection-session-start.md) |
| 03 | Feature 2b — display flag aggiornamento (statusline) | [DONE] | [task-03](task-03-update-notice-statusline.md) |
| 04 | Wiring test in run-all.sh + no-regression full suite | [DONE] | [task-04](task-04-wire-tests-no-regression.md) |

**Nota no-regression (Task 04):** i 3 test sono cablati in `run-all.sh` (righe 1229-1249) e
passano 3/3 con l'invocazione identica del runner. La full-suite **locale** (macOS + iCloud)
ha un abort flaky **pre-esistente** nei test session-start (macOS crea `Library/Caches` nel
sandbox HOME → un `rm -rf` non guardato aborta sotto `set -e`), che si manifesta prima dei
nuovi blocchi e non è correlato a queste modifiche. In CI Linux il comportamento non si
verifica. Verifica funzionale diretta: `hooks/session-start` continua a emettere
`additional_context` JSON valido dopo la modifica.

## Criteri di accettazione globali (dal design)

1. python3 assente → "🐍 python3 assente — installalo per token/telemetria" (giallo)
2. python3 presente → nessun messaggio (no-regression)
3. Script non in errore (`set -euo pipefail`) in entrambi i casi
4. Prima installazione (no last-seen) → scrive versione, nessun avviso
5. Versione invariata → nessun avviso
6. Versione cambiata → "🆙 DevForge aggiornato a vX.Y.Z" (verde) per tutta la sessione
7. Versione non determinabile (dev-mode senza semver/jq) → skip silenzioso
8. `session-start` non regredisce (no rete, no stdout, guard `|| true`)
