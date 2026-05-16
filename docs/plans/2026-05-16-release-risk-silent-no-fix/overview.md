# Release-Risk Silent-NO Fix — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development` per implementare questo piano task per task.

**Goal:** Eliminare 2 silent-failure scoperti nel detector release-risk (Criterion 5 KG-unavailable mascherato da NO, Criterion 6 false positive su tag pattern SIAE custom + subprocess fail silenziato).

**Architettura:** Modifica `lib/release_risk/{detector.py,kg_lookup.py,cli.py}` per propagare status esplicito (`OK`/`UNAVAILABLE`) da subprocess git e da MCP JSON prefetch. Detector mappa status `UNAVAILABLE` → `TOOL_UNAVAILABLE`, dati assenti → `REQUIRES_INPUT`. Zero fallback silente a `0`/`NO`.

**Stack:** Python 3.11, pytest, dataclass `CriterionResult` (status Literal YES/NO/REQUIRES_INPUT/TOOL_UNAVAILABLE).

**SP:** 1 (Umano) · 0.4 (Augmented)

**Design doc:** `docs/plans/2026-05-16-release-risk-silent-no-fix-design.md`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Test red Criterion 6 (tag pattern + status) | `task-01-test-c6-tag-pattern-red.md` | [DONE] |
| 2 | Fix Criterion 6 + `_count_release_tags` (green) | `task-02-fix-c6-tag-pattern-green.md` | [DONE] |
| 3 | Test red Criterion 5 (KG-unavailable propagation) | `task-03-test-c5-kg-unavailable-red.md` | [DONE] |
| 4 | Fix `mcp_invoker_from_json_file` + `lookup_criticality` (green) | `task-04-fix-c5-kg-unavailable-green.md` | [DONE] |
| 5 | Integration re-run scorecard pae-deposito-musica-fe | `task-05-integration-rerun-pae.md` | [DONE] |
| 6 | CHANGELOG + version bump 1.57.0 → 1.58.0 | `task-06-changelog-version-bump.md` | [PENDING] |

## Dipendenze

- Task 2 dipende da Task 1 (test red → fix green)
- Task 4 dipende da Task 3 (test red → fix green)
- Task 1+2 e Task 3+4 sono indipendenti tra loro (possono essere paralleli)
- Task 5 dipende da Task 2 + Task 4
- Task 6 dipende da Task 5 (CHANGELOG documenta solo fix verificati)

## Acceptance globale

- [ ] Scorecard re-run su `pae-deposito-musica-fe release/2.3.4` mostra: Criterion 6 = NO, Criterion 5 = REQUIRES_INPUT, score ≤ 4 (LOW)
- [ ] `pytest tests/test_release_risk_*` esce 0 con 134 esistenti + 7 nuovi PASS
- [ ] `git tag --list 'release*' 'v*' '*RELEASE*' '*-RELEASE' 'RELEASE-*'` riconosciuto come pattern default
- [ ] Env var `DEVFORGE_RELEASE_RISK_TAG_GLOBS` override funzionante
