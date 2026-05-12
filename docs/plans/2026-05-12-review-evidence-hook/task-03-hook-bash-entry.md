# Task 03 — Hook bash entry point + hooks.json + bypass state file

**SP:** 1.5 · **AC mappati:** AC #1, AC #6 · **Dipendenze:** nessuna · **Wave:** 1

## Goal

Creare `hooks/review-evidence` (bash script extensionless) che è entry point dei 3 trigger (PreToolUse Bash su `gh pr create|edit`, PostToolUse Bash su commit, Skill `/forge-evidence`). Implementare bypass via state file `~/.claude/.devforge-skip-evidence` (env var come fallback). Registrare in `hooks/hooks.json`.

## File coinvolti

**Creare:**
- `hooks/review-evidence` (bash, eseguibile)
- `tests/test_review_evidence_hook.py`

**Modificare:**
- `hooks/hooks.json` (aggiungere 2 voci: PreToolUse Bash dopo `pr-gate`, PostToolUse Bash dopo `post-commit-review`)

## Step TDD

### Step 1 — Scrivi test fallente

`tests/test_review_evidence_hook.py`:

```python
"""Integration tests for hooks/review-evidence (bash entry point)."""
import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
HOOK = REPO_ROOT / "hooks" / "review-evidence"


def _run_hook(stdin_json: dict, env: dict | None = None) -> tuple[int, str, str]:
    full_env = os.environ.copy()
    full_env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    if env:
        full_env.update(env)
    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(stdin_json),
        capture_output=True,
        text=True,
        env=full_env,
        timeout=20,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_hook_is_executable():
    assert HOOK.exists()
    assert os.access(HOOK, os.X_OK)


def test_hook_emits_empty_json_on_non_matching_command():
    """Without hook_event_name + with non-matching command, hook MUST be no-op.
    The default branch (`*) TRIGGER=skill_or_manual`) only fires when
    hook_event_name is explicitly absent from PreToolUse/PostToolUse; here we
    pass hook_event_name=PreToolUse with a non-`gh pr` command, so TRIGGER=other
    and exit early with {}."""
    rc, out, _ = _run_hook({
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "command": "echo hello",
    })
    assert rc == 0
    parsed = json.loads(out or "{}")
    assert parsed == {}


def test_hook_blocks_on_gh_pr_edit_with_blocking_evidence(tmp_path):
    """gh pr edit must trigger the same PreToolUse blocking path as gh pr create."""
    import subprocess as _sp
    _sp.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    _sp.run(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    _sp.run(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("x")
    _sp.run(["git", "add", "."], cwd=tmp_path, check=True)
    _sp.run(["git", "commit", "-m", "x"], cwd=tmp_path, check=True, capture_output=True)
    sha = _sp.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True)
    blocked = {"schema_version": "1.0", "sha": sha, "verdict": {"block": True,
              "block_reasons": ["coverage_below_threshold:45<60"], "warnings": []}}
    (ev_dir / f"{sha}.json").write_text(json.dumps(blocked))

    rc, out, _ = _run_hook({
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "command": "gh pr edit 123 --add-label review-ready",
    })
    parsed = json.loads(out or "{}")
    assert parsed.get("decision") == "block"


def test_hook_bypass_state_file(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    skip_file = tmp_path / ".claude" / ".devforge-skip-evidence"
    skip_file.parent.mkdir(parents=True)
    skip_file.write_text("")
    rc, out, _ = _run_hook({"command": "gh pr create --title x"},
                            env={"HOME": str(tmp_path)})
    parsed = json.loads(out)
    assert rc == 0
    # bypassed: no block decision, just advisory
    assert parsed.get("decision") != "block"


def test_hook_bypass_env_var_fallback():
    rc, out, _ = _run_hook(
        {"command": "gh pr create --title x"},
        env={"DEVFORGE_SKIP_EVIDENCE": "1"},
    )
    parsed = json.loads(out)
    assert rc == 0
    assert parsed.get("decision") != "block"


def test_hook_registered_in_hooks_json():
    hooks_json = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())
    # PreToolUse Bash chain contains review-evidence
    pre_bash = [
        h for entry in hooks_json["hooks"]["PreToolUse"]
        if entry["matcher"] == "Bash"
        for h in entry["hooks"]
    ]
    assert any("review-evidence" in h["command"] for h in pre_bash)
    # PostToolUse Bash chain contains review-evidence
    post_bash = [
        h for entry in hooks_json["hooks"]["PostToolUse"]
        if entry["matcher"] == "Bash"
        for h in entry["hooks"]
    ]
    assert any("review-evidence" in h["command"] for h in post_bash)
```

