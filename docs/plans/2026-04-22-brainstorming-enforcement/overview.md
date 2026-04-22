# Brainstorming Enforcement — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Portare adoption `siae-brainstorming` da 3.3% a ≥50% in 30 giorni via hook progressivo (nudge → warn → block) con bypass tracciato + anti-abuse detection.

**Architettura:** Nuovo hook `hooks/brainstorming-gate` (PreToolUse Edit/Write) parallelo a `tdd-gate`. Counter SID-anchored in `$HOME/.claude/.devforge-brainstorm-counter` (schema `SID|N`). Reset su `siae-brainstorming` invocato tramite `hooks/post-skill` (PostToolUse Skill). Bypass `DEVFORGE_SKIP_BRAINSTORMING=1` per-comando con counter giornaliero anti-abuse.

**Stack:** Bash hook + JSONL logger (`lib/logger.sh` — `devforge_get_sid`, `devforge_log`, `devforge_sanitize_json_str`). Test shell con mock HOME isolato.

**SP:** 5 SP-Umano / 2 SP-Augmented

**Design doc:** [2026-04-22-brainstorming-enforcement-design.md](../2026-04-22-brainstorming-enforcement-design.md)

**Branch target:** `feat/brainstorming-enforcement-progressive` (attuale)

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Test scaffold + helper gh/git mock | `task-01-test-scaffold.md` | [PENDING] |
| 2 | Hook scope filter + escape hatch | `task-02-hook-scope-filter.md` | [PENDING] |
| 3 | Counter SID-anchored + 3 livelli (soft/warn/block) | `task-03-counter-levels.md` | [PENDING] |
| 4 | Bypass env var + daily anti-abuse counter | `task-04-bypass-anti-abuse.md` | [PENDING] |
| 5 | Reset counter in post-skill su siae-brainstorming | `task-05-post-skill-reset.md` | [PENDING] |
| 6 | Hooks.json registration + run-all.sh integration | `task-06-hooks-json-integration.md` | [PENDING] |

## Dipendenze

- Task 1 è prerequisito per Task 2-6 (infrastruttura test condivisa).
- Task 3 dipende da Task 2 (estende lo scaffold del hook).
- Task 4 dipende da Task 3 (aggiunge bypass + anti-abuse al flusso).
- Task 5 dipende da Task 3 (reset del counter prodotto da Task 3).
- Task 6 dipende da tutti i precedenti (wiring finale).

## Criteri globali di accettazione

- 12/12 scenari test passano in `tests/hooks/brainstorming-gate.test.sh`
- Test esistenti restano verdi: `post-commit-review-sha`, `post-skill-plan-events`, `post-commit-pr-lifecycle`
- 6 eventi telemetry nuovi emessi: `brainstorming_nudge_soft`, `brainstorming_gate_warn`, `brainstorming_gate_blocked`, `brainstorming_gate_bypassed`, `brainstorming_bypass_abuse_suspected`, `brainstorming_invoked_post_gate`
- Counter `SID|N` stabile su stash/checkout (SID-anchored, non session-skills-dependent)
- `DEVFORGE_ENFORCEMENT_OFF=1` → skip immediato sempre (escape hatch)
- W1 opt-in: attivo solo con `DEVFORGE_ENFORCEMENT_STRICT=1`
- Hook wall-clock < 500ms anche con counter file I/O

## Branching + push finale

Ogni task produce 1 commit atomico. Dopo Task 6:

```bash
git push -u origin feat/brainstorming-enforcement-progressive
gh pr create --base main --title "feat(hook): brainstorming-gate progressive enforcement" --body-file /tmp/pr-body-enforcement.md
```
