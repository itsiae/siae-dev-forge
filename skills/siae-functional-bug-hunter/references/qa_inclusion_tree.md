# QA inclusion decision tree

This file is the single source of truth for the question: **is this
hypothesis something a manual QA tester (ISTQB Foundation + 2 years
experience) could reasonably surface?**

A finding that fails any node of the tree below is NOT emitted in
`qa_report.md`. It is recorded in `hypotheses.json` with the verdict
reason naming the failing node.

**Inter-rater agreement target**: Cohen's κ ≥ 0.7 between two
independent reviewers labelling the golden set. The same calibration
loop documented in `severity_rubric.md` applies here.

## Reference persona

The skill assumes the following QA tester profile when judging
inclusion:

- **Certification**: ISTQB Foundation (CTFL) baseline.
- **Experience**: 2 years on web / mobile / API products, exposure to
  basic API testing tools (Postman, curl), basic SQL, basic
  observability (CloudWatch / Datadog / similar).
- **NOT assumed**: code reading skills, ability to debug with breakpoints,
  ability to write automation, deep AWS knowledge, deep cryptography
  knowledge.
- **Tools available**: a browser / device, Postman or equivalent, read
  access to logs and dashboards, NO source-code read access.

A hypothesis is "QA-reasonable" iff this persona could reproduce it
following a written test case in under one hour of focused work.

## The 4-node decision tree

The tree is traversed top-down. At each node, "yes" continues down the
tree; "no" rejects the hypothesis with the node id as the rejection
reason.

```
                  ┌──────────────────────────────────────────────────┐
                  │ N1: OBSERVABILITY                                 │
                  │ Can the QA observe the buggy outcome              │
                  │ through one of the 8 actor primitives             │
                  │ defined in repro_voice_guide.md, without          │
                  │ source-code reading?                              │
                  └────────────┬─────────────────────────────────────┘
                              yes
                               │
                  ┌────────────▼─────────────────────────────────────┐
                  │ N2: TRIGGERABILITY                                │
                  │ Can the QA *cause* the buggy outcome              │
                  │ from outside the system, by performing a finite   │
                  │ sequence (≤ 12 steps) using the 8 actor           │
                  │ primitives, without writing code?                 │
                  └────────────┬─────────────────────────────────────┘
                              yes
                               │
                  ┌────────────▼─────────────────────────────────────┐
                  │ N3: REPRODUCIBILITY                               │
                  │ Does the reproduction recipe meet the             │
                  │ minimally-flaky threshold (≥ 80% race / ≥ 95%     │
                  │ non-race)?                                        │
                  └────────────┬─────────────────────────────────────┘
                              yes
                               │
                  ┌────────────▼─────────────────────────────────────┐
                  │ N4: RELEVANCE                                     │
                  │ Is the impact functionally observable             │
                  │ (changes what the user sees, persists, or         │
                  │ receives) — i.e. NOT just an internal             │
                  │ refactor opportunity, NOT performance-only,       │
                  │ NOT pure security without functional              │
                  │ manifestation?                                    │
                  └────────────┬─────────────────────────────────────┘
                              yes
                               │
                               ▼
                       INCLUDED in qa_report.md
```

If any node returns "no", the hypothesis is excluded and recorded as
`{ verdict: "rejected", reason: "N<n>", node: "<node title>" }` in
`hypotheses.json`.

## Node N1 — Observability

A QA can observe the outcome through one of:

- a UI state visible on screen (`ui-user` observation),
- an HTTP / gRPC / GraphQL response body or status code (`api-caller`
  observation),
- a message visible on a queue / topic / bus they have read access to
  (`event-publisher` followed by `observer`),
- a database row content they have read access to (`observer` on a
  `db-operator` query),
- a log entry / metric / dashboard tile they have read access to
  (`observer`).

Internal stack traces, JVM heap state, off-CPU profiling data, kernel
audit logs are NOT QA-observable.

## Node N2 — Triggerability

A QA can trigger the path using only the 8 actor primitives. Examples
of NON-triggerable scenarios:

- A race window that requires injecting a `sleep()` inside the code
  under test → not triggerable.
- A bug that requires modifying the application's bytecode at runtime
  → not triggerable.
- A bug that requires DDoS-scale concurrent traffic to manifest → not
  triggerable in a one-hour QA session (note this is a different
  exclusion from "performance audit out of scope").
- A bug reachable only via direct memory editing → not triggerable.

A bug that requires concurrent requests is **triggerable** as long as
the QA can issue them with standard tools (Postman runner, curl in a
loop, two browser windows).

## Node N3 — Reproducibility

The threshold is the minimally-flaky threshold from
`<terminology>/minimally_flaky`:

- For BP-003 (state-race-window) and BP-011 (concurrent-mutation):
  ≥ 80% over 5 attempts.
- For all other patterns: ≥ 95% over 5 attempts.

A hypothesis whose reproduction rate is below threshold is NOT included.
Instead, it is recorded in `open_questions.md` with a note: "Bug pattern
plausible but reproduction unreliable; suggest instrumentation."

## Node N4 — Relevance

A bug is "relevant" iff its functional manifestation is **directly
observable by the QA** as a deviation from the documented expected
behaviour. Exclusions:

- "The code could be cleaner" / "this is a code smell" → not relevant.
- "This is slow" without an SLA breach → not relevant (performance
  audits are out of scope; see `SKILL.md` "When NOT to use").
- "This is insecure" without a functional manifestation a QA can see
  → not relevant (security-only findings are out of scope; see the
  functional manifestation test in `bug_patterns.md` BP-002).
- "This emits a warning log" without user-visible effect → not relevant.

The functional manifestation test:

> **There exists an actor A from the 8 primitives and an observable
> user journey J such that A performs J and the bug changes the
> observable outcome of J.**

Boolean. True → relevant. False → excluded.

## Worked examples

### Example A — INCLUDED

- Hypothesis: BP-007 off-by-one-pagination on `GET /v1/orders`.
- N1: yes (response body lists rows; QA can compare across pages).
- N2: yes (call API with `offset=0` then `offset=20`).
- N3: yes (≥ 95% — deterministic).
- N4: yes (user sees missing or duplicated orders).
- Result: **included**.

### Example B — REJECTED at N1

- Hypothesis: a JVM `ExecutorService` is not shut down properly on
  application exit, leaking threads.
- N1: no — internal state, not visible to the QA.
- Result: **rejected (N1)**. Moved to `open_questions.md` with note:
  "Investigate during a JVM-profiling session."

### Example C — REJECTED at N2

- Hypothesis: a race window only triggers when two threads call a
  private method with specific timing.
- N1: yes (the outcome is a duplicate row).
- N2: no — the private method is not callable from outside; the only
  trigger is two simultaneous API calls but the race window is < 1 ms
  and requires server-side cooperation.
- Result: **rejected (N2)**. Moved to `open_questions.md`.

### Example D — REJECTED at N3

- Hypothesis: a memory-pressure-triggered cache eviction returns stale
  data.
- N1: yes (stale data visible).
- N2: yes (QA can fill the cache to threshold).
- N3: no — reproduction rate observed at 30% even with maximum effort.
- Result: **rejected (N3)**. Moved to `open_questions.md` with note:
  "Add deterministic eviction hook for testability."

### Example E — REJECTED at N4

- Hypothesis: a redundant database round-trip on every request (N+1)
  visible in slow query logs but no SLA breach yet.
- N1: yes (log entry).
- N2: yes (call API).
- N3: yes.
- N4: no — no functional manifestation; the user does not see slower
  responses past the SLA.
- Result: **rejected (N4)**. Moved to `open_questions.md` (performance
  observation, not a functional bug).

## Calibration

The κ ≥ 0.7 target is monitored quarterly. Each node's rejection rate
is tracked. A node whose rejection rate is wildly imbalanced (e.g. N1
rejecting > 70% of hypotheses) triggers a review: either the node is
too aggressive, the bug-pattern catalog is generating poor hypotheses,
or the runtime's grounding is failing.