### Step 2 — Esegui (fallisce)

```bash
pytest tests/test_review_evidence_hook.py -v
```

**Output atteso:** tutti FAIL — file non esiste.

### Step 3 — Implementa hooks/review-evidence

```bash
#!/usr/bin/env bash
# review-evidence — pre-compute deterministic quality signals for code review.
# ─────────────────────────────────────────────────────────────────
# Hook:     review-evidence
# Eventi:   PreToolUse (Bash gh pr create|edit) — sync, can BLOCK
#           PostToolUse (Bash, commit detected) — async, warms cache
#           Skill   (/forge-evidence)            — on-demand, sync, human-readable
# Formato:  additional_context (standard DevForge)
# ─────────────────────────────────────────────────────────────────

set -euo pipefail
export DEVFORGE_CURRENT_HOOK="review-evidence"

HOOK_INPUT=$(cat)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck disable=SC1091
source "${PLUGIN_ROOT}/lib/logger.sh" 2>/dev/null || true
devforge_init_session 2>/dev/null || true

# ── Bypass: state file primario, env var fallback ──────────────
SKIP_STATE_FILE="${HOME}/.claude/.devforge-skip-evidence"
if [ -f "$SKIP_STATE_FILE" ] || [ "${DEVFORGE_SKIP_EVIDENCE:-0}" = "1" ]; then
    devforge_log "evidence_bypass_used" "info" \
        "{\"source\":\"$([ -f "$SKIP_STATE_FILE" ] && echo state_file || echo env_var)\"}" 2>/dev/null || true
    echo '{}'
    exit 0
fi

# ── Determine trigger source ───────────────────────────────────
TOOL_NAME=$(echo "$HOOK_INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)
TOOL_COMMAND=$(echo "$HOOK_INPUT" | jq -r '.command // .tool_input.command // empty' 2>/dev/null || true)
HOOK_EVENT_NAME=$(echo "$HOOK_INPUT" | jq -r '.hook_event_name // empty' 2>/dev/null || true)

TRIGGER="other"
IS_BLOCKING=0
case "$HOOK_EVENT_NAME" in
    PreToolUse)
        if [[ "$TOOL_COMMAND" =~ gh[[:space:]]+pr[[:space:]]+(create|edit) ]]; then
            TRIGGER="pre_pr"
            IS_BLOCKING=1
        fi
        ;;
    PostToolUse)
        # We're chained after post-commit-review; trigger only on real commit
        if [[ "$TOOL_COMMAND" =~ git[[:space:]]+(commit|push) ]]; then
            TRIGGER="post_commit"
        fi
        ;;
    *)
        TRIGGER="skill_or_manual"
        ;;
esac

if [ "$TRIGGER" = "other" ]; then
    echo '{}'
    exit 0
fi

# ── Compute SHA + dirty flag ───────────────────────────────────
SHA=$(git rev-parse HEAD 2>/dev/null || echo "")
if [ -z "$SHA" ]; then
    echo '{}'
    exit 0
fi
DIRTY=0
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    DIRTY=1
fi

EVIDENCE_DIR=".claude/review-evidence"
EVIDENCE_FILE="${EVIDENCE_DIR}/${SHA}.json"
mkdir -p "$EVIDENCE_DIR"

# ── Cache lookup ───────────────────────────────────────────────
NEEDS_COMPUTE=1
if [ "$DIRTY" = "0" ] && [ -f "$EVIDENCE_FILE" ]; then
    NEEDS_COMPUTE=0
fi

if [ "$NEEDS_COMPUTE" = "1" ]; then
    BASE_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
    if [ "$TRIGGER" = "post_commit" ]; then
        # Async: detach
        nohup python3 "${PLUGIN_ROOT}/lib/review_evidence/collector.py" \
            --sha "$SHA" --base "$BASE_BRANCH" --dirty "$DIRTY" \
            --out "$EVIDENCE_FILE" >/dev/null 2>&1 &
        echo '{"additional_context":"review-evidence: async compute scheduled for '"$SHA"'"}'
        exit 0
    fi
    # Sync
    if ! python3 "${PLUGIN_ROOT}/lib/review_evidence/collector.py" \
            --sha "$SHA" --base "$BASE_BRANCH" --dirty "$DIRTY" \
            --out "$EVIDENCE_FILE" 2>/dev/null; then
        echo '{"additional_context":"review-evidence: compute failed (see logs)"}'
        exit 0
    fi
fi

# ── Read verdict + enforce hard-block (only on PreToolUse) ─────
if [ ! -f "$EVIDENCE_FILE" ]; then
    echo '{}'
    exit 0
fi

BLOCK=$(jq -r '.verdict.block // false' "$EVIDENCE_FILE" 2>/dev/null || echo "false")
REASONS=$(jq -r '.verdict.block_reasons | join(", ")' "$EVIDENCE_FILE" 2>/dev/null || echo "")

if [ "$IS_BLOCKING" = "1" ] && [ "$BLOCK" = "true" ]; then
    devforge_log "evidence_block" "warn" "{\"sha\":\"${SHA}\",\"reasons\":\"$(echo "$REASONS" | sed 's/"/\\"/g')\"}" 2>/dev/null || true
    cat <<JSON
{
  "decision": "block",
  "reason": "review-evidence: hard-block triggered. Reasons: ${REASONS}. Evidence: ${EVIDENCE_FILE}. Override: touch ~/.claude/.devforge-skip-evidence"
}
JSON
    exit 0
fi

# ── Advisory (always) ──────────────────────────────────────────
COV=$(jq -r '.metrics.coverage.overall_pct // "n/a"' "$EVIDENCE_FILE" 2>/dev/null)
LINT=$(jq -r '.metrics.lint.errors // 0' "$EVIDENCE_FILE" 2>/dev/null)
CTX="review-evidence ${SHA:0:8}: coverage=${COV}%, lint_errors=${LINT}, block=${BLOCK}. File: ${EVIDENCE_FILE}"
cat <<JSON
{"additional_context": "${CTX}"}
JSON
```

