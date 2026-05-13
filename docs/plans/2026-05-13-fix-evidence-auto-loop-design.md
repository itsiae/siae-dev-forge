---
status: draft
created: 2026-05-13
revised: 2026-05-13 (iter 1 spec-review — scope reduction MVP, token budget, edge oscillazione)
topic: fix-evidence-auto-loop
owner: lodetomasi
priority: medium
sp_human: 4.0
sp_augmented: 1.5
predecessor: docs/plans/2026-05-13-review-evidence-v2-scoring-design.md
---

# Design — Skill `siae-fix-evidence` — Auto-Fix Loop hook-driven

## North star

Chiudere il loop manuale del dev-driven fix. Hook v2 `review-evidence` emette
`block_reasons` atomici, ma il dev fixa a mano. Questa skill compone skill
DevForge esistenti per **auto-fix** quando il block è remediable.

## Pain point

Demo PR #243 ha mostrato 5 decision branch ma il dev deve:
1. Leggere `reason` JSON
2. Capire quale skill DevForge invocare (TDD per coverage, debugging per security, ecc.)
3. Lanciare la skill manualmente
4. Re-run hook
5. Iterare

Tempo medio: 2-3 min per ciclo × 3-5 cicli = 10-15 min puro orchestration overhead. Auto-loop riduce a 0.

## Componenti

```
┌──────────────────────────────────────────────────────────────┐
│ skills/siae-fix-evidence/SKILL.md (NEW)                      │
│  • Trigger: /forge-fix-evidence (manual MVP)                  │
│  • Lee .claude/review-evidence/<sha>.json                     │
│  • Skip conditions:                                            │
│    - hard_floor_breaches (richiede BREAK-GLASS human)         │
│    - is_bot_pr (no orchestration needed)                      │
│    - SEVERELY_DEGRADED (bug infra, non code)                  │
│  • Loop max 5 iter + cost cap $5                              │
│  • Per ogni block_reason atomic → dispatch fix action         │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ lib/review_evidence/fix_parser.py (NEW)                      │
│  • parse_block_reasons(evidence) → list[FixAction]            │
│  • FixAction dataclass: kind, prompt, sub_skill, priority     │
│  • 5 atomic patterns:                                         │
│    - coverage_below_threshold:X<Y → sub_skill=siae-tdd        │
│    - lint_errors:N>0             → sub_skill=siae-code-stds  │
│    - complexity_max:X>Y          → sub_skill=siae-tdd refactor│
│    - drift_severity_high         → sub_skill=siae-brainstorming│
│    - security:high:N             → sub_skill=siae-debugging  │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
   For each FixAction (priority order):
     1. Skill tool invoke sub_skill with prompt
     2. Wait subagent completion + commit
     3. Re-run hooks/review-evidence (compute new SHA evidence)
     4. Parse new evidence
     5. If decision == AUTO_APPROVE → break
     6. If decision in [BLOCK_HARD_FLOOR, SEVERELY_DEGRADED] → escalate human
     7. Else → next iter (max 5)
```

## Skill markdown structure

`skills/siae-fix-evidence/SKILL.md` segue pattern DevForge:

```markdown
# siae-fix-evidence — Auto-Fix Loop hook-driven

## Quando si applica
- `review-evidence v2` ha emesso BLOCK_REGRESSION (NOT BLOCK_HARD_FLOOR)
- Branch è ahead di main
- Working tree clean (no uncommitted changes)

## Skip conditions
- hard_floor_breaches non vuoto → ESCALATE human (BREAK-GLASS)
- is_bot_pr=True → ESCALATE (bot non usa DevForge)
- SEVERELY_DEGRADED → ESCALATE (fix tooling first)

## Algorithm
1. Read .claude/review-evidence/<SHA>.json
2. parse_block_reasons(evidence) → actions sorted by priority
3. For action in actions (max 5):
   a. Skill tool invoke action.sub_skill with action.prompt
   b. After commit: re-run `bash hooks/review-evidence`
   c. New evidence parsed
   d. If AUTO_APPROVE → success, break
   e. If new hard_floor → escalate, break
   f. Increment iter counter
4. Final report (iters, $cost, $remaining_budget, final decision)
```

## fix_parser.py — MVP 2 atomic patterns (post scope reduction iter1)

**MVP scope reduction (YAGNI iter1):** 2 atomic pattern coprono 80% block_reasons reali in PR ordinaria (coverage + lint). Complexity / drift / ci_critical deferred a follow-up post-MVP (richiedono integration test più sofisticati).

