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

# ─── Scenario 6: file docs (.md) → out of scope ───
invoke_gate "${TEST_REPO}/README.md"
if [ "$(count_events brainstorming_nudge_soft)" != "0" ] || [ "$(count_events brainstorming_gate_blocked)" != "0" ]; then
    echo "FAIL scenario 6: hook ha elaborato file .md"
    exit 1
fi
echo "PASS scenario 6: file .md → pass (out of scope)"

# ─── Scenario 7: file IaC (.tf) → out of scope ───
echo "resource {}" > "${TEST_REPO}/main.tf"
invoke_gate "${TEST_REPO}/main.tf"
if [ "$(count_events brainstorming_nudge_soft)" != "0" ]; then
    echo "FAIL scenario 7: hook ha elaborato .tf"
    exit 1
fi
echo "PASS scenario 7: file .tf → pass (out of scope)"

# ─── Scenario 8: repo non-itsiae → out of scope ───
NON_ITSIAE_REPO=$(mktemp -d)
(cd "$NON_ITSIAE_REPO" && git init -q && git config user.email t@t && git config user.name t && \
  git remote add origin "https://github.com/other-org/repo.git" && \
  echo "ts" > f.ts && git add f.ts && git commit -q -m init)
invoke_gate "${NON_ITSIAE_REPO}/f.ts"
if [ "$(count_events brainstorming_nudge_soft)" != "0" ]; then
    echo "FAIL scenario 8: hook ha elaborato repo non-itsiae"
    rm -rf "$NON_ITSIAE_REPO"
    exit 1
fi
rm -rf "$NON_ITSIAE_REPO"
echo "PASS scenario 8: repo non-itsiae → pass (out of scope)"

# ─── Scenario 9: DEVFORGE_ENFORCEMENT_OFF=1 → escape hatch ───
DEVFORGE_ENFORCEMENT_OFF=1 invoke_gate "${TEST_REPO}/hello.ts"
if [ "$(count_events brainstorming_nudge_soft)" != "0" ]; then
    echo "FAIL scenario 9: ENFORCEMENT_OFF non ha escapato"
    exit 1
fi
echo "PASS scenario 9: DEVFORGE_ENFORCEMENT_OFF=1 → escape immediato"

echo "SETUP OK"
exit 0
