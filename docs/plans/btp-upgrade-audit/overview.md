# siae-btp-upgrade-audit — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Creare la skill `siae-btp-upgrade-audit` in siae-dev-forge per rilevare regressioni di business logic durante l'upgrade delle librerie SAP BTP deprecate nel repo `itsiae/liquidazione`.
**Architettura:** Skill markdown a due fasi (BASELINE + AUDIT). Layer 1 estrae meccanicamente via bash (grep). Layer 2 estrae semanticamente via Claude con schema YAML locked. Diff strutturale produce gap report per app.
**Stack:** Markdown (skill), Bash (layer1), YAML (fingerprint schema), GitHub API via `gh` CLI
**SP:** 13 SP-Umano / 5 SP-Augmented
**Design doc:** `docs/plans/2026-03-31-btp-upgrade-audit-design.md`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Skill skeleton + frontmatter + banner | `task-01-skill-skeleton.md` | [PENDING] |
| 2 | Phase 1 BASELINE: app discovery + Layer 1 grep (deprecated imports + OData v2) | `task-02-layer1-deprecated-odata.md` | [PENDING] |
| 3 | Phase 1 BASELINE: Layer 1 grep (method signatures + navigation + routing) | `task-03-layer1-signatures-nav.md` | [PENDING] |
| 4 | Phase 1 BASELINE: Layer 2 schema-locked (error_handlers + logic_blocks + external_calls) | `task-04-layer2-schema-locked.md` | [PENDING] |
| 5 | Phase 2 AUDIT: diff engine (confronto fingerprint old vs new + severity) | `task-05-diff-engine.md` | [PENDING] |
| 6 | Phase 2 AUDIT: gap report generator (CRITICAL / LOGIC DIFF / INFO / OK) | `task-06-gap-report.md` | [PENDING] |
| 7 | Registrazione skill + test smoke con `appavvisi` | `task-07-registration-test.md` | [PENDING] |

## Dipendenze

- Task 2 e 3 dipendono da Task 1 (skeleton deve esistere)
- Task 4 dipende da Task 2+3 (la skill deve già avere la sezione Phase 1)
- Task 5 dipende da Task 2+3+4 (entrambi i layer devono essere definiti)
- Task 6 dipende da Task 5 (il diff engine deve esistere)
- Task 7 dipende da tutti i task precedenti
- Task 3 è eseguibile in parallelo con Task 2
