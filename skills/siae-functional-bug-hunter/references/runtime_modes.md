# Runtime modes — event → action matrix

Single source of truth for the dispatcher in
`scripts/run_lock.py` (`dispatch(mode, event) -> Action`). When this
table changes, `_DISPATCH_TABLE` in `run_lock.py` MUST be updated and
the parametrized matrix in `tests/test_run_lock_dispatch.py` MUST be
extended.

## Modes

| Mode | Default trigger | TTY behaviour | Intended use |
|---|---|---|---|
| `interactive` | TTY session, no `--mode` argument | may pause and ask the operator | exploratory analysis on a developer workstation |
| `strict` | non-TTY session, no `--mode` argument | never pauses; flags low-confidence and continues | CI, batch, scheduled jobs |
| `report-only` | explicit `--mode report-only` | never pauses; degraded confidence acceptable | first scan of an unfamiliar codebase where partial signal is better than none |

## Events

Closed enumeration of STOP triggers emitted by the pipeline phases:

| Event | Emitted by | Meaning |
|---|---|---|
| `STOP_DEPENDENCY_CLOSURE` | Phase 2 | external dependency referenced but not in `roots` |
| `STOP_FINDING_THRESHOLD` | Phase 6 | >5 critical OR >1 blocker findings retained |
| `STOP_WALLCLOCK_EXCEEDED` | any phase | `max_wallclock_minutes` exceeded |
| `STOP_DIRTY_WORKING_TREE` | Phase 0 / Phase 4 | tracked files modified during run |
| `STOP_AMBIGUOUS_SCOPE` | Phase 0 | >1 plausible interpretation of `args.roots` |

## Dispatch matrix

| Event \ Mode | interactive | strict | report-only |
|---|---|---|---|
| `STOP_DEPENDENCY_CLOSURE` | PAUSE | CONTINUE | DEGRADE |
| `STOP_FINDING_THRESHOLD`  | PAUSE | CONTINUE | CONTINUE |
| `STOP_WALLCLOCK_EXCEEDED` | PAUSE | CONTINUE | CONTINUE |
| `STOP_DIRTY_WORKING_TREE` | PAUSE | CONTINUE | CONTINUE |
| `STOP_AMBIGUOUS_SCOPE`    | PAUSE | CONTINUE | CONTINUE |

## Actions

| Action | Caller obligation |
|---|---|
| `PAUSE` | suspend the pipeline, prompt the operator, resume on input |
| `CONTINUE` | proceed to the next phase; if in `strict` mode set `confidence: low_partial` flag in `run_manifest.json` |
| `DEGRADE` | proceed but mark the report-level confidence as `degraded` and append the triggering event to `open_questions.md` |

## CLI

    python3 scripts/run_lock.py dispatch <mode> <event>

prints the action on stdout; exit 0 on valid input, 2 on unknown mode
or event.
