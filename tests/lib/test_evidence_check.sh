#!/usr/bin/env bash
# tests/lib/test_evidence_check.sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$SCRIPT_DIR/lib/evidence-check.sh"

PASS=0
FAIL=0
assert() {
    local name="$1"; local expected="$2"; local actual="$3"
    if [ "$expected" = "$actual" ]; then
        echo "  PASS  $name"
        PASS=$((PASS+1))
    else
        echo "  FAIL  $name (expected=$expected actual=$actual)"
        FAIL=$((FAIL+1))
    fi
}

# Setup isolated state
export HOME="$(mktemp -d)"
mkdir -p "$HOME/.claude"
trap 'rm -rf "$HOME"' EXIT

# --- siae-tdd positive ---
echo "GREEN|foo.py|test_bar|$(date +%s)" > "$HOME/.claude/.devforge-tdd-state"
devforge_skill_validated "siae-tdd" "dummy-task" && R=0 || R=1
assert "tdd_red_green_observed: GREEN state returns 0" "0" "$R"

# --- siae-tdd negative (INIT state) ---
echo "INIT|pending|awaiting|$(date +%s)" > "$HOME/.claude/.devforge-tdd-state"
devforge_skill_validated "siae-tdd" "dummy-task" && R=0 || R=1
assert "tdd_red_green_observed: INIT state returns 1" "1" "$R"

# --- siae-tdd negative (no state file) ---
rm -f "$HOME/.claude/.devforge-tdd-state"
devforge_skill_validated "siae-tdd" "dummy-task" && R=0 || R=1
assert "tdd_red_green_observed: missing state returns 1" "1" "$R"

# --- siae-brainstorming positive ---
export DEVFORGE_SESSION_START_S=$(($(date +%s) - 3600))  # 1h ago
mkdir -p docs/plans
touch docs/plans/2026-04-25-test-design.md  # mtime = now
devforge_skill_validated "siae-brainstorming" "dummy-task" && R=0 || R=1
assert "design_doc_produced: fresh design doc returns 0" "0" "$R"

# --- siae-brainstorming negative (old file) ---
# Set mtime to before session_start_s
touch -t 202001010000 docs/plans/2026-04-25-test-design.md
devforge_skill_validated "siae-brainstorming" "dummy-task" && R=0 || R=1
assert "design_doc_produced: stale file returns 1" "1" "$R"
rm -rf docs/plans

# --- siae-git-workflow positive ---
TMP_REPO="$(mktemp -d)"
git -C "$TMP_REPO" init -q
git -C "$TMP_REPO" commit --allow-empty -m "feat(x): y" -q
(cd "$TMP_REPO" && devforge_skill_validated "siae-git-workflow" "dummy-task") && R=0 || R=1
assert "conventional_commit_made: feat(x): y returns 0" "0" "$R"

# --- siae-git-workflow negative ---
git -C "$TMP_REPO" commit --allow-empty -m "updated stuff" -q
(cd "$TMP_REPO" && devforge_skill_validated "siae-git-workflow" "dummy-task") && R=0 || R=1
assert "conventional_commit_made: non-conventional returns 1" "1" "$R"
rm -rf "$TMP_REPO"

# --- siae-verification positive ---
export DEVFORGE_LOG_FILE="$HOME/.claude/devforge-activity.jsonl"
export DEVFORGE_SESSION_ID="test-session-123"
cat > "$DEVFORGE_LOG_FILE" <<EOF
{"sid":"test-session-123","event":"verification_run","meta":{"exit":0}}
EOF
devforge_skill_validated "siae-verification" "dummy-task" && R=0 || R=1
assert "verification_run_passed: exit=0 event returns 0" "0" "$R"

# --- siae-verification negative (no event) ---
echo '{"sid":"test-session-123","event":"other"}' > "$DEVFORGE_LOG_FILE"
devforge_skill_validated "siae-verification" "dummy-task" && R=0 || R=1
assert "verification_run_passed: no event returns 1" "1" "$R"

# --- siae-blind-review positive ---
cat > "$DEVFORGE_LOG_FILE" <<EOF
{"sid":"test-session-123","event":"blind_review_verdict","meta":{"verdict":"APPROVED"}}
EOF
devforge_skill_validated "siae-blind-review" "dummy-task" && R=0 || R=1
assert "blind_review_completed: verdict event returns 0" "0" "$R"

echo ""
echo "Total: $((PASS+FAIL))  PASS: $PASS  FAIL: $FAIL"
exit $FAIL
