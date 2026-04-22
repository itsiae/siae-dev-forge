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

echo "SETUP OK"
exit 0
