# TDD Gate External Files — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Il TDD gate non blocca file esterni al repository git corrente
**Architettura:** Aggiungere check prefix-match su GIT_ROOT in `hooks/tdd-gate`
**Stack:** Bash
**SP:** 2 SP-Umano / 1 SP-Augmented
**Design doc:** `docs/plans/2026-03-30-tdd-gate-external-files-design.md`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Aggiungere check file esterno al repo in tdd-gate | `task-01-external-file-check.md` | [DONE] |
