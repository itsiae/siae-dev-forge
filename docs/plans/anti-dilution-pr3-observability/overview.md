---
title: PR #3 — Anti-Dilution Observability Loop
date: 2026-04-26
status: in_progress
branch: feat/anti-dilution-pr3-observability
base: feat/anti-dilution-pr2-task-scope
design_doc: docs/plans/2026-04-25-anti-dilution-enforcement-design.md
pr1_ref: https://github.com/itsiae/siae-dev-forge/pull/215
pr2_ref: https://github.com/itsiae/siae-dev-forge/pull/216
---

# PR #3 — Observability Loop (v1.48 ADR-009)

Terzo e ultimo stadio dell'initiative anti-dilution. PR #1 ha ridotto
l'injection noise. PR #2 ha cablato il task-scope enforcement. PR #3 lo
**rende visibile agli utenti** — adoption rate + block explainer + recap
sessione.

## Razionale

Il design doc (sezione "PR #3 — v1.48 Observability") separa
deliberatamente l'observability dall'enforcement per poter misurare PR
#2 prima di aggiungere dashboard. Con PR #2 mergiato (137 → 148 PASS,
tutti i CRITICAL review fixati), ora serve il loop visibile.

## Scope

7 deliverable:

1. `lib/adoption-analyzer.py` — legge ledger task-skills + activity.jsonl,
   calcola per-user + per-team adoption per-skill per-task (7d/30d).
2. `commands/forge-adoption.md` — slash command `/forge-adoption`.
3. Stop-gate 3-line recap a fine sessione (N task, skill X/Y, next nudge).
4. Gate block explainer: i messaggi di block mostrano la tua adoption
   personale + team median ("La tua adoption siae-tdd: 42%, team 78%").
5. Extension `siae-dev-analytics` — colonna nuova `adoption_per_task`
   nel report Excel.
6. Test suite + aggregator `tests/pr3-observability/run-all.sh`.
7. README + `plugin.json` v1.48.0 + PR open.

## Out of scope

- FSM backbone (deferred in `docs/plans/2026-04-25-fsm-backbone-decision.md`).
- Maturity levels W0-W3 (rejected dal design doc principale).
- Nuovi gate — osservabilità non introduce enforcement.

## Criteri accettazione

- [ ] `/forge-adoption` emette tabella adoption per le 5 skill core
- [ ] Recap stop-gate 3 righe visibile a fine sessione reale
- [ ] Block messages su tdd/brainstorming/pre-commit/stop/pr-blind-review
      contengono numero personale + team median
- [ ] Extension dev-analytics produce colonna nuova senza rompere export
- [ ] ≥30 test aggregator PASS
- [ ] Baseline PR #2 invariato (148 + 161 Δ=0)

## Task list

Vedi `task-XX-*.md` per dettaglio:

1. [Task 1 — adoption-analyzer](task-01-adoption-analyzer.md)
2. [Task 2 — /forge-adoption command](task-02-forge-adoption-command.md)
3. [Task 3 — stop-gate recap](task-03-stop-gate-recap.md)
4. [Task 4 — block explainer dati personali](task-04-block-explainer.md)
5. [Task 5 — dev-analytics extension](task-05-dev-analytics-extension.md)
6. [Task 6 — test suite + aggregator](task-06-test-suite.md)
7. [Task 7 — release v1.48 + PR open](task-07-release.md)