**ADR-7 (NUOVO post iter1):** Skill tool accetta `args` parameter come stringa dinamica. Pattern già usato da `siae-subagent-development` e `siae-debugging` per passare contesto. Verificato empiricamente nelle sessioni PR #241 + PR #243: `Skill(skill="siae-tdd", args="prompt custom")`. NO re-implementazione delle skill esistenti necessaria.

**ADR-8 (NUOVO post iter1):** Schema v2 `RegressionVerdict.reason` format CANONICO è definito QUI come parte di questo design. `regression.py` esistente in PR #243 commit `c3b6e74` emette già:
- `coverage_below_threshold:{actual}<{threshold}`
- `lint_errors:{actual}>{threshold}`
- `coverage_delta:{delta}<{budget}` (formato esteso warn zone)

Riga `lib/review_evidence/regression.py:75` (PR #243). Quindi le regex sono ALLINEATE a output reale, non speculative.

```python
PATTERNS = [
    # coverage_below_threshold:45<60
    (re.compile(r"coverage_below_threshold:(\d+(?:\.\d+)?)<(\d+(?:\.\d+)?)"),
     lambda m: FixAction(
         kind="coverage",
         priority=2,
         sub_skill="siae-tdd",
         prompt=f"Aggiungi test per portare coverage da {m.group(1)} a "
                f"{m.group(2)}+. Usa file uncovered da "
                f".claude/review-evidence/<sha>.json::metrics.coverage.per_file. "
                f"Validate path via `jq -e .metrics.coverage.per_file evidence.json` prima."
     )),
    # lint_errors:3>0
    (re.compile(r"lint_errors:(\d+)>(\d+)"),
     lambda m: FixAction(
         kind="lint",
         priority=1,
         sub_skill="siae-code-standards",
         prompt=f"Fixa {m.group(1)} lint errors da .claude/review-evidence/<sha>.json"
                f"::metrics.lint.findings. Validate path via jq prima del fix."
     )),
]

# Out-of-scope MVP (follow-up PR-D):
# - complexity_max:X>Y → siae-tdd refactor
# - drift_severity_high → siae-brainstorming update design doc
# - ci_critical:N>M → siae-debugging SARIF fix
```

**Unknown patterns:** parse_block_reasons emette `FixAction(kind="unknown", sub_skill=None)` per reason non matched. Loop top-level skip questi (no auto-fix possibile, escalate a human).

## Loop pseudo-code (in SKILL.md)

```python
def auto_fix_loop(repo_root: Path, sha: str, max_iter: int = 5, cost_cap_usd: float = 5.0):
    iter = 0
    cost = 0.0
    while iter < max_iter and cost < cost_cap_usd:
        evidence = read_evidence(repo_root, sha)
        if should_skip(evidence):
            return {"status": "ESCALATED", "reason": skip_reason(evidence)}
        actions = parse_block_reasons(evidence)
        if not actions:
            return {"status": "SUCCESS_AUTO_APPROVE", "iters": iter}
        action = actions[0]  # highest priority
        # Dispatch via Skill tool
        invoke_skill(action.sub_skill, action.prompt)
        # subagent commits its fix
        sha = git_rev_parse_head()  # new SHA after commit
        # Re-run hook
        run_hook(sha)
        evidence = read_evidence(repo_root, sha)
        cost += estimate_iter_cost()  # rough $ from token usage
        iter += 1
    if iter >= max_iter:
        return {"status": "MAX_ITER_EXCEEDED", "iters": iter}
    return {"status": "COST_CAP_EXCEEDED", "cost": cost}
```

## Decisioni chiave

| Decisione | Scelta | Razionale |
|---|---|---|
| Approccio | A — Skill composer markdown + Python parser | Riusa skill esistenti, time-to-deliver minimo |
| Trigger MVP | Manuale `/forge-fix-evidence` | Auto-trigger su hook = hook change, out of scope. MVP manual è già 80% value |
| Hard floor auto-fix | NO | Security critical richiede human judgment (compliance, design review) |
| Bot PR auto-fix | NO | Bot non usa DevForge, mancano signal skill_adoption |
| SEVERELY_DEGRADED auto-fix | NO | Bug infra (tool missing), non code |
| Max iter | 5 hard cap | Pattern memory `feedback_spec_reviewer_iter2_roi` |
| Cost cap | **Token budget 200k default** (iter1 fix: era $5 non verificabile, ora token-based) | Misurabile via Claude API usage. ENV `DEVFORGE_FIX_EVIDENCE_TOKEN_BUDGET` |
| **NEW (iter1) Oscillation guard** | Se stesso `block_reasons set` per ≥2 iter consecutivi → escalate human | Memory pattern fix oscillatorio (coverage↑→complexity↑→coverage↓) |
| Branch strategy | Stacked `feat/auto-fix-evidence` su PR #243 | Non bloccare review Mario |

## Acceptance criteria (post iter1 scope reduction)

1. Skill `skills/siae-fix-evidence/SKILL.md` esiste con frontmatter (name, description, triggers, allowed-tools)
2. `lib/review_evidence/fix_parser.py` con `parse_block_reasons(evidence) → list[FixAction]`
3. **2 atomic patterns MVP matched: coverage_below_threshold + lint_errors** (3 follow-up deferred)
4. Test unit `tests/test_fix_parser.py` con 2 scenari + edge case empty reasons + unknown reason → kind="unknown"
5. Skip conditions verificati (hard_floor / bot_pr / SEVERELY_DEGRADED → escalate)
6. Max iter 5 + **token budget 200k** enforced (iter1 fix: token-based vs $)
7. **Oscillation guard:** stesso block_reasons set per ≥2 iter → escalate (iter1 fix)
8. Test E2E con evidence sintetica BLOCK_REGRESSION simulato (1 iter → AUTO_APPROVE)
9. `commands/forge-fix-evidence.md` (skill exposed via command)
10. ENV_VARS.md aggiornato (`DEVFORGE_FIX_EVIDENCE_TOKEN_BUDGET`, `DEVFORGE_FIX_EVIDENCE_MAX_ITER`)
11. CHANGELOG.md entry follow-up v2 (sotto v1.55.0 Pending)

## Edge case

| Edge | Mitigation |
|---|---|
| Reason malformed (`coverage_below_threshold` senza `:X<Y`) | parse_block_reasons emette `UnknownReason` action → log + skip |
| Multiple reason same kind | Ordina per priority, applica sequenziale (no concurrent same-file edits) |
| Skill sub_skill non-existent | Fail-safe escalate human, no crash |
| Cost cap reached mid-iter | Commit gia' fatti restano, log partial progress, escalate |
| Infinite loop (fix introduce nuovo block) | Max iter 5 enforced, anche se cost cap non raggiunto |
| Subagent fix fa commit ma hook ancora block | Continua iter (potrebbe fixare progressive) |
| Working tree dirty pre-loop | Pre-flight: abort if dirty (no risk di commit accidentale) |
| Subagent commit fallisce | Catch exception, log, escalate |

## Stima (post iter1 scope reduction)

| Componente | Umano | Augmented |
|---|---|---|
| Skill markdown SKILL.md | 1.0 | 0.5 |
| fix_parser.py + **2 atomic patterns MVP** | 1.0 | 0.5 |
| Loop logic (skip + iter cap + token budget + oscillation guard) | 1.0 | 0.5 |
| Test unit fix_parser + oscillation | 0.5 | 0.0 |
| Test E2E auto-fix loop (mock subagent) | 0.3 | 0.0 |
| commands/forge-fix-evidence.md + ENV_VARS + CHANGELOG | 0.2 | 0.0 |
| **TOTALE** | **4.0** | **1.5** |

(era 6.0/2.5 pre iter1, ridotto -2 SP rimuovendo 3 atomic pattern follow-up)

## Out of scope (Future)

- Auto-trigger su hook output (richiede hook change)
- Multi-PR coordination
- Cost cap dinamico (per-repo, per-team)
- Telemetria fix success rate
- Skill `siae-fix-evidence-watch` (background daemon che monitora `.claude/review-evidence/` e auto-fixa al volo)

## ADR

- **ADR-1** Skill composer markdown + parser Python (vs pure Python)
- **ADR-2** Trigger manuale MVP (vs auto-trigger hook change)
- **ADR-3** Hard floor / bot / degraded → escalate, no auto-fix
- **ADR-4** Max 5 iter + $5 cap (no infinite loop)
- **ADR-5** Stacked branch su PR #243 (no merge wait)
- **ADR-6** Riusa skill esistenti (siae-tdd, siae-debugging, siae-code-standards, siae-brainstorming) — no re-implement
