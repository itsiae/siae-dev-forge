---
task: 12
title: hooks.json wiring + env var documentation
size: S
depends: [10, 11]
blocks: [13]
---

# Task 12 — hooks.json + rollback docs

Aggiornamenti a `hooks/hooks.json` per registrare nuovi hook + documentazione
env var nel `hooks/README.md` (se esistente) o `docs/hooks-env-vars.md`.

## hooks.json diff

```diff
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        { "command": "... pre-commit", "timeout": 10 },
+       { "command": "... pr-blind-review-gate", "timeout": 10 },
        { "command": "... pr-gate", "timeout": 15 }
      ]
    },
+   {
+     "matcher": "Write",
+     "hooks": [
+       { "command": "... plan-gate-write", "timeout": 5 },
+       { "command": "... tdd-gate", "timeout": 5 },
+       { "command": "... brainstorming-gate", "timeout": 5 }
+     ]
+   },
    {
      "matcher": "Edit",
      "hooks": [
        { "command": "... tdd-gate", "timeout": 5 },
        { "command": "... brainstorming-gate", "timeout": 5 }
      ]
    }
  ]
```

Note:
- `plan-gate-write` precede tdd/brainstorming su Write matcher (decide prima su design docs)
- `tdd-gate` e `brainstorming-gate` già funzionanti su Edit; aggiunti su Write
  per coprire file creation flow (nuovo file produzione via Write)
- `pr-blind-review-gate` dopo `pre-commit` e prima di `pr-gate` (ordine stabile)

## Env var matrix

Documentare in `hooks/ENV_VARS.md` (nuovo file):

| Env var | Default | Scope | Descrizione |
|---|---|---|---|
| `DEVFORGE_ENFORCEMENT_OFF` | 0 | Global | Disabilita tutti i gate (esistente) |
| `DEVFORGE_USE_SESSION_SCOPE` | 0 | **PR #2 NEW** | Rollback globale: ripristina session-scoped enforcement |
| `DEVFORGE_FORCE_STOP` | 0 | **PR #2 NEW** | Escape esplicito stop-gate (sostituisce 2-block) — tracked 3/day |
| `DEVFORGE_BASH_TDD` | 0 | **PR #2 NEW** | Opt-in TDD per .sh/.bash (deny-by-default) |
| `DEVFORGE_SKIP_BLIND_REVIEW` | 0 | **PR #2 NEW** | Bypass pr-blind-review-gate — tracked 5/day |
| `DEVFORGE_SKIP_BRAINSTORMING` | 0 | Existing | Bypass brainstorming-gate — tracked 5/day |
| `DEVFORGE_SKIP_GIT_GATE` | 0 | Existing | Bypass pre-commit git-workflow check — tracked 5/day |
| `DEVFORGE_SKIP_RETRO_GATE` | 0 | Existing | Bypass stop-gate retrospective check |
| `DEVFORGE_ENFORCEMENT_STRICT` | 0 | Deprecated | Ex W2 strict mode — removed in PR #2 |
| `DEVFORGE_W2_DEFAULT` | N/A | **REMOVED** | No-op, gate sempre attivo |

## Rollout strategy

1. **Pre-merge**: branch stacked, test passa, shadow-log divergenza <10% (task 13)
2. **Merge**: default attivo dopo merge
3. **Settimana 1 post-merge**: monitorare `gate_divergence` log. Se divergenza
   >10% → revert PR #2 via `DEVFORGE_USE_SESSION_SCOPE=1` globale + hotfix
4. **Settimana 2**: misurare adoption per-task (baseline-metrics-tasks.json)
5. **Settimana 3+**: rimuovere dual-write se divergenza <2%, mantenere
   solo task-scoped (follow-up PR)

## Acceptance

- [ ] `hooks/hooks.json` aggiornato con pr-blind-review-gate + plan-gate-write + Write matcher per tdd/brainstorming
- [ ] `hooks/ENV_VARS.md` creato con matrix completa
- [ ] Test: `jq .` su hooks.json valido (no broken JSON)
- [ ] Test integration: ogni nuovo matcher viene scelto da Claude Code runtime (smoke test manuale)

## Out of scope

- Soft-remove DEVFORGE_ENFORCEMENT_STRICT → deferred follow-up (ora deprecato, no-op nel codice)