```bash
chmod +x hooks/review-evidence
```

### Step 4 — Aggiorna hooks/hooks.json

Aggiungi `review-evidence` nei matcher Bash di `PreToolUse` (dopo `pr-gate`) e `PostToolUse` (dopo `post-commit-review`).

**PreToolUse Bash — aggiungere dopo `pr-gate`:**

```json
{
  "type": "command",
  "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" review-evidence",
  "timeout": 20
}
```

**PostToolUse Bash — aggiungere dopo `post-commit-review`:**

```json
{
  "type": "command",
  "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" review-evidence",
  "timeout": 20
}
```

Mantieni il resto invariato. Timeout 20s perché compute Python può essere lento; PostToolUse comunque scappa async.

### Step 5 — Stub temporaneo per collector

Visto che Task 04 implementerà il collector vero, crea uno **stub minimale** in `lib/review_evidence/collector.py` che permetta ai test del Task 03 di passare:

```python
"""Stub orchestrator — replaced by Task 04. Emits a minimal valid evidence file."""
import argparse
import json
import sys
from datetime import datetime, timezone

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sha", required=True)
    p.add_argument("--base", required=True)
    p.add_argument("--dirty", default="0")
    p.add_argument("--out", required=True)
    args = p.parse_args()
    ev = {
        "schema_version": "1.0",
        "sha": args.sha,
        "branch": "unknown",
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "dirty_tree": args.dirty == "1",
        "base_branch": args.base,
        "stack_detected": [],
        "metrics": {},
        "spec_drift": None,
        "verdict": {"block": False, "block_reasons": [], "warnings": ["stub: Task 04 not yet implemented"]},
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(ev, f, indent=2)
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

Task 04 sostituirà completamente questo stub.

### Step 6 — Esegui test (passa)

```bash
pytest tests/test_review_evidence_hook.py -v
```

**Output atteso:** `5 passed`.

### Step 7 — Commit

```bash
git add hooks/review-evidence hooks/hooks.json \
        lib/review_evidence/collector.py \
        tests/test_review_evidence_hook.py
git commit -m "feat(review-evidence): add hook bash entry + bypass + hooks.json registration (#task-03)"
```

## Criteri di accettazione

- [ ] `hooks/review-evidence` esiste, è eseguibile (`chmod +x`)
- [ ] Hook detect 3 trigger (pre_pr, post_commit, skill_or_manual)
- [ ] Bypass via state file `~/.claude/.devforge-skip-evidence` funziona
- [ ] Bypass via env var `DEVFORGE_SKIP_EVIDENCE=1` funziona come fallback
- [ ] `hooks.json` aggiornato con review-evidence in PreToolUse Bash e PostToolUse Bash
- [ ] 5 test passano
- [ ] Hook emit `{"decision":"block"}` su PreToolUse se evidence ha `verdict.block=true`
- [ ] Hook emit `additional_context` advisory in tutti gli altri casi
