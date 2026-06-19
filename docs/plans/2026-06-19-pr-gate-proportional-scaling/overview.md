# Scaling proporzionale gate PR — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: `siae-subagent-development` (stessa sessione) o
> `siae-executing-plans` (sessione separata) per eseguire i task in TDD.

**Goal:** I gate PR (`pr-premortem-gate`, `pr-blind-review-gate`) scalano sul rischio del
diff: `risk=low` (doc/manifest) → advisory; `risk=code` → hard-block invariato. Floor
security/secret intatto.

**Architettura:** nuovo `lib/diff-risk-classifier.sh` (signal path/estensione-based,
rename-aware, fail-safe `code`); i 2 gate lo invocano e downgrade ad advisory su `low`;
2 SKILL.md allineate per coerenza.

**Stack:** Bash hooks + test bash. **SP:** Umano 3 · Augmented 1.

**Design doc:** `docs/plans/2026-06-19-pr-gate-proportional-scaling-design.md` (approved)

**Branch:** creare `feat/pr-gate-proportional-scaling` da `main` (NON sul branch corrente).

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | `lib/diff-risk-classifier.sh` + test | `task-01-diff-classifier.md` | [DONE] |
| 2 | Downgrade advisory nei 2 gate PR + test | `task-02-gate-advisory.md` | [DONE] |
| 3 | Allineamento SKILL.md (premortem + blind-review) | `task-03-skill-coherence.md` | [DONE] |

## Dipendenze
- Task 2 dipende da Task 1 (i gate chiamano il classifier).
- Task 3 indipendente (doc skill); può andare in parallelo, commit dopo Task 2.

## Mappa AC → Task
| AC | Task |
|----|------|
| AC-1..6, AC-11..14 (classifier) | 1 |
| AC-7, AC-8, AC-9, AC-10 (gate advisory + no-regression + floor) | 2 |
| Criterio #7 (coerenza skill) | 3 |
