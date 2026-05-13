---
name: forge-fix-evidence
description: Auto-fix loop hook-driven per BLOCK_REGRESSION review-evidence v2. Legge block_reasons atomici e dispatcha siae-tdd/siae-code-standards via Skill tool fino a AUTO_APPROVE (max 5 iter, token budget 200k, oscillation guard, escalate human su hard_floor/bot/SEVERELY_DEGRADED).
allowed-tools: Read, Bash, Skill
---

# /forge-fix-evidence — Auto-Fix Loop hook-driven

Espone la skill `siae-fix-evidence`. Auto-remediation loop per
`BLOCK_REGRESSION` emesso dal hook `review-evidence v2`. **NON** modifica
file direttamente: invoca sub-skill DevForge esistenti via Skill tool.

## Cosa fa

1. Legge `.claude/review-evidence/<sha>.json` (compute on-demand se assente)
2. Verifica skip conditions (`hard_floor_breaches`, `is_bot_pr`,
   `SEVERELY_DEGRADED`) -> escalate human se match
3. `parse_block_reasons` -> `list[FixAction]` (MVP: coverage + lint)
4. Loop max 5 iter / token budget 200k:
   - Dispatch `Skill(skill=action.sub_skill, args=action.prompt)`
   - Wait commit del subagent
   - Re-run `bash hooks/review-evidence`
   - Re-parse evidence
   - `AUTO_APPROVE` -> break SUCCESS
   - Stesso `block_reasons` set 2 iter consecutivi -> escalate (oscillation)
   - Unknown reason -> escalate
5. Final report markdown (status, iters, tokens, sub-skill log)

## Pre-flight

```bash
# Working tree pulito
git status --porcelain   # empty atteso

# Evidence presente
SHA=$(git rev-parse HEAD)
test -f ".claude/review-evidence/${SHA}.json" || bash hooks/review-evidence

# Decision = BLOCK_REGRESSION
jq -r '.regression_verdict.decision' ".claude/review-evidence/${SHA}.json"
```

## Quando usarlo

- Dopo `gh pr create` se hook `review-evidence v2` ha emesso
  `BLOCK_REGRESSION` (decision branch overridable)
- **NON** usare su `BLOCK_HARD_FLOOR` (richiede admin BREAK-GLASS)
- **NON** usare su `SEVERELY_DEGRADED` (fix tooling prima)
- **NON** usare se sei un bot PR (Dependabot/Renovate)

## Limiti operativi

| Vincolo            | Valore   | Override                                     |
|--------------------|----------|----------------------------------------------|
| Max iter           | 5        | `DEVFORGE_FIX_EVIDENCE_MAX_ITER` (design review) |
| Token budget       | 200_000  | `DEVFORGE_FIX_EVIDENCE_TOKEN_BUDGET`         |
| Concurrent sub-skill | NO     | sequenziale per evitare race su .git/index   |

## Sub-skill dispatch tabella (MVP)

| Reason format                   | Sub-skill            | Priority |
|---------------------------------|----------------------|----------|
| `coverage_below_threshold:X<Y`  | `siae-tdd`           | 2        |
| `lint_errors:N>M`               | `siae-code-standards`| 1        |

Out-of-scope MVP (follow-up PR-D): `complexity_max`, `drift_severity:high`,
`ci_critical:N>M`.

## Final report (atteso)

```
fix-evidence loop — SHA <final-sha>
  Status:        AUTO_APPROVE | ESCALATED | MAX_ITER_EXCEEDED | TOKEN_BUDGET_EXCEEDED
  Iters:         <N>/5
  Tokens:        <consumed>/200_000
  Final reasons: [...]
  Sub-skill log: [(iter, sub_skill, kind), ...]
```

## Design + Plan

- **Skill:** `skills/siae-fix-evidence/SKILL.md`
- **Parser:** `lib/review_evidence/fix_parser.py`
- **Tests:** `tests/test_fix_parser.py`
- **Design:** `docs/plans/2026-05-13-fix-evidence-auto-loop-design.md`
- **Predecessor (v2 scoring):** `docs/plans/2026-05-13-review-evidence-v2-scoring-design.md`
