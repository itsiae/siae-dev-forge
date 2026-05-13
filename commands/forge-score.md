---
name: forge-score
description: On-demand: compute review-evidence v2 score card for current SHA + display human-readable markdown. No block, advisory only.
allowed-tools: Bash, Read
---

# /forge-score — Review Evidence v2 Score Card on-demand

Calcola lo score card v2 per il SHA corrente (5 dimensioni + overall 0-100)
e stampa il risultato in markdown copy-paste pronto per `gh pr comment`.
Solo advisory: non blocca push/PR, complementa `/forge-evidence` (v1 hook).

## Cosa fa

1. Detect SHA corrente via `git rev-parse HEAD`
2. Carica `.claude/review-evidence/<sha>.json` (se gia' calcolato da v1 hook)
   OR triggera compute on-demand via `hooks/review-evidence`
3. Calcola gli score 5-dim (security/quality/coverage/spec/discipline)
   + overall weighted via `lib/review_evidence/scoring.py`
4. Confronta vs baseline (`baseline_cache` S3 + local fallback) e produce
   `RegressionVerdict.decision` (5 branch enum)
5. Stampa score card markdown 5 dim + overall + decision + warnings
6. Stampa `BREAK-GLASS:` instructions se score sotto hard floor

## Quando usarlo

- **Prima di `gh pr create`** per anticipare il verdict v2 e fixare regressioni
  prima che `code-reviewer` Step 0.6 le blocchi
- **Debug:** capire perche' un PR e' stato bloccato (decision branch +
  block reasons + delta vs baseline)
- **Post-merge baseline visibility:** verifica come la PR appena mergiata
  sposta la baseline per i successivi

## Uso

```bash
# Score on-demand del SHA corrente
bash hooks/review-evidence
python3 -m lib.review_evidence.cli score

# Oppure tramite skill (alias)
# /forge-score
```

## 5 decision branch (output `regression_verdict.decision`)

| Decision | Significato | Reviewer action |
|---|---|---|
| `AUTO_APPROVE` | overall >= 80, no regression > budget warn | Advisory summary, no block |
| `REVIEWER_HANDOFF` | overall 55-80 oppure delta in warn budget | Reviewer agent rivaluta full 6-punti |
| `BLOCK_REGRESSION` | delta scende sotto `hard_block_budget` (security/coverage/etc.) | BLOCK — fix regressione |
| `BLOCK_HARD_FLOOR` | dim sotto `hard_floors.min_dim` o overall sotto `hard_floors.overall` | BLOCK — NON-overridable da reviewer agent (solo admin BREAK-GLASS) |
| `SEVERELY_DEGRADED` | < 2 dim disponibili (tooling rotto) | BLOCK fail-closed — fix tooling prima di re-run |

## Output esempio

```
review-evidence v2 — SHA abc12345

| Dim          | Score | Delta vs baseline |
|---|---|---|
| Security     | 85    | +2                |
| Quality      | 72    | -3 (warn)         |
| Coverage     | 68    | -5 (block)        |
| Spec         | 90    | +0                |
| Discipline   | 80    | +0                |
| **Overall**  | **78**| **-1**            |

Decision: BLOCK_REGRESSION
Reason: coverage regressed -5pp (hard_block budget: -5).
Override: touch ~/.claude/.devforge-skip-evidence (tracked, abuse 5/day).
```

Hard floor block:

```
review-evidence v2 — SHA abc12345

| Dim          | Score | Delta vs baseline |
|---|---|---|
| Security     | 45    | -10               |
| ...          |       |                   |
| **Overall**  | **52**| **-8**            |

Decision: BLOCK_HARD_FLOOR
Reason: security=45 < hard_floors.security=60 (NON-overridable da reviewer agent).
Override: admin only — commit message must contain `BREAK-GLASS: SDLC-NNNN`
          (cfr. DEVFORGE_BREAK_GLASS_REGEX).
```

## Bypass / override

```bash
# Reviewer agent advisory override (NON funziona su BLOCK_HARD_FLOOR)
touch ~/.claude/.devforge-skip-evidence

# Admin break-glass (commit message)
git commit -m "fix: emergency rollback

BREAK-GLASS: SDLC-9999 incident response, override hard_floor"
```

Il break-glass e' tracked e logga `break_glass_invoked` in `~/.claude/devforge-activity.jsonl`.

## Env var rilevanti

Vedi [`hooks/ENV_VARS.md`](../hooks/ENV_VARS.md) sezione "Review Evidence v2 — Scoring".
Riassunto override piu' usati:

```bash
export DEVFORGE_SCORING_V2_ENABLED=1            # GA in v1.55+, kill-switch
export DEVFORGE_BASELINE_S3_BUCKET=<override>   # default: itsiae-review-evidence-baseline-prod
export DEVFORGE_BASELINE_S3_REGION=<region>     # default: eu-west-1
export DEVFORGE_BASELINE_LOCAL_DIR=<path>       # default: ~/.claude/review-evidence-baseline-local
export DEVFORGE_BREAK_GLASS_REGEX='BREAK-GLASS:\s+\w+-\d+'
```

## Differenza vs `/forge-evidence` (v1)

| Aspetto | `/forge-evidence` (v1) | `/forge-score` (v2) |
|---|---|---|
| Output | block:bool + reasons[] | ScoreCard 5-dim + overall + 5 decision branch |
| Baseline | n/a | S3 cache + local fallback (`itsiae-review-evidence-baseline-prod`) |
| Reviewer agent | Step 0.5 evidence-loading | Step 0.6 gatekeeper (NON-overridable hard floor) |
| Skill scope | Compute deterministico | Render score card umano + decision narrative |

Le due skill **coesistono**: v2 e' additive su v1.

## Design + Plan

- **Design:** `docs/plans/2026-05-13-review-evidence-v2-scoring-design.md`
- **Plan:** `docs/plans/2026-05-13-review-evidence-v2-scoring/`
- **Template config:** `docs/templates/.devforge-scores.yml`
- **JSON Schema:** `docs/schemas/devforge-scores.schema.json`
