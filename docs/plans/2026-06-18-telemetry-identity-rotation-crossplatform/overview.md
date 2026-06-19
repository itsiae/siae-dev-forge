# Piano — Telemetria & Identità cross-platform (parità Windows ≡ macOS ≡ Linux)

**Design:** `docs/plans/2026-06-18-telemetry-identity-rotation-crossplatform-design.md` (APPROVATO)
**Data:** 2026-06-18
**Branch:** da creare via siae-git-workflow (es. `feat/telemetry-identity-rotation-crossplatform`)

## Obiettivo

Eliminare le 2 degradazioni cross-platform trovate in verifica (rotazione python3-only;
`event_id` collidibile senza `flock`) e arricchire l'identità developer con 6 segnali locali per
attribuire al 100% anche col caso "1 profilo GitHub + N PAT". Requisito hard: **parità stretta
Windows ≡ macOS ≡ Linux**, zero-loss, additivo, no-regression.

## Invarianti (valgono per OGNI task)

- Nessun `set -e` abort: ogni ramo best-effort termina con `|| true` o guard.
- Additivo: mai rimuovere campi/funzioni esistenti.
- Parità: nessun comportamento solo-mac o solo-Windows; metodo per-OS dietro guard `uname`/`command -v`.
- No-regression: `tests/zero-loss/unit/*` + `tests/test_telemetry_fixes.sh` +
  `tests/test_telemetry_flush_storm.sh` devono restare verdi a fine di ogni task.
- TDD: ogni task scrive prima il test che fallisce (RED), poi l'implementazione (GREEN), poi refactor.

## Indice task

| Task | Capability | Descrizione | Stato |
|------|-----------|-------------|-------|
| [task-01](task-01-event-id-collision-resistant.md) | D | `event_id` collision-resistant via mkdir-lock in `devforge_next_seq` | [DONE] |
| [task-02](task-02-identity-os-signals.md) | A | `os_full_name`/`os_login`/`os_domain` cross-platform | [DONE] |
| [task-03](task-03-identity-ssh-npm-gh.md) | A | `ssh_fingerprint`/`npm_email`/`gh_email` (opt-in) | [DONE] |
| [task-04](task-04-identity-bundle-wire.md) | A | Wire dei 6 campi in `devforge_identity_bundle` | [DONE] |
| [task-05](task-05-rotate-inline-helper.md) | B | `_devforge_rotate_inline` (rename + collisione + stat) | [PENDING] |
| [task-06](task-06-lock-append-rotation-routing.md) | B | Firma 4-arg `_devforge_lock_append` + cursor-move + routing | [PENDING] |
| [task-07](task-07-batch-global-archives.md) | B | Drain archivi globali in `devforge_batch_global` | [PENDING] |
| [task-08](task-08-crlf-guard.md) | C | CRLF guard su tutte le letture cursore | [PENDING] |
| [task-09](task-09-no-regression-crossplatform-verify.md) | tutte | Harness verifica cross-platform committato + no-regression | [PENDING] |

## Ordine e dipendenze

- task-01 indipendente (foundational).
- task-02 → task-03 → task-04 (sequenziali, stessa funzione).
- task-05 → task-06 → task-07 (sequenziali, rotazione).
- task-08 trasversale (dopo task-06/07 che toccano i cursori).
- task-09 ultimo (gate finale).

## Criteri di accettazione globali

Vedi AC1-AC11 nel design doc §7. Ogni task mappa a uno o più AC (indicati nel task file).
