# DevForge PR Lifecycle Events — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Emettere 5 eventi PR lifecycle (`pr_opened` idempotente, `pr_commit_after_open`, `pr_review_cycle`, `pr_merged`, `pr_metrics`) per coprire il terzo KPI Rosario ("iterazioni tra fine dev e chiusura PR").

**Architettura:** Estensione hook-only di `hooks/post-commit-review`. Snapshot per-PR come source of truth (`$HOME/.claude/.devforge-pr-state-<n>.json`). Wrapper su `gh pr merge` per merge via CLI. Catch-up polling al push per merge via UI web.

**Stack:** Bash + python3 helper + JSONL logger (`lib/logger.sh`). Mock `gh` via PATH shim nei test.

**SP:** 3 SP-Umano / 1 SP-Augmented

**Design doc:** [2026-04-22-devforge-pr-lifecycle-events-design.md](../2026-04-22-devforge-pr-lifecycle-events-design.md)

**Branch target:** `feat/devforge-pr-lifecycle-events` (da creare **dopo** merge di PR #212).

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Setup test file + gh mock shim | `task-01-setup-test-shim.md` | [PENDING] |
| 2 | pr_opened idempotente via snapshot | `task-02-pr-opened-idempotent.md` | [PENDING] |
| 3 | pr_commit_after_open su push successivi | `task-03-pr-commit-after-open.md` | [PENDING] |
| 4 | pr_review_cycle su CHANGES_REQUESTED | `task-04-pr-review-cycle.md` | [PENDING] |
| 5 | pr_merged via gh pr merge (CLI) | `task-05-pr-merged-cli.md` | [PENDING] |
| 6 | pr_metrics aggregato post-merge | `task-06-pr-metrics.md` | [PENDING] |
| 7 | Catch-up polling + pr_merged web | `task-07-catch-up-web.md` | [PENDING] |

## Dipendenze

- Task 1 è prerequisito per Task 2-7 (infrastruttura test condivisa).
- Task 3 dipende da Task 2 (riusa snapshot creato da pr_opened).
- Task 4 dipende da Task 2 (legge `last_review_decision` da snapshot).
- Task 6 dipende da Task 5 (pr_metrics emesso subito dopo pr_merged CLI).
- Task 7 dipende da Task 5+6 (catch-up riusa la stessa logica di pr_merged + pr_metrics).

## Criteri globali di accettazione

- 7/7 test nuovi in `tests/hooks/post-commit-pr-lifecycle.test.sh` passano.
- 2/2 test esistenti (`post-commit-review-sha.test.sh`, `post-skill-plan-events.test.sh`) restano verdi.
- `pr_opened` emesso esattamente 1x per pr_number.
- `pr_metrics.rework_commits` == count `pr_commit_after_open` per pr_number.
- `pr_metrics.review_cycles` == count `pr_review_cycle` per pr_number.
- Snapshot file `.devforge-pr-state-<n>.json` rimosso dopo `pr_merged`.
- Happy path senza PR (push su branch senza PR aperta) resta invariato.

## Branching

```bash
# Dopo merge PR #212:
git checkout main && git pull
git checkout -b feat/devforge-pr-lifecycle-events
```

Ogni task termina con un commit atomico. PR finale aperta dopo Task 7.
