# SDLC Backbone — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Introdurre catena SDLC minima obbligatoria con 7 fasi backbone, state machine, 3 gate phase-based
**Stack:** Bash, Node.js (skills-core.js), JSON state
**SP:** 8 SP-Umano / 3 SP-Augmented
**Design doc:** `docs/plans/2026-04-04-sdlc-backbone-design.md`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Frontmatter backbone metadata su tutte le skill | `task-01-frontmatter-metadata.md` | [PENDING] |
| 2 | State machine lib/sdlc-state.sh | `task-02-state-machine.md` | [PENDING] |
| 3 | post-skill avanza stage | `task-03-post-skill-advance.md` | [PENDING] |
| 4 | impl-gate (sostituisce tdd-gate + plan-gate) | `task-04-impl-gate.md` | [PENDING] |
| 5 | close-gate (sostituisce stop-gate enforcement + pre-commit enforcement) | `task-05-close-gate.md` | [PENDING] |
| 6 | stage-gate (sostituisce sub-skill-gate) | `task-06-stage-gate.md` | [PENDING] |
| 7 | Context injection phase-based | `task-07-context-injection.md` | [PENDING] |
| 8 | Nuova skill siae-review-gate | `task-08-review-gate.md` | [PENDING] |
| 9 | Test + eval backbone | `task-09-tests.md` | [PENDING] |

## Dipendenze

```
Task 1 (metadata) ──→ Task 2 (state machine) ──→ Task 3 (post-skill)
                                                ──→ Task 4 (impl-gate)
                                                ──→ Task 5 (close-gate)
                                                ──→ Task 6 (stage-gate)
Task 7 (context injection) ──→ dopo Task 2
Task 8 (review-gate skill) ──→ dopo Task 1
Task 9 (tests) ──→ dopo tutti
```

**Wave 1:** Task 1 (metadata) + Task 8 (review-gate skill)
**Wave 2:** Task 2 (state machine)
**Wave 3:** Task 3, 4, 5, 6, 7 (paralleli, tutti dipendono da Task 2)
**Wave 4:** Task 9 (test)
