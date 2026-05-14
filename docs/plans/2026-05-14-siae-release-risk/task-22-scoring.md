# Task 22 — scoring.py max 36

**Stato:** [DONE]
**SP:** 1 Human / 0.5 Augmented
**Dipendenze:** task-04

## Goal

Implementare `lib/release_risk/scoring.py` con `compute_score(criteria) -> ScoreCard` + assign level/decision. Max 36, soglie 0-4/5-9/10-14/15+.

## File coinvolti

- Create: `lib/release_risk/scoring.py`

## Step

### Step 1 — Write scoring.py

Write `lib/release_risk/scoring.py`:
```python
"""Compute total score + assign level/decision."""
from lib.release_risk.schema import CriterionResult, ScoreCard, Level, Decision

MAX_SCORE = 36
LEVEL_THRESHOLDS = [
    (4, "LOW", "GO"),
    (9, "MEDIUM", "GO_WITH_MONITORING"),
    (14, "HIGH", "POSTPONE_WITHOUT_TL"),
    (999, "CRITICAL", "NO_GO_WITHOUT_CAB"),
]
SECURITY_FOLLOWUP_THRESHOLD_HIGH = 10


def compute_score(criteria: list[CriterionResult]) -> ScoreCard:
    total = sum(c.weight for c in criteria if c.status == "YES")
    total = max(0, total)  # clamp negative aggregato a 0
    partial = any(c.status == "REQUIRES_INPUT" for c in criteria)

    level: Level = "LOW"
    decision: Decision = "GO"
    for threshold, lvl, dec in LEVEL_THRESHOLDS:
        if total <= threshold:
            level, decision = lvl, dec
            break

    followups = []
    c17 = next((c for c in criteria if c.id == 17), None)
    if c17 and "suggested_followup_security=True" in str(c17.evidence):
        followups.append("siae-security")

    rationale_parts = [f"score={total}/{MAX_SCORE}", f"level={level}"]
    yes_criteria = [c.id for c in criteria if c.status == "YES"]
    if yes_criteria:
        rationale_parts.append(f"yes_criteria={yes_criteria}")
    if partial:
        rationale_parts.append("partial=True (some criteria REQUIRES_INPUT)")

    return ScoreCard(
        total_score=total,
        level=level,
        decision=decision,
        decision_rationale=" | ".join(rationale_parts),
        suggested_followups=followups,
        partial=partial,
    )
```

### Step 2 — Verifica

Run: `python3 -c "from lib.release_risk.scoring import compute_score, MAX_SCORE; print(MAX_SCORE)"` → `36`

### Step 3 — Commit

```bash
git add lib/release_risk/scoring.py
git commit -m "feat(release-risk): scoring compute_score + level/decision assignment (max 36)"
```

## Criteri di accettazione

- [ ] `MAX_SCORE = 36`
- [ ] LEVEL_THRESHOLDS = 0-4/5-9/10-14/15+
- [ ] Suggested followup `siae-security` se Criterion 17 evidence contiene flag
- [ ] Partial=True se ≥1 REQUIRES_INPUT
- [ ] Commit eseguito
