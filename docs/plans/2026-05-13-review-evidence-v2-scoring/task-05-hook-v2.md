# Task 05 — Hook bash v2 extension (5 decision branch)

**SP:** 2.0 · **AC mappati:** AC #1, AC #13 · **Dipendenze:** Task 01 (schema enum) · **Wave:** 1b

## Goal

Estendere `hooks/review-evidence` esistente con logica v2 per parsare `evidence.regression_verdict.decision` (5 valori) e emettere il `decision/additional_context` JSON corretto per ogni branch. Mantiene single-file pattern (B3 fix). Zero regression sul flow v1 (cache lookup, dirty flag, bypass).

## File coinvolti

**Modificare:**
- `hooks/review-evidence`

**Creare:**
- `tests/test_review_evidence_hook_v2.py`

## Step TDD

### Step 1 — Test fallente

`tests/test_review_evidence_hook_v2.py`:

```python
"""Tests for hook bash v2 — 5 decision branch logic."""
import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "hooks" / "review-evidence"


def _init_repo(tmp_path):
    sp = subprocess.run
    sp(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sp(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    sp(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    sp(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    sp(["git", "config", "tag.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("x")
    sp(["git", "add", "."], cwd=tmp_path, check=True)
    sp(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)


def _write_evidence(tmp_path, sha, decision, reason="test reason"):
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True)
    evidence = {
        "schema_version": "2.0",
        "sha": sha, "branch": "feat/x", "computed_at": "now",
        "dirty_tree": False, "base_branch": "main", "stack_detected": [],
        "metrics": {}, "spec_drift": None,
        "verdict": {"block": decision.startswith("BLOCK"),
                     "block_reasons": [reason], "warnings": []},
        "regression_verdict": {
            "block_dimensions": [], "warn_dimensions": [],
            "improved_dimensions": [], "hard_floor_breaches": [],
            "decision": decision, "reason": reason,
        },
        "current_scores": {"security": 80, "quality": 75, "coverage": 70,
                            "spec_compliance": 85, "discipline": 90, "overall": 80,
                            "weights_used": {"security": 0.30, "quality": 0.20,
                                              "coverage": 0.20, "spec_compliance": 0.15,
                                              "discipline": 0.15},
                            "missing_components": []},
    }
    (ev_dir / f"{sha}.json").write_text(json.dumps(evidence))
    return ev_dir


def _run_hook(stdin_obj, cwd):
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(stdin_obj),
        capture_output=True, text=True, env=env, cwd=str(cwd), timeout=20,
    )


def test_decision_auto_approve_emits_advisory(tmp_path):
    _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    _write_evidence(tmp_path, sha, "AUTO_APPROVE")
    p = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                    "command": "gh pr create --title x"}, tmp_path)
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") != "block"
    assert "AUTO_APPROVE" in out.get("additional_context", "")


def test_decision_block_hard_floor_blocks(tmp_path):
    _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    _write_evidence(tmp_path, sha, "BLOCK_HARD_FLOOR", reason="security < 60")
    p = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                    "command": "gh pr create --title x"}, tmp_path)
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") == "block"
    assert "hard floor" in out.get("reason", "").lower()
    assert "BREAK-GLASS" in out.get("reason", "")


def test_decision_block_regression_blocks_overridable(tmp_path):
    _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    _write_evidence(tmp_path, sha, "BLOCK_REGRESSION", reason="coverage regressed -8pp")
    p = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                    "command": "gh pr create --title x"}, tmp_path)
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") == "block"
    assert "regression" in out.get("reason", "").lower()


def test_decision_reviewer_handoff_advisory_no_block(tmp_path):
    _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    _write_evidence(tmp_path, sha, "REVIEWER_HANDOFF")
    p = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                    "command": "gh pr create --title x"}, tmp_path)
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") != "block"
    assert "reviewer" in out.get("additional_context", "").lower()


def test_decision_severely_degraded_skips_block(tmp_path):
    """F2 iter2 fix: SEVERELY_DEGRADED = tooling broken, skip hard floor."""
    _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    _write_evidence(tmp_path, sha, "SEVERELY_DEGRADED")
    p = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                    "command": "gh pr create --title x"}, tmp_path)
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") != "block"
    assert "DEGRADED" in out.get("additional_context", "") or "degraded" in out.get("additional_context", "")


def test_v1_evidence_no_decision_field_still_works(tmp_path):
    """No regression: v1 evidence (no regression_verdict) → fallback to v1 logic."""
    _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True)
    v1_evidence = {
        "schema_version": "1.0", "sha": sha, "branch": "x",
        "computed_at": "now", "dirty_tree": False, "base_branch": "main",
        "stack_detected": [], "metrics": {}, "spec_drift": None,
        "verdict": {"block": False, "block_reasons": [], "warnings": []},
    }
    (ev_dir / f"{sha}.json").write_text(json.dumps(v1_evidence))
    p = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                    "command": "gh pr create --title x"}, tmp_path)
    assert p.returncode == 0
    # v1 fallback: emit advisory, no block
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") != "block"
```

