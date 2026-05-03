# PR-6 Skill Polish — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development` per implementare questo piano task per task.

**Goal:** Polish finale skill non-core: tdd trigger reduction (no-regression), service-logic-map disambiguazione 2 modalità, subagent tool whitelist, sequence hint advisory.

**Architettura:** Edit frontmatter agent + skill, no nuovi hook, no nuovi file (eccetto eventuali reference per service-logic-map).

**Stack:** Markdown skill/agent frontmatter.

**SP:** 2 SP-Augmented.

**Design doc:** `../2026-05-03-skill-alignment-design.md` (sezioni 5.1-5.4).

**Vincolo critico:** NO-REGRESSION specialmente per Task 01 (tdd trigger). Lista keyword removed in CHANGELOG plugin obbligatorio. Smoke test pre-merge con 10 prompt che usano vecchie keyword.

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | tdd trigger keyword reduction (20+ → 5-8) + CHANGELOG removed list | `task-01-tdd-trigger-reduction.md` | [PENDING] |
| 2 | service-logic-map disambiguazione 2 modalità (frontmatter + flowchart) | `task-02-service-logic-map-disambiguation.md` | [PENDING] |
| 3 | Subagent `code-reviewer` tool whitelist | `task-03-agent-code-reviewer-tools.md` | [PENDING] |
| 4 | Subagent `spec-reviewer` tool whitelist | `task-04-agent-spec-reviewer-tools.md` | [PENDING] |
| 5 | Subagent `mcp-impact-analyst` tool whitelist | `task-05-agent-mcp-impact-analyst-tools.md` | [PENDING] |
| 6 | Subagent `qa-investigator` tool whitelist | `task-06-agent-qa-investigator-tools.md` | [PENDING] |
| 7 | Subagent `doc-generator` tool whitelist | `task-07-agent-doc-generator-tools.md` | [PENDING] |
| 8 | Sequence hint advisory `siae-verification` | `task-08-sequence-hint-verification.md` | [PENDING] |
| 9 | Sequence hint advisory `siae-architecture` | `task-09-sequence-hint-architecture.md` | [PENDING] |
| 10 | Sequence hint advisory `siae-finishing-branch` | `task-10-sequence-hint-finishing-branch.md` | [PENDING] |
| 11 | Smoke test pre-merge: 10 prompt vecchi tdd keyword + diff baseline | `task-11-smoke-test-tdd-regression.md` | [PENDING] |
| 12 | Final validation (5/5 agent whitelist, frontmatter coherent, KPI globali) | `task-12-validation.md` | [PENDING] |

## Dipendenze

- Task 01 indipendente (con CHANGELOG inline)
- Task 02 indipendente
- Task 03-07 indipendenti tra loro (5 agent diversi)
- Task 08-10 indipendenti tra loro (3 skill diverse)
- Task 11 dipende da Task 01 (testa la riduzione)
- Task 12 dipende da tutti

## Criteri accettazione PR

- tdd trigger keyword count ≤8
- CHANGELOG documenta keyword removed con migration path
- service-logic-map description distingue 2 modalità (build-catalog vs impact-analysis) con trigger separati
- 5/5 agent con `tools:` array popolato
- 3+ skill (verification, architecture, finishing-branch) con sequence hint nel description
- Smoke test 10 prompt vecchi tdd keyword: ≥80% ancora attivano siae-tdd (no-regression principle)
- Suite Bedrock post PR-6: accuracy ≥ post-PR-5 (cumulative no-regression)
