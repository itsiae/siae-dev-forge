---
title: Tiered CLAUDE.md — piano implementativo
date: 2026-05-19
design_doc: docs/plans/2026-05-19-tiered-claude-md-design.md
status: PENDING_APPROVAL
total_tasks: 8
sp_human: 5
sp_augmented: 2
---

# Tiered CLAUDE.md — Plan Overview

Implementazione gerarchia CLAUDE.md L1+L2+L3 secondo best practice Anthropic
post "How Claude Code works in large codebases" (14 mag 2026) + hook
SessionStart advisory non-bloccante per stale detection.

Design doc: [2026-05-19-tiered-claude-md-design.md](../2026-05-19-tiered-claude-md-design.md)

## Indice task

| # | Task | Stato | Dipende da | Tipo |
|---|---|---|---|---|
| 01 | Scaffold sub-skill `siae-codebase-map-tiered` | [PENDING] | — | scaffold |
| 02 | TDD `emit-claude-md.py` | [PENDING] | 01 | TDD |
| 03 | TDD `anti-bloat-lint.py` | [PENDING] | 01 | TDD |
| 04 | Modifica `siae-codebase-map` Step 7 (invocazione condizionale) | [PENDING] | 02, 03 | edit |
| 05 | TDD hook `session-start-tiered-advisor` | [PENDING] | — | TDD |
| 06 | Aggiornare `hooks/hooks.json` con entry SessionStart | [PENDING] | 05 | edit |
| 07 | Aggiornare test no-regression hook count | [PENDING] | 06 | test |
| 08 | Version bump dual-source + CHANGELOG + PR | [PENDING] | 01-07 | release |

## Dipendenze critiche

```
01 (scaffold) ──┬─→ 02 (emit-claude-md)
                └─→ 03 (anti-bloat-lint)
                         │
                         ▼
                    04 (codebase-map Step 7)
                         │
05 (hook) ──→ 06 (hooks.json) ──→ 07 (test count)
                                       │
                                       ▼
                                  08 (release)
```

Task 01-04 e 05-07 sono **parallel-safe** (rami indipendenti). Subagent paralleli possibili.

## Criteri di accettazione globali

Vedi design doc Section "Criteri di accettazione" — 10 AC.

Sintesi:
1. `/forge-map --tiered` genera L1 + L2 per Maven module
2. L2 contiene import `@../CLAUDE.md`
3. L3 solo se >=10 file + pattern locale distintivo
4. Hook session-start stale detection (>=30 commit OR >14gg) → additionalContext, exit 0
5. `/forge-map` senza `--tiered` invariato (backward compatible)
6. Anti-bloat: <200 righe OR warning
7. Test no-regression count +1
8. Hook errors silent
9. plugin.json + marketplace.json allineati
10. CHANGELOG v1.61.0

## Execution handoff

Opzione consigliata: **subagent paralleli stessa sessione** via `siae-subagent-development`.
- Rami 01→02→03→04 e 05→06→07 paralleli
- Task 08 (release) seriale dopo tutti gli altri
- Memory `feedback_parallel_subagent_git_race`: usare worktree dedicate

Riferimento: `siae-executing-plans` se sessione separata.
