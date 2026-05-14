---
name: siae-fix-evidence
description: >
  Use when review-evidence v2 hook ha emesso BLOCK_REGRESSION e vuoi tentare
  un auto-fix loop hook-driven. Skill composer che legge `block_reasons`
  atomici e dispatcha `siae-tdd` o `siae-code-standards` via Skill tool fino
  ad AUTO_APPROVE (max 5 iter, token budget 200k, oscillation guard).
  Trigger: /forge-fix-evidence, "auto-fix evidence", "rimedio automatico",
  "fixa block_regression", "loop di remediation", BLOCK_REGRESSION ricevuto.
allowed-tools: Read, Bash, Skill
---

```
╔══════════════════════════════════════════════════════════════════╗
║              SIAE Fix Evidence — Auto-Fix Loop                   ║
║              hook-driven remediation composer                    ║
╚══════════════════════════════════════════════════════════════════╝
```

# siae-fix-evidence — Auto-Fix Loop hook-driven

> **Tipo:** Rigid | **Fase SDLC:** 4. Implementation (auto-remediation)
>
> Skill composer: legge `.claude/review-evidence/<sha>.json` e auto-dispatcha
> sub-skill DevForge (`siae-tdd`, `siae-code-standards`) fino ad
> `AUTO_APPROVE` o escalation. **NON modifica file direttamente** — invoca
> solo sub-skill che fanno il commit reale.

---

## LA LEGGE DI FERRO

**SU `BLOCK_REGRESSION` DEL HOOK `review-evidence`, AUTO-FIX FINO AD
`AUTO_APPROVE` O ESCALATE.** Mai loop infiniti, mai bypass nascosti, mai
fix direttamente — solo composizione di sub-skill esistenti.

---

## Quando si applica

- `review-evidence v2` ha emesso `regression_verdict.decision == BLOCK_REGRESSION`
- Branch e' ahead di `main` (commit gia' presenti)
- Working tree pulito (`git status --porcelain` empty)
- Trigger: `/forge-fix-evidence` (manuale, MVP)

---

## Skip conditions — ESCALATE human

| Condizione                              | Motivo                                                      |
|----------------------------------------|--------------------------------------------------------------|
| `hard_floor_breaches` non vuoto         | BREAK-GLASS richiesto, human judgment (security/compliance) |
| `is_bot_pr == True`                     | Bot (Dependabot/Renovate) non usa DevForge                  |
| `decision == SEVERELY_DEGRADED`         | Tooling rotto, fix infra prima                              |
| Action `kind == "unknown"`              | Reason format ignoto, escalate per safety                   |
| Working tree dirty pre-loop             | Rischio commit accidentale -> abort                          |

---

## Algorithm (pseudo-Python)

```python
def auto_fix_loop(
    repo_root: Path,
    sha: str,
    max_iter: int = 5,
    token_budget: int = 200_000,
):
    """Loop di remediation. Sequenziale, no concurrent sub-skill."""
    iter_count = 0
    tokens_consumed = 0
    last_reasons_set: frozenset[str] | None = None

    while iter_count < max_iter and tokens_consumed < token_budget:
        # 1. Read evidence corrente
        evidence = evidence_from_json(
            read_json(repo_root / ".claude/review-evidence" / f"{sha}.json")
        )

        # 2. Skip conditions (escalate -> exit loop)
        if should_escalate(evidence):
            return {"status": "ESCALATED", "reason": skip_reason(evidence)}

        # 3. Parse block_reasons -> FixAction[]
        actions = parse_block_reasons(evidence)
        if not actions:
            return {"status": "SUCCESS_AUTO_APPROVE", "iters": iter_count}

        # 4. Unknown reason -> escalate (no sub_skill mapping)
        if actions[0].kind == "unknown":
            return {"status": "ESCALATED", "reason": "unknown_block_reason"}

        # 5. Oscillation guard — stesso set block_reasons 2 iter consecutivi
        current_set = frozenset(evidence.verdict.block_reasons)
        if last_reasons_set is not None and current_set == last_reasons_set:
            return {"status": "ESCALATED", "reason": "oscillation_detected"}
        last_reasons_set = current_set

        # 6. Dispatch sub-skill (highest priority action first)
        action = actions[0]
        Skill(skill=action.sub_skill, args=action.prompt)  # ADR-7 dynamic prompt

        # 7. Subagent commits -> nuovo SHA HEAD
        sha = git_rev_parse_head()

        # 8. Re-run hook (compute new evidence)
        run_bash("hooks/review-evidence")

        # 9. Accumula token usage (rough est. via Claude API)
        tokens_consumed += estimate_iter_tokens()
        iter_count += 1

    if iter_count >= max_iter:
        return {"status": "MAX_ITER_EXCEEDED", "iters": iter_count}
    return {"status": "TOKEN_BUDGET_EXCEEDED", "tokens": tokens_consumed}
```

