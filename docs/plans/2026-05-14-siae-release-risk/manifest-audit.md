# Plugin manifest audit — pre-bump 1.57.0

**Data audit:** 2026-05-14
**Branch:** feat/siae-release-risk
**Manifest auditato:** `.claude-plugin/plugin.json` (v1.56.0)

## Count drift

| Tipo | On-disk pre-merge | Manifest attuale | Drift | Post-merge atteso |
|---|---|---|---|---|
| Skills | 41 | 39 | -2 | 42 (+1) |
| Commands | 16 | 11 | -5 | 17 (+1) |
| Agents | 5 | 3 | -2 | 5 (invariato) |
| Hooks | 23 | 21 | -2 | 24 (+1) |

**Drift cause:** manifest description non aggiornato in PR precedenti (recurring issue).
**Fix:** task-38 bump applica counts post-merge corretti (42/17/5/24).

## Comandi audit (riproducibilità)

```bash
# Skills
ls -1 skills/ | grep -vE "^\." | wc -l
# -> 41

# Commands
ls -1 commands/*.md | wc -l
# -> 16

# Agents (esclude SPORT_KG_TOOLS.yaml che è registry, non agent)
ls -1 agents/*.md | wc -l
# -> 5

# Hooks (esclude lib/, run-hook.cmd, hooks.json, ENV_VARS.md)
ls -1 hooks/ | grep -vE "^(lib|run-hook\.cmd|hooks\.json|ENV_VARS\.md)$" | wc -l
# -> 23
```

## Inventory on-disk pre-merge

### Skills (41)

code-coverage, siae-architecture, siae-automation, siae-autoresearch, siae-blind-review, siae-brainstorming, siae-branching-strategy-check, siae-code-standards, siae-codebase-map, siae-data-engineering, siae-debugging, siae-dev-analytics, siae-documentation, siae-executing-plans, siae-finishing-branch, siae-finops, siae-fix-evidence, siae-flutter, siae-frontend, siae-git-env, siae-git-workflow, siae-git-worktrees, siae-iac, siae-jasper-from-pdf, siae-microservices-map, siae-nr-test-flows, siae-onboarding, siae-parallel-agents, siae-qa, siae-receiving-review, siae-requesting-review, siae-retrospective, siae-robot-framework, siae-security, siae-service-logic-map, siae-subagent-development, siae-tdd, siae-verification, siae-writing-plans, siae-writing-skills, using-devforge.

### Commands (16)

code-coverage, forge-adoption, forge-analytics, forge-automate, forge-cost, forge-doc, forge-evidence, forge-finops, forge-fix-evidence, forge-flows, forge-implement, forge-jasper, forge-mcp-preflight, forge-mcp-snapshot, forge-score, forge-test.

### Agents (5)

code-reviewer, doc-generator, mcp-impact-analyst, qa-investigator, spec-reviewer.

**Esclusi:** `agents/SPORT_KG_TOOLS.yaml` (registry MCP tools, non agent dispatchabile).

### Hooks (23)

batch-checkpoint, batch-reset, brainstorming-gate, capture-test-result, devforge-context, devforge-flusher, plan-gate, plan-gate-write, post-commit-review, post-skill, pr-blind-review-gate, pr-gate, pre-commit, review-evidence, session-start, setup-mcp-kibana, setup-mcp-sport, skill-advisory, sport-task-detect, state-writer, stop-gate, sub-skill-gate, tdd-gate.

**Esclusi:** `lib/` (helper scripts), `run-hook.cmd`, `hooks.json`, `ENV_VARS.md`.

## Post-merge expected (target task-38 bump)

Dopo il merge della release `feat/siae-release-risk`:

- **+1 skill:** `siae-release-risk` (gestione PR risk classification)
- **+1 command:** `forge-release-risk` (trigger explicit risk check)
- **+1 hook:** `release-risk-gate` (pre-commit/pre-push hook per high-risk changes)
- **agents invariato:** nessun nuovo agent in release-risk track

**Target counts manifest description post-bump:** `42 skill, 17 comandi, 5 agent, 24 hook`.

## Action items

1. **task-38 bump 1.57.0:** aggiornare `.claude-plugin/plugin.json` description con counts post-merge corretti.
2. **Follow-up architetturale:** considerare auto-generazione description da `ls` count via hook pre-commit (eliminare drift recurring).
