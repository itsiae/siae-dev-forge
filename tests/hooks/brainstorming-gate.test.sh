#!/usr/bin/env bash
# Test: brainstorming-gate hook — progressive enforcement (nudge/warn/block)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

TEST_HOME=$(mktemp -d)
TEST_REPO=$(mktemp -d)
TEST_LOG=$(mktemp)

trap 'rm -rf "$TEST_HOME" "$TEST_REPO" "$TEST_LOG" 2>/dev/null || true' EXIT

export HOME="$TEST_HOME"
export DEVFORGE_LOG_FILE="$TEST_LOG"
export DEVFORGE_SESSION_DIR=$(mktemp -d)
export DEVFORGE_FORCE_BASH_FALLBACK=1
mkdir -p "${HOME}/.claude"

cd "$TEST_REPO"
git init -q
git config user.email "test@test.local"
git config user.name "Test"
git remote add origin "https://github.com/itsiae/test-repo.git"
echo "hello" > hello.ts
git add hello.ts
git commit -q -m "initial"

invoke_gate() {
    local file_path="$1"
    local hook_input
    hook_input=$(python3 -c 'import json,sys; print(json.dumps({"tool_name":"Edit","file_path":sys.argv[1],"tool_input":{"file_path":sys.argv[1]}}))' "$file_path")
    echo "$hook_input" | bash "${PLUGIN_ROOT}/hooks/brainstorming-gate" 2>/dev/null
}

set_sid() {
    echo "$1" > "${HOME}/.claude/.devforge-session-id"
}

count_events() {
    local event_name="$1"
    grep -c "\"event\":\"${event_name}\"" "$DEVFORGE_LOG_FILE" 2>/dev/null || true
}

read_counter() {
    cat "${HOME}/.claude/.devforge-brainstorm-counter" 2>/dev/null || echo ""
}

set_session_skill() {
    echo "$1" > "${HOME}/.claude/.devforge-session-skills"
}

set_sid "test-sid-12345"

# ─── Scenario 1: N=1 → nudge soft ───
DEVFORGE_ENFORCEMENT_STRICT=1 invoke_gate "${TEST_REPO}/hello.ts"
if [ "$(count_events brainstorming_nudge_soft)" != "1" ]; then
    echo "FAIL scenario 1: nudge_soft count != 1"
    cat "$DEVFORGE_LOG_FILE"
    exit 1
fi
COUNTER=$(read_counter)
if [ "$COUNTER" != "test-sid-12345|1" ]; then
    echo "FAIL scenario 1: counter = '$COUNTER', atteso 'test-sid-12345|1'"
    exit 1
fi
echo "PASS scenario 1: N=1 nudge_soft + counter=1"

# ─── Scenario 2: N=2 → warn block ───
OUT=$(DEVFORGE_ENFORCEMENT_STRICT=1 invoke_gate "${TEST_REPO}/hello.ts")
if [ "$(count_events brainstorming_gate_warn)" != "1" ]; then
    echo "FAIL scenario 2: gate_warn count != 1"
    exit 1
fi
if ! echo "$OUT" | grep -qE '"decision":\s*"block"'; then
    echo "FAIL scenario 2: no decision:block"
    echo "OUT: $OUT"
    exit 1
fi
COUNTER=$(read_counter)
if [ "$COUNTER" != "test-sid-12345|2" ]; then
    echo "FAIL scenario 2: counter='$COUNTER'"
    exit 1
fi
echo "PASS scenario 2: N=2 warn + block + counter=2"

# ─── Scenario 3: N=4 → hard block ───
DEVFORGE_ENFORCEMENT_STRICT=1 invoke_gate "${TEST_REPO}/hello.ts" >/dev/null  # N=3
OUT=$(DEVFORGE_ENFORCEMENT_STRICT=1 invoke_gate "${TEST_REPO}/hello.ts")       # N=4
if [ "$(count_events brainstorming_gate_blocked)" != "1" ]; then
    echo "FAIL scenario 3: gate_blocked count != 1"
    exit 1
fi
if ! echo "$OUT" | grep -qE '"decision":\s*"block"'; then
    echo "FAIL scenario 3: no decision:block a N=4"
    exit 1