### Step 2 — Esegui (fail su decision branch nuovi)

```bash
python3 -m pytest tests/test_review_evidence_hook_v2.py -v
```

**Output atteso:** alcuni FAIL su BLOCK_HARD_FLOOR / SEVERELY_DEGRADED (hook v1 non li gestisce).

### Step 3 — Estendi hook bash

In `hooks/review-evidence`, **dopo** la lettura cache evidence e verifica `BLOCK`, **prima** del `additional_context` emit, aggiungi:

```bash
# ── v2 — Parse regression_verdict.decision (5 valori) ──────────────
DECISION=""
if [ -f "$EVIDENCE_FILE" ]; then
    DECISION=$(jq -r '.regression_verdict.decision // ""' "$EVIDENCE_FILE" 2>/dev/null || echo "")
fi
REGRESSION_REASON=$(jq -r '.regression_verdict.reason // ""' "$EVIDENCE_FILE" 2>/dev/null || echo "")

case "$DECISION" in
    BLOCK_HARD_FLOOR)
        # NON-OVERRIDABLE by reviewer agent
        ESCAPED_REASON=$(echo "$REGRESSION_REASON" | sed 's/"/\\"/g')
        cat <<JSON
{"decision":"block","reason":"review-evidence v2: hard floor breach — ${ESCAPED_REASON}. NOT overridable by reviewer. Admin BREAK-GLASS: commit msg 'BREAK-GLASS: <jira>' + 2 reviewer + post-mortem 48h."}
JSON
        devforge_log "evidence_v2_block_hard_floor" "warn" "{\"sha\":\"${SHA}\",\"reason\":\"$ESCAPED_REASON\"}" 2>/dev/null || true
        exit 0
        ;;
    BLOCK_REGRESSION)
        ESCAPED_REASON=$(echo "$REGRESSION_REASON" | sed 's/"/\\"/g')
        cat <<JSON
{"decision":"block","reason":"review-evidence v2: regression block — ${ESCAPED_REASON}. Override: touch ~/.claude/.devforge-skip-evidence (tracked, abuse 5/day)."}
JSON
        exit 0
        ;;
    REVIEWER_HANDOFF)
        cat <<JSON
{"additional_context":"review-evidence v2: regression in warn zone — code-reviewer agent will gatekeep. ${REGRESSION_REASON}"}
JSON
        exit 0
        ;;
    SEVERELY_DEGRADED)
        MISSING=$(jq -r '.current_scores.missing_components | join(",")' "$EVIDENCE_FILE" 2>/dev/null || echo "unknown")
        cat <<JSON
{"additional_context":"review-evidence v2: SEVERELY_DEGRADED — DevForge runners parzialmente non disponibili: ${MISSING}. Hard floor SKIP."}
JSON
        exit 0
        ;;
    AUTO_APPROVE)
        SCORE=$(jq -r '.current_scores.overall // "n/a"' "$EVIDENCE_FILE" 2>/dev/null)
        cat <<JSON
{"additional_context":"review-evidence v2: AUTO_APPROVE (overall=${SCORE})."}
JSON
        exit 0
        ;;
    "")
        # No regression_verdict field → v1 evidence, fall through to v1 logic
        ;;
esac

# ── v1 fallback logic stays unchanged below ──────────────────
```

### Step 4 — Run + commit

```bash
python3 -m pytest tests/test_review_evidence_hook_v2.py -v
# 6 passed
python3 -m pytest tests/ -q  # full suite no regression
# 158 + 6 = 164 atteso

git add hooks/review-evidence tests/test_review_evidence_hook_v2.py
git commit -m "feat(review-evidence-v2): hook bash 5 decision branch (#task-05)"
```

## Criteri di accettazione

- [ ] Hook gestisce 5 decision values esplicitamente
- [ ] `BLOCK_HARD_FLOOR` emit decision:block con "NOT overridable by reviewer" + BREAK-GLASS note
- [ ] `BLOCK_REGRESSION` emit decision:block overridable via state file
- [ ] `REVIEWER_HANDOFF` emit additional_context (no block)
- [ ] `SEVERELY_DEGRADED` emit additional_context (no block, no hard floor enforcement)
- [ ] `AUTO_APPROVE` emit advisory con overall score
- [ ] Hook chain v1 unchanged (no regression v1 158 test PASS)
- [ ] 6 nuovi test PASS
