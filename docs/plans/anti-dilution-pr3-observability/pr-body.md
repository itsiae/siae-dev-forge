## Summary

PR #3 di 3 dell'initiative **Anti-Dilution Enforcement** (design:
[`docs/plans/2026-04-25-anti-dilution-enforcement-design.md`](docs/plans/2026-04-25-anti-dilution-enforcement-design.md),
ADR-009 "Observability Loop"). Base: `feat/anti-dilution-pr2-task-scope`
(PR [#216](https://github.com/itsiae/siae-dev-forge/pull/216)).

PR #1 ha ridotto il noise di iniezione (-99.6%). PR #2 ha cablato il
task-scope enforcement (148 test PASS, 2 CRITICAL + 5 MAJOR review fixati).
PR #3 **rende visibile agli utenti** l'adoption per-task e trasforma i
block message da ceremoniali a informativi.

## Changes

### `lib/adoption-analyzer.py` (NEW — 180 righe, 8 test)

Legge il ledger `~/.claude/.devforge-task-skills/<task_id>/skills_validated`
(PR #2) e aggrega `~/.claude/devforge-activity.jsonl`. Calcola:

- **User adoption** per le 5 skill core (task-scope quando ledger è
  popolato, session-scope come fallback)
- **Team median** session-scope (mediana delle adoption per-utente nella
  finestra)
- **Delta** in punti percentuali

Output modes: `json` / `table` / `recap` (3-line per stop-gate) / `block`
(singolo skill per block explainer).

### `commands/forge-adoption.md` (NEW)

Slash command `/forge-adoption` che invoca l'analyzer in formato tabella
markdown. Zero side effect, zero network call.

### `hooks/stop-gate` — 3-line recap (ADR-009)

A fine sessione (dopo `session_end` emit) stampa a stderr 3 righe:
numero task tracked, skill più debole vs team median, nudge per la
prossima sessione. Opt-out via `DEVFORGE_DISABLE_RECAP=1`.

### `lib/block-explainer.sh` + 5 gate block messages (ADR-009)

Helper bash che invoca l'analyzer in format `block` per ottenere una
riga tipo "La tua adoption `siae-tdd`: 42% · team median: 78%". Cache
24h per evitare fork-bomb Python ad ogni block. Wire'd in:

- `tdd-gate`
- `brainstorming-gate` (warn + hard block)
- `pre-commit` (git-workflow check)
- `stop-gate` (verification check)
- `pr-blind-review-gate`

Opt-out globale: `DEVFORGE_DISABLE_EXPLAINER=1`.

### Test

- `tests/lib/test_adoption_analyzer.py` — 8 test (TDD RED-GREEN completo)
- `tests/pr3-observability/run-all.sh` — aggregator che combina suite
  PR #3 + suite PR #2 regression

Risultati:
- **PR #3 test suite**: 8/8 PASS
- **PR #2 regression**: 148/148 PASS (invariato)
- **Baseline**: 161/6/1 (Δ=0)

## Env vars introdotte

| Env var | Default | Scopo |
|---|---|---|
| `DEVFORGE_DISABLE_RECAP` | 0 | Disabilita recap stop-gate (non-interactive CI) |
| `DEVFORGE_DISABLE_EXPLAINER` | 0 | Disabilita block explainer (CI headless / privacy) |

## Acceptance criteria

- [x] `/forge-adoption` emette tabella adoption per le 5 skill core
- [x] Recap stop-gate 3 righe visibile (stderr, non blocca)
- [x] Block messages su tdd/brainstorming/pre-commit/stop/pr-blind-review
      contengono numero personale + team median
- [x] ≥30 test aggregator PASS (8 PR #3 + 148 PR #2 = 156)
- [x] Baseline PR #2 invariato (148 + 161 Δ=0)

## Out of scope

- **Extension `siae-dev-analytics` Excel**: documentazione aggiornata
  del formato output, implementazione column esteso deferred a v1.49.
- **FSM backbone**: deferred in `docs/plans/2026-04-25-fsm-backbone-decision.md`.
- **Maturity levels W0-W3**: rejected dal design doc principale.

## Rollback

Per-gate: `DEVFORGE_DISABLE_EXPLAINER=1` / `DEVFORGE_DISABLE_RECAP=1`.
Globale: `git revert <merge commit>` + revert PR #216 se necessario.

## Cosa chiude questa PR

L'initiative anti-dilution è completa:

| PR | Versione | Effetto misurato |
|---|---|---|
| #215 | v1.46 | SKILL.md -62%, injection -99.6%, wolf-cry -100% |
| #216 | v1.47 | Task-scoped enforcement, 8 gate migrati, 39→20 prereq-map autogen, 4 nuovi gate |
| #217 | v1.48 | Adoption visibility loop, block explainer, recap sessione |

**Next step**: 2 settimane di telemetria post-merge. Se adoption per-task
tocca i target (≥80% tdd/brainstorming, ≥60% verification, ≥40% blind-review),
l'initiative è chiusa. Altrimenti ridesigniamo con maturity levels o
personalization (rejected al T0 ma riapribili con dati).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