fi
if ! echo "$OUT" | grep -qi "BLOCCATO"; then
    echo "FAIL scenario 3: no 'BLOCCATO' in reason"
    exit 1
fi
echo "PASS scenario 3: N=4 hard block"

# ─── Scenario 5: siae-brainstorming in session → short-circuit ───
set_session_skill "siae-brainstorming"
echo "test-sid-12345|0" > "${HOME}/.claude/.devforge-brainstorm-counter"
DEVFORGE_ENFORCEMENT_STRICT=1 invoke_gate "${TEST_REPO}/hello.ts"
COUNTER=$(read_counter)
if echo "$COUNTER" | grep -qE "\|[1-9]"; then
    echo "FAIL scenario 5: counter incrementato con siae-brainstorming presente ($COUNTER)"
    exit 1
fi
echo "PASS scenario 5: siae-brainstorming presente → no enforcement"
rm -f "${HOME}/.claude/.devforge-session-skills"

# ─── Scenario 10: senza STRICT → no enforcement ───
rm -f "${HOME}/.claude/.devforge-brainstorm-counter"
BLOCKED_BEFORE=$(count_events brainstorming_gate_blocked)
invoke_gate "${TEST_REPO}/hello.ts"
BLOCKED_AFTER=$(count_events brainstorming_gate_blocked)
if [ "$BLOCKED_BEFORE" != "$BLOCKED_AFTER" ]; then
    echo "FAIL scenario 10: blocked aumentato senza STRICT"
    exit 1
fi
echo "PASS scenario 10: senza STRICT → no enforcement"

# ─── Scenario 6: file docs (.md) → out of scope (delta check) ───
BEFORE_6=$(count_events brainstorming_nudge_soft)
invoke_gate "${TEST_REPO}/README.md"
AFTER_6=$(count_events brainstorming_nudge_soft)
if [ "$BEFORE_6" != "$AFTER_6" ]; then
    echo "FAIL scenario 6: hook ha elaborato file .md (delta=$((AFTER_6 - BEFORE_6)))"
    exit 1
fi
echo "PASS scenario 6: file .md → pass (out of scope)"

# ─── Scenario 7: file IaC (.tf) → out of scope ───
echo "resource {}" > "${TEST_REPO}/main.tf"
BEFORE_7=$(count_events brainstorming_nudge_soft)
invoke_gate "${TEST_REPO}/main.tf"
AFTER_7=$(count_events brainstorming_nudge_soft)
if [ "$BEFORE_7" != "$AFTER_7" ]; then
    echo "FAIL scenario 7: hook ha elaborato .tf"
    exit 1
fi
echo "PASS scenario 7: file .tf → pass (out of scope)"

# ─── Scenario 8: repo non-itsiae → out of scope ───
NON_ITSIAE_REPO=$(mktemp -d)
(cd "$NON_ITSIAE_REPO" && git init -q && git config user.email t@t && git config user.name t && \
  git remote add origin "https://github.com/other-org/repo.git" && \
  echo "ts" > f.ts && git add f.ts && git commit -q -m init)
BEFORE_8=$(count_events brainstorming_nudge_soft)
invoke_gate "${NON_ITSIAE_REPO}/f.ts"
AFTER_8=$(count_events brainstorming_nudge_soft)
if [ "$BEFORE_8" != "$AFTER_8" ]; then
    echo "FAIL scenario 8: hook ha elaborato repo non-itsiae"
    rm -rf "$NON_ITSIAE_REPO"
    exit 1
fi
rm -rf "$NON_ITSIAE_REPO"
echo "PASS scenario 8: repo non-itsiae → pass (out of scope)"

# ─── Scenario 9: DEVFORGE_ENFORCEMENT_OFF=1 → escape hatch ───
BEFORE_9=$(count_events brainstorming_nudge_soft)
DEVFORGE_ENFORCEMENT_OFF=1 invoke_gate "${TEST_REPO}/hello.ts"
AFTER_9=$(count_events brainstorming_nudge_soft)
if [ "$BEFORE_9" != "$AFTER_9" ]; then
    echo "FAIL scenario 9: ENFORCEMENT_OFF non ha escapato"
    exit 1
fi
echo "PASS scenario 9: DEVFORGE_ENFORCEMENT_OFF=1 → escape immediato"

echo "SETUP OK"
exit 0