### Dispatch tabella (MVP — 2 pattern)

| `block_reason` format                  | `kind`     | priority | Sub-skill            |
|----------------------------------------|------------|----------|----------------------|
| `coverage_below_threshold:X<Y`         | `coverage` | 2        | `siae-tdd`           |
| `lint_errors:N>M`                      | `lint`     | 1        | `siae-code-standards`|
| (out-of-scope MVP) `complexity_max:X>Y`| TODO       | TODO     | `siae-tdd` refactor  |
| (out-of-scope MVP) `drift_severity:high`| TODO      | TODO     | `siae-brainstorming` |
| (out-of-scope MVP) `ci_critical:N>M`   | TODO       | TODO     | `siae-debugging`     |

Priority lower = applied first. Lint prima di coverage (small surface ->
basso blast radius).

---

## Limiti operativi

- **Max iter:** 5 (hard cap, no override)
- **Token budget:** 200_000 token (`DEVFORGE_FIX_EVIDENCE_TOKEN_BUDGET`)
- **Esecuzione:** sequenziale (NO concurrent sub-skill — race su .git/index)
- **Oscillation guard:** stesso `frozenset(block_reasons)` per 2 iter
  consecutivi -> escalate (memory `feedback_*` su fix oscillatorio)
- **Working tree:** deve essere pulito a inizio loop, ogni iter chiude con
  commit del subagent
- **Idempotenza:** ogni iter parte da un SHA diverso (HEAD aggiornato)

---

## Vincoli

1. **NON modificare file direttamente** — invoca solo sub-skill via
   `Skill tool`. Il subagent fa il commit reale.
2. **NON pushare** — solo commit locali. La PR viene aggiornata fuori da
   questa skill (workflow utente).
3. **ESCALATE quando human judgment serve:** hard_floor, security
   critical, oscillation, unknown reason, SEVERELY_DEGRADED.
4. **Riusa skill esistenti** (`siae-tdd`, `siae-code-standards`) via ADR-7
   dynamic prompt — NON re-implementarle.
5. **Forward-compat:** reason format ignoto -> `FixAction(kind="unknown")`
   -> escalate. Mai crash silenzioso, mai drop silenzioso.

---

## Pre-flight check (manuale prima del loop)

```bash
# 1. Working tree pulito
git status --porcelain
# (empty) -> ok

# 2. Evidence presente per SHA corrente
SHA=$(git rev-parse HEAD)
test -f ".claude/review-evidence/${SHA}.json" || bash hooks/review-evidence

# 3. Decision deve essere BLOCK_REGRESSION
jq -r '.regression_verdict.decision' ".claude/review-evidence/${SHA}.json"
# expected: BLOCK_REGRESSION

# 4. hard_floor_breaches deve essere []
jq -r '.regression_verdict.hard_floor_breaches' ".claude/review-evidence/${SHA}.json"
# expected: []
```

Se uno qualsiasi dei check fallisce -> abort + escalate.

---

## Final report (a fine loop)

```
fix-evidence loop — SHA <final-sha>
  Status:        <AUTO_APPROVE | ESCALATED | MAX_ITER_EXCEEDED | TOKEN_BUDGET_EXCEEDED>
  Iters:         <N>/5
  Tokens:        <consumed>/200_000
  Final reasons: [<lista block_reasons al termine>]
  Sub-skill log: [<lista (iter, sub_skill, kind)>]
  Escalation:    <reason se ESCALATED, altrimenti none>
```

---

## Env var rilevanti

| Env var                                  | Default | Note |
|------------------------------------------|---------|------|
| `DEVFORGE_FIX_EVIDENCE_TOKEN_BUDGET`     | `200000`| Token budget loop (Claude API usage rough). |
| `DEVFORGE_FIX_EVIDENCE_MAX_ITER`         | `5`     | Hard cap iter (override richiede design review). |
| `DEVFORGE_FIX_EVIDENCE_AUTO`             | `1`     | **Default ON (BREAKING dal follow-up `feat/fix-evidence-auto-trigger`).** Auto-trigger fully-autonomous: hook `review-evidence` emette signal `AUTO_FIX_TRIGGER` in `additional_context` su `BLOCK_REGRESSION`, agent intercept e auto-invoca questa skill. Set `0` per disabilitare (opt-out kill-switch). |

---

## Auto-trigger pattern (fully-autonomous)

