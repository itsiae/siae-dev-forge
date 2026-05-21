# Task 07 — Add mode dispatcher to scripts/run_lock.py + smoke test

**Stato**: [PENDING] · **Effort**: 3h · **File toccati**: 3 (run_lock.py + runtime_modes.md + tests)

## Goal

Codificare in script il dispatcher dei tre runtime mode
(interactive/strict/report-only) dichiarati nello SKILL.md. Chiude il
gap A1 #3 dell'audit ("Runtime modes non dispatched").

## Acceptance

- `scripts/run_lock.py` accetta un nuovo sub-command:
  `python3 run_lock.py dispatch <mode> <event>` → stampa su stdout
  un'azione fra `PAUSE`, `CONTINUE`, `DEGRADE`. Exit 0 se mode+event
  validi, 2 se invalidi.
- Mode enum: `interactive`, `strict`, `report-only`.
- Event enum (chiuso): `STOP_DEPENDENCY_CLOSURE`,
  `STOP_FINDING_THRESHOLD`, `STOP_WALLCLOCK_EXCEEDED`,
  `STOP_DIRTY_WORKING_TREE`, `STOP_AMBIGUOUS_SCOPE`.
- Matrix di dispatch documentata in
  `references/runtime_modes.md` (≤30 righe, tabella `event × mode → action`).
- `scripts/preflight.sh` invariato (caller può ora invocare
  `run_lock.py dispatch` per scoprire l'azione).
- Smoke test: 3 invocazioni (1 per mode), exit code 0, output corretto.

## Implementation

1. **Test first (TDD)**: scrivere
   `tests/run_lock/test_mode_dispatcher.py` con test parametrizzati su
   matrix 3×5 = 15 (mode × event) + 2 negative test (invalid mode,
   invalid event).
2. Tests fail (sub-command `dispatch` non esistente).
3. Implementare in `run_lock.py`:
   - Funzione `dispatch(mode, event) -> Action`
   - Dispatch table inline costante
   - Sub-command parser via argparse subparsers
4. Refactor: estrarre la dispatch table in
   `references/runtime_modes.md` come single source of truth e nel
   codice tenerla allineata via commento dichiarativo.
5. Verifica smoke test.

## Matrix di dispatch (target)

| Event \ Mode | interactive | strict | report-only |
|---|---|---|---|
| `STOP_DEPENDENCY_CLOSURE` | PAUSE | CONTINUE | DEGRADE |
| `STOP_FINDING_THRESHOLD` | PAUSE | CONTINUE | CONTINUE |
| `STOP_WALLCLOCK_EXCEEDED` | PAUSE | CONTINUE | CONTINUE |
| `STOP_DIRTY_WORKING_TREE` | PAUSE | CONTINUE | CONTINUE |
| `STOP_AMBIGUOUS_SCOPE` | PAUSE | CONTINUE | CONTINUE |

(`CONTINUE` in strict comporta `flag low-confidence` nel run_manifest;
`DEGRADE` in report-only comporta `mark + log`; gestione lato caller.)
