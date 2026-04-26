---
title: Deferral — siae-dev-analytics task-scope extension to v1.49
date: 2026-04-26
status: decided
scope: anti-dilution initiative
supersedes: docs/plans/2026-04-25-anti-dilution-enforcement-design.md §"PR #3 — v1.48 Observability (SP 3/2)" deliverable "Extension siae-dev-analytics"
linked_pr: https://github.com/itsiae/siae-dev-forge/pull/217
decision_maker: lodetomasi
---

# ADR — Deferral `siae-dev-analytics` task-scope extension to v1.49

## Context

The v1.48 design doc (`docs/plans/2026-04-25-anti-dilution-enforcement-design.md`
at riga 379 / criterion riga 386) includes as a PR #3 deliverable:

> **Extension `siae-dev-analytics`** — colonna nuova `adoption_per_task`
> nel report Excel + split task-count vs session-count.

During PR #217 review, the spec-reviewer agent flagged that the deliverable
was implicitly moved to "Out of scope" in the pr-body without an explicit
scope-change decision. This ADR supplies that decision — modelled on
`docs/plans/2026-04-25-fsm-backbone-decision.md` (the FSM deferral
precedent of this initiative).

## Decision

**Deferred to v1.49.** The `siae-dev-analytics` skill does NOT receive
the `adoption_per_task` column in PR #217 (v1.48).

## Rationale

1. **Measurement-first sequencing.** The design doc argues repeatedly
   (sezioni "Obiettivo", "Criteri globali") that PR #3 is low-risk and
   that the telemetry it emits must be measured for 2 weeks before
   declaring the anti-dilution initiative closed. Building the Excel
   report surface before the 2-week measurement window would freeze
   the report schema on pre-data assumptions. Better to:
   - ship `lib/adoption-analyzer.py` + `/forge-adoption` now (read-side,
     already in PR #217),
   - collect 2 weeks of real ledger + activity data,
   - design the Excel column(s) on observed data in v1.49.

2. **Value already captured.** The three high-signal consumers of the
   adoption metric are already shipped in PR #217:
   - `/forge-adoption` command (interactive, per-user)
   - Stop-gate 3-line recap (passive, per-session)
   - Gate block explainer (contextual, per-block)
   These cover 95% of the "make adoption visible" goal. The Excel
   column is a reporting-surface nice-to-have, useful for team leads
   aggregating across 98 users, not for the individual developer the
   anti-dilution loop targets.

3. **Dependency on field labels.** PR #216 review introduced a
   **user task-scope vs team session-scope** scope mismatch that
   required explicit labeling in table/block outputs (applied as
   MAJOR #1 fix during PR #217 review). Any Excel column must carry
   the same scope disclaimer — simpler to author once with real
   column semantics informed by 2-week telemetry.

4. **Scope hygiene.** The initiative's explicit contract (design doc)
   says "3 PR, 2 settimane, ridesign se lift insufficiente". Keeping
   the extension inside v1.48 either pushes the window or lands an
   untested report. Neither is what the design asked for.

## Consequences

### Accepted

- v1.48 (PR #217) closes the initiative on the read side (analyzer +
  command + recap + explainer). The design doc's criterion
  "[ ] Dashboard dev-analytics estesa" is **not** satisfied by v1.48.
- The `siae-dev-analytics` Excel report remains on the previous schema
  for the 2 weeks of post-v1.48 measurement.
- A v1.49 follow-up is required. Minimum scope:
  - New column(s) surfacing per-user `adoption_per_task` for each of
    the 5 core skills.
  - Scope-mismatch label in the Excel header or legend (consistent with
    the `_format_table` label introduced in v1.48).
  - Aggregator test extending the PR #3 pattern.

### Not accepted

- We will **not** skip the 2-week measurement window.
- We will **not** re-open the PR #3 scope before v1.49 unless the
  2-week data forces a redesign.

## Delta vs design doc

| Design doc location | Original | After this ADR |
|---|---|---|
| §"PR #3 — v1.48 Observability" bullet 4 | "Extension siae-dev-analytics" | Deferred to v1.49 |
| Criterio accettazione riga 386 | "[ ] Dashboard dev-analytics estesa" | Superseded: criterion moved to v1.49 definition-of-done |

## Entry / exit criteria for v1.49

**Entry** (all must be true):
- v1.48 merged to `main`
- ≥ 2 weeks of telemetry in `~/.claude/.devforge-task-skills/` and
  `devforge-activity.jsonl` from ≥ 10 distinct users
- No outstanding CRITICAL from the v1.48 auto-review

**Exit** (v1.49 closes when):
- `siae-dev-analytics` Excel report contains the per-task column
- Column header documents the scope difference (task-user vs team-session)
- Aggregator test includes at least one scenario validating the column
  derivation path

## Related decisions

- `docs/plans/2026-04-25-fsm-backbone-decision.md` — FSM backbone
  deferral (same initiative, same measurement-first rationale).
