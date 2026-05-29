# Task 17 — `predict_coverage.py` + sentinel display

**Goal:** Script che in Phase 3 genera `coverage-prediction.json` (line/branch attese post-Phase6/7, risk flags, confidence LOW/MEDIUM) e lo espone nel sentinel handshake PRIMA di Phase 4. Risolve gap R10 (l'utente scopre il branch gap solo a Phase 6, dopo ~10 min). Coefficienti empirici, confidence mai HIGH in v1.

**WS:** WS-4 · **Dipendenze:** Task 01 (branch pct), Task 05 (branch operators), Task 08 (batch schema).

## File coinvolti
- Crea: `skills/code-coverage/scripts/predict_coverage.py`
- Crea: `skills/code-coverage/scripts/tests/test_predict_coverage.py`
- Modifica: `skills/code-coverage/lib/sentinel-handshake.sh` (cmd_read: emette predicted_branch_after_phase7 + branch_risk)
- Modifica: `skills/code-coverage/SKILL.md` (Phase 3: invocazione predict_coverage.py)

## Step TDD

### Step 1 — Test fallente
Crea `skills/code-coverage/scripts/tests/test_predict_coverage.py`:

```python
import predict_coverage as pc


def test_predict_flags_branch_risk():
    out = pc.predict(size_class="VERY_LARGE", n_batches=3, total_loc=31000,
                     pre_line=59.08, pre_branch=42.31, target_line=70, target_branch=70)
    assert "predicted_branch_after_phase7" in out["predictions"]
    assert out["predictions"]["confidence"] in ("LOW", "MEDIUM")
    # branch target 70 alto + base 42 → rischio
    assert any(f["flag"] == "BRANCH_GAP_HIGH_RISK" for f in out["risk_flags"])


def test_no_risk_when_target_low():
    out = pc.predict(size_class="MEDIUM", n_batches=2, total_loc=8000,
                     pre_line=65, pre_branch=60, target_line=70, target_branch=60)
    assert out["risk_flags"] == [] or all(
        f["flag"] != "BRANCH_GAP_HIGH_RISK" for f in out["risk_flags"])


def test_confidence_low_without_branch_data():
    out = pc.predict(size_class="LARGE", n_batches=4, total_loc=20000,
                     pre_line=50, pre_branch=0, target_line=70, target_branch=60)
    assert out["predictions"]["confidence"] == "LOW"
```

### Step 2 — Verifica che fallisce
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_predict_coverage.py -v`
Output atteso: ImportError → 3 FAILED.

### Step 3 — Implementa `scripts/predict_coverage.py`

```python
#!/usr/bin/env python3
"""predict_coverage.py — prediction upfront di line/branch post Phase 6/7.

Coefficienti empirici (calibrati su 1 post-mortem). Confidence mai HIGH in v1.
Usage CLI: predict_coverage.py <repo>   (legge size/stack/user-choice/batch-plan)
Scrive .code-coverage/coverage-prediction.json
"""
import json
import math
import sys
from pathlib import Path

_LINE_GAIN = {"SMALL": 8, "MEDIUM": 6, "LARGE": 5, "VERY_LARGE": 4}
_BRANCH_GAIN = {"SMALL": 5, "MEDIUM": 4, "LARGE": 3, "VERY_LARGE": 2}
_BRANCH_OPS_PER_LOC = 0.015


def predict(size_class, n_batches, total_loc, pre_line, pre_branch,
            target_line, target_branch):
    est_ops = int(total_loc * _BRANCH_OPS_PER_LOC)
    line_gain = n_batches * _LINE_GAIN.get(size_class, 4)
    branch_gain = n_batches * _BRANCH_GAIN.get(size_class, 2)
    p6_line = min(95, pre_line + line_gain)
    p6_branch = min(95, pre_branch + branch_gain)
    max_iter = min(10, max(3, math.ceil(n_batches * 1.5))) if n_batches else 3
    p7_line = min(95, p6_line + max_iter * 1.5)
    p7_branch = min(95, p6_branch + max_iter * 2.5)

    risk_flags = []
    gap = target_branch - p7_branch
    if gap > 0:
        risk_flags.append({
            "flag": "BRANCH_GAP_HIGH_RISK",
            "description": f"Predicted branch after Phase 7 ({p7_branch:.1f}%) is "
                           f"{gap:.1f}pp below target ({target_branch}%).",
            "recommended_action": "branch-priority mode OR accept BEST_EFFORT",
        })

    if pre_branch == 0:
        conf, reason = "LOW", "No pre-existing branch data; LOC-only estimate"
    elif est_ops > 300:
        conf, reason = "LOW", f"High branch-operator density (~{est_ops})"
    else:
        conf, reason = "MEDIUM", "Pre-existing branch data available"

    return {
        "schema_version": "1.0",
        "inputs": {"size_class": size_class, "batch_count": n_batches,
                   "total_branch_operators_estimated": est_ops,
                   "pre_existing_line_pct": pre_line, "pre_existing_branch_pct": pre_branch,
                   "target_line": target_line, "target_branch": target_branch},
        "predictions": {
            "predicted_line_after_phase6": round(p6_line, 1),
            "predicted_branch_after_phase6": round(p6_branch, 1),
            "predicted_line_after_phase7": round(p7_line, 1),
            "predicted_branch_after_phase7": round(p7_branch, 1),
            "confidence": conf, "confidence_reason": reason,
        },
        "risk_flags": risk_flags,
    }


def main() -> None:
    repo = Path(sys.argv[1]).resolve()
    cc = repo / ".code-coverage"
    size = json.loads((cc / "size.json").read_text()) if (cc / "size.json").exists() else {}
    stack = json.loads((cc / "stack.json").read_text()) if (cc / "stack.json").exists() else {}
    uc = json.loads((cc / "user-choice.json").read_text()) if (cc / "user-choice.json").exists() else {}
    bp = json.loads((cc / "batch-plan.json").read_text()) if (cc / "batch-plan.json").exists() else {}
    out = predict(
        size_class=size.get("class", "MEDIUM"),
        n_batches=len(bp.get("batches", bp.get("pending_batches", []))),
        total_loc=int(size.get("loc", 0) or 0),
        pre_line=float(stack.get("pre_existing_coverage_pct", 0) or 0),
        pre_branch=float(stack.get("pre_existing_branch_pct", 0) or 0),
        target_line=float(uc.get("target_line", 70)),
        target_branch=float(uc.get("target_branch", 60)),
    )
    (cc / "coverage-prediction.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out["predictions"]))


if __name__ == "__main__":
    main()
```

### Step 4 — Verifica che passa
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_predict_coverage.py -v`
Output atteso: `3 passed`.

## Step 5 — Sentinel display + SKILL.md
In `lib/sentinel-handshake.sh` `cmd_read`, dopo gli altri `emit`, aggiungi (non-bloccante):
```python
import pathlib as _pl
_pred = _pl.Path(path).parent / "coverage-prediction.json"
if _pred.exists():
    try:
        _p = json.loads(_pred.read_text())
        emit("predicted_branch_after_phase7", _p["predictions"]["predicted_branch_after_phase7"])
        emit("branch_risk", _p["risk_flags"][0]["flag"] if _p.get("risk_flags") else "NONE")
    except Exception:
        pass
```
In `SKILL.md` Phase 3, dopo `plan_batches.py`, aggiungi:
```markdown
**Prediction:** `python3 skills/code-coverage/scripts/predict_coverage.py <repo>` →
coverage-prediction.json. Includi nel messaggio pre-Phase-4: "[prediction]
branch_p7=<Y>% confidence=<C> <risk_flag>". Non-bloccante: se fallisce, Phase 3 continua.
```

## Step 6 — Commit
```
git add skills/code-coverage/scripts/predict_coverage.py skills/code-coverage/scripts/tests/test_predict_coverage.py skills/code-coverage/lib/sentinel-handshake.sh skills/code-coverage/SKILL.md
git commit -m "feat(code-coverage): upfront coverage prediction + sentinel display"
```

## Criteri di accettazione
- [ ] VERY_LARGE base branch 42 / target 70 → flag `BRANCH_GAP_HIGH_RISK`.
- [ ] `pre_branch=0` → confidence LOW.
- [ ] target branch basso e raggiungibile → nessun flag rischio.
- [ ] `coverage-prediction.json` scritto; sentinel emette `predicted_branch_after_phase7`/`branch_risk`.
- [ ] Invocazione non-bloccante in Phase 3.
