# Task 12 — Reviewer agent Step 0.6 (5 decision branch)

**SP:** 1.5 · **AC mappati:** AC #12, CRITICAL F1 · **Dipendenze:** Task 11 · **Wave:** 3

## Goal

Aggiungere "Step 0.6 — Gatekeeper Logic (v2 scoring)" a `agents/code-reviewer.md` con 5 decision branch espliciti. Reviewer NON può mai overrule hard floor breach (F1 CRITICAL). Auto-approve emette comunque review summary advisory (W2 fix).

## File coinvolti

**Modificare:**
- `agents/code-reviewer.md`

**Creare:**
- `tests/test_review_evidence_reviewer_step_06.py`

## Step TDD

### Step 1 — Test contract

```python
"""Tests for agents/code-reviewer.md Step 0.6 (v2 scoring gatekeeper)."""
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]
CODE_REVIEWER = REPO_ROOT / "agents" / "code-reviewer.md"


def test_step_0_6_section_exists():
    content = CODE_REVIEWER.read_text()
    assert "Step 0.6" in content
    assert "Gatekeeper" in content or "gatekeeper" in content


def test_step_0_6_lists_5_decision_branch():
    """AC #12: 5 decision values explicit."""
    content = CODE_REVIEWER.read_text()
    for decision in ["AUTO_APPROVE", "REVIEWER_HANDOFF", "BLOCK_HARD_FLOOR",
                       "BLOCK_REGRESSION", "SEVERELY_DEGRADED"]:
        assert decision in content, f"Decision branch {decision} missing"


def test_step_0_6_hard_floor_non_overridable():
    """CRITICAL F1: reviewer can NEVER override hard floor."""
    content = CODE_REVIEWER.read_text()
    # Must explicitly state non-overridable
    assert re.search(r"NON[\s-]+overridable|cannot.*overrule|NEVER.*override",
                       content, re.IGNORECASE)


def test_step_0_6_auto_approve_advisory():
    """W2 fix: AUTO_APPROVE emit review summary anyway."""
    content = CODE_REVIEWER.read_text()
    assert "advisory" in content.lower()
    assert "summary" in content.lower()


def test_step_0_6_break_glass_documented():
    """Document admin BREAK-GLASS override path."""
    content = CODE_REVIEWER.read_text()
    assert "BREAK-GLASS" in content
```

### Step 2 — Esegui (fail su Step 0.6 mancante)

```bash
python3 -m pytest tests/test_review_evidence_reviewer_step_06.py -v
```

### Step 3 — Aggiungi Step 0.6 a code-reviewer.md

Inserisci **dopo** "Step 0.5 — Load Pre-Computed Evidence" (v1 esistente), prima di "## PRIMA DELLA REVIEW":

```markdown
## Step 0.6 — Gatekeeper Logic (v2 scoring)

Schema evidence v2 estende v1 con `regression_verdict.decision` (5 valori).
Dopo aver caricato evidence in Step 0.5, controlla `decision`:

### Decision branches

| Decision | Behavior | Override |
|---|---|---|
| `AUTO_APPROVE` | Emit **review summary advisory** (no full 6-point review) — score card markdown + 1-line judgment qualitativo. Decision finale: approve. **W2 fix:** anche su AUTO_APPROVE il reviewer genera un comment summary (no buchi naming/intent). | No override needed (already pass) |
| `BLOCK_HARD_FLOOR` | Emit `{"decision": "block"}` immediatamente. **NON-OVERRIDABLE.** Reviewer NON può approvare. | Solo admin BREAK-GLASS: commit message contains `BREAK-GLASS: <jira-id>` + 2 reviewer approvals + post-mortem entro 48h |
| `BLOCK_REGRESSION` | Emit `{"decision": "block"}`. Reasons in `regression_verdict.block_dimensions`. | Override via `touch ~/.claude/.devforge-skip-evidence` (tracked, abuse 5/day) |
| `REVIEWER_HANDOFF` | Procedi con **review qualitativa full 6-point** (standard SIAE). Verdict finale: `APPROVED` / `REJECTED`. | N/A (reviewer È il gatekeeper qui) |
| `SEVERELY_DEGRADED` | Tooling parzialmente broken (runner missing, AWS unreachable). **Skip hard floor enforcement** (dev non punito). Procedi con review qualitativa standard + nota in commento PR: "DevForge runners parzialmente non disponibili: <missing_components>". | N/A |

### Rules

- **CRITICAL F1: Reviewer can NEVER override `hard_floor_breaches`.** Solo admin BREAK-GLASS via repo flag. Auto-approve su hard_floor = bug critico, segnala immediatamente.
- **`AUTO_APPROVE` (W2 fix):** anche se la pipeline passa automaticamente, emetti uno **score card summary** in PR comment con:
  - Tabella 5 dim score + overall
  - 1-line qualitative judgment (es. "Naming consistente, intent chiaro, no smell trovati")
  - Improvement opportunities (se score < 90 su qualche dim) come advisory non-blocking
- **`SEVERELY_DEGRADED`:** la review qualitativa procede ma il punteggio NON è hard-enforced. Il dev non è punito per tool broken.
- **`REVIEWER_HANDOFF`:** la full review 6-point è IL gating mechanism. Decisione finale del reviewer = decisione finale del pipeline.

### Output

Reviewer emette sempre uno dei seguenti formati:
- `{"decision": "block", "reason": "<text>"}` → blocca push
- `{"decision": "approve", "reason": "<text>"}` → approva
- `{"decision": "review_required", "reason": "<text>"}` → richiede ulteriore review umana (raro)

Score card markdown sempre incluso in PR comment via `gh pr comment` (pattern siae-gh-actions).
```

### Step 4 — Run + commit

```bash
python3 -m pytest tests/test_review_evidence_reviewer_step_06.py -v
# 5 passed

git add agents/code-reviewer.md tests/test_review_evidence_reviewer_step_06.py
git commit -m "feat(review-evidence-v2): reviewer agent Step 0.6 5 decision branch + F1 non-overridable (#task-12)"
```

## Criteri di accettazione

- [ ] Sezione "Step 0.6" presente in `agents/code-reviewer.md`
- [ ] 5 decision branch enumerati esplicitamente
- [ ] **CRITICAL F1:** hard floor non-overridable rule esplicita
- [ ] **W2 fix:** AUTO_APPROVE → review summary advisory emit
- [ ] SEVERELY_DEGRADED branch documentato (no hard floor enforcement)
- [ ] BREAK-GLASS path documentato (commit msg + 2 reviewer + post-mortem)
- [ ] 5 test contract PASS
- [ ] No regression v1