> **Quando si attiva:** sempre, di default (`DEVFORGE_FIX_EVIDENCE_AUTO=1`
> e' il default dal follow-up `feat/fix-evidence-auto-trigger`).
> **BREAKING change** vs v1.55 PR #244 dove il default era `0` (opt-in).

Pattern semantic (doc-level, NO bash enforcement) per chiudere il loop "zero
bug usando DevForge" senza azione utente manuale. DevForge e' opinionato
verso questo comportamento: ogni `BLOCK_REGRESSION` clean (no hard floor,
no bot, not degraded) tenta un auto-fix loop prima di propagare il block
all'utente.

### Signal canonico hook -> agent

Quando il hook `review-evidence` v2 emette `BLOCK_REGRESSION` E
`DEVFORGE_FIX_EVIDENCE_AUTO=1` E nessuna skip condition matcha, l'output JSON
contiene `additional_context` con marker grep-friendly:

```
AUTO_FIX_TRIGGER:/forge-fix-evidence:sha=<SHA>
```

### Comportamento agent (Claude Code)

**Quando vedi `AUTO_FIX_TRIGGER:/forge-fix-evidence` in tool output**, l'agent
DEVE:

1. **Intercept** il marker PRIMA di propagare il block all'utente.
2. **Invocare automaticamente** `Skill(skill="siae-fix-evidence", args="sha=<SHA>")`.
3. **Aspettare result** della skill (max 5 iter + token budget 200k).
4. **Se skill ritorna `AUTO_APPROVE`** → ri-prova action originale (`gh pr create`).
5. **Se `ESCALATED`** → mostra all'utente con context per intervento manuale.

Non chiedere conferma utente: il design e' opt-in via env, la conferma e'
gia' stata data attivando `DEVFORGE_FIX_EVIDENCE_AUTO=1`.

### Skip conditions hook-level (no signal emitted)

Identiche alle skill SKIP conditions:

| Condizione                                          | Hook check                                                            |
|-----------------------------------------------------|-----------------------------------------------------------------------|
| `regression_verdict.hard_floor_breaches` non vuoto  | `jq '.regression_verdict.hard_floor_breaches \| length'` > 0 -> skip |
| Bot PR (Dependabot / Renovate / github-actions)     | `GITHUB_ACTOR` matches pattern -> skip                                |
| `decision == SEVERELY_DEGRADED`                     | Diverso case branch, signal non raggiunto                             |
| `decision == BLOCK_HARD_FLOOR`                      | Diverso case branch, signal non raggiunto                             |

In tutte queste condizioni il hook **non emette il signal**: il block resta
ma senza auto-trigger, escalation human come da skill skip table.

### Vincoli di safety

1. **Signal e' ADDITIVO**, NOT al posto di `decision:block`. Block resta per
   safety; agent intercept `additional_context` -> auto-launch skill ->
   re-check block sulla nuova evidence.
2. **Default ON, opt-out kill-switch via env:** `DEVFORGE_FIX_EVIDENCE_AUTO=1`
   e' il default. Set `0` per disabilitare globalmente (vedi sezione
   "Opt-out" sotto). Skip conditions semantic (hard floor / bot /
   SEVERELY_DEGRADED) restano invariate.
3. **Hook resta single-file** (B3 PR #243 fix preserved): il signal e' una
   stringa nel campo `additional_context` esistente, non un nuovo hook.

### Opt-out

Per disabilitare globalmente l'auto-trigger (es. agent non-Claude-Code che
non riesce a fare intercept del marker, debug/troubleshooting, policy
aziendale "human in the loop" mandatoria):

```bash
# Opt-out per la sessione corrente
export DEVFORGE_FIX_EVIDENCE_AUTO=0

# Opt-out persistente
echo 'export DEVFORGE_FIX_EVIDENCE_AUTO=0' >> ~/.zshrc

# Opt-out one-shot
DEVFORGE_FIX_EVIDENCE_AUTO=0 gh pr create --title "..."
```

Con `=0` il hook non emette il marker `AUTO_FIX_TRIGGER`: `BLOCK_REGRESSION`
si comporta come pre-PR-#244 (block + reason, fix manuale via
`/forge-fix-evidence` o human review). Le skip conditions semantic restano
in vigore identicamente (hard floor / bot / SEVERELY_DEGRADED non emettono
mai il marker, anche con `=1`).

---

## Design + Plan

- **Design:** `docs/plans/2026-05-13-fix-evidence-auto-loop-design.md`
- **Predecessor:** `docs/plans/2026-05-13-review-evidence-v2-scoring-design.md`
- **Parser:** `lib/review_evidence/fix_parser.py`
- **Tests:** `tests/test_fix_parser.py`

## Out-of-scope MVP (follow-up PR-D)

- 3 atomic pattern aggiuntivi (`complexity_max`, `drift_severity`,
  `ci_critical`)
- Test E2E loop con mock subagent
- Auto-trigger su hook output (richiede hook change)
- Telemetria fix success rate
