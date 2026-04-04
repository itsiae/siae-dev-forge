# DevForge Infrastructure Hardening — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Fix 6 bug infrastrutturali + ristrutturazione sistema triggering skill
**Architettura:** Hook/lib bash + skills-core.js Node.js. State centralizzato in DEVFORGE_STATE_DIR, frontmatter strutturato per triggering deterministico.
**Stack:** Bash, Node.js, js-yaml, Python (eval)
**SP:** 28 SP-Umano / 11 SP-Augmented
**Design doc:** `docs/plans/2026-04-02-devforge-infra-hardening-design.md`

---

## Indice Task

| # | Task | Deliverable | File | Stato |
|---|------|-------------|------|-------|
| 01 | STATE_DIR + bug fix plumbing | D1 | `task-01-state-dir.md` | [DONE] |
| 02 | Test ermetici con flag | D2 | `task-02-test-hermetic.md` | [PENDING] |
| 03 | Split session-start | D3 | `task-03-split-session-start.md` | [PENDING] |
| 04 | Manifest generato | D4 | `task-04-manifest-generator.md` | [DONE] |
| 05 | YAML parser js-yaml | D5 | `task-05-yaml-parser.md` | [PENDING] |
| 06 | Gate contract espliciti | D6+D6b | `task-06-gate-contracts.md` | [DONE] |
| 07 | Frontmatter strutturato | D7 | `task-07-structured-frontmatter.md` | [PENDING] |
| 08 | Output JSON skills-core | D8 | `task-08-json-output.md` | [DONE] |
| 09 | Shortlist contestuale reinject | D9 | `task-09-shortlist.md` | [PENDING] |
| 10 | Eval gate con soglie | D10 | `task-10-eval-gate.md` | [PENDING] |
| 11 | Strumentazione mismatch | D11 | `task-11-instrumentation.md` | [PENDING] |

## Dipendenze

```
Task 01 (D1) ──→ Task 02 (D2)
              ──→ Task 03 (D3)
              ──→ Task 04 (D4) ──→ Task 05 (D5) ──→ Task 07 (D7) ──→ Task 09 (D9)
              ──→ Task 06 (D6+D6b)
Task 08 (D8) ──→ [indipendente, parallelizzabile dopo Task 01]
Task 10 (D10) ──→ [indipendente]
Task 11 (D11) ──→ [indipendente, dopo Task 01 per DEVFORGE_STATE_DIR]
```

**Wave 1:** Task 01 (prerequisito)
**Wave 2:** Task 02, 03, 04, 06, 08, 10, 11 (paralleli)
**Wave 3:** Task 05 (dopo 04)
**Wave 4:** Task 07 (dopo 05)
**Wave 5:** Task 09 (dopo 07)
