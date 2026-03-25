# branching-strategy-check — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Portare la skill `branching-strategy-check` in siae-devforge con scan org-wide + summary hook a SessionStart.
**Architettura:** Nuova skill SKILL.md per scan on-demand; modifica hook session-start per iniettare summary compact da cache (TTL 4h) all'avvio sessione.
**Stack:** Bash, GitHub CLI (`gh`), Markdown
**SP:** 2 SP-Umano / 1 SP-Augmented
**Design doc:** `docs/plans/2026-03-25-branching-strategy-check-design.md`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Crea SKILL.md branching-strategy-check | `task-01-skill-md.md` | [PENDING] |
| 2 | Modifica session-start: branching summary | `task-02-session-start-hook.md` | [PENDING] |
| 3 | Aggiorna plugin.json skill count | `task-03-plugin-json.md` | [PENDING] |

## Dipendenze

- Task 2 e 3 sono indipendenti da Task 1
- Tutti e 3 possono girare in parallelo
