#!/usr/bin/env bash
# Test suite for capture-test-result hook
# Verifies TDD state machine transitions, especially with escaped quotes in JSON
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_DIR="$(cd "${SCRIPT_DIR}/../../hooks" && pwd)"
HOOK="${HOOK_DIR}/capture-test-result"

# Temp dir for test isolation
TEST_TMP=$(mktemp -d)
trap 'rm -rf "$TEST_TMP"' EXIT

# Override HOME so hooks write to our temp dir
export HOME="$TEST_TMP"
mkdir -p "${TEST_TMP}/.claude"

PASS=0
FAIL=0

assert_eq() {
    local test_name="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        echo "  PASS: $test_name"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $test_name"
        echo "    expected: '$expected'"
        echo "    actual:   '$actual'"
        FAIL=$((FAIL + 1))
    fi
}

# ─────────────────────────────────────────────────────────────
# Test 1: Simple command (no escaped quotes) — INIT → RED
# ─────────────────────────────────────────────────────────────
echo "Test 1: Simple pytest command transitions INIT → RED"
echo "siae-tdd" > "${TEST_TMP}/.claude/.devforge-session-skills"
echo "INIT|pending|awaiting-test|$(date +%s)" > "${TEST_TMP}/.claude/.devforge-tdd-state"

echo '{"command": "pytest tests/ -v", "exit_code": 1, "stdout": "FAILED 3 tests"}' | bash "$HOOK"

TDD_PHASE=$(cat "${TEST_TMP}/.claude/.devforge-tdd-state" | cut -d'|' -f1)
assert_eq "INIT→RED on simple pytest fail" "RED" "$TDD_PHASE"

# ─────────────────────────────────────────────────────────────
# Test 2: Command with escaped quotes in path — INIT → RED
# This is the BUG: paths with spaces produce escaped quotes
# e.g. cd \"/Users/foo/Library/Mobile Documents/bar\" && pytest
# ─────────────────────────────────────────────────────────────
echo "Test 2: Pytest command with escaped quotes in path transitions INIT → RED"
echo "siae-tdd" > "${TEST_TMP}/.claude/.devforge-session-skills"
echo "INIT|pending|awaiting-test|$(date +%s)" > "${TEST_TMP}/.claude/.devforge-tdd-state"

# Simulate the JSON that Claude Code sends when the path has spaces
cat <<'JSONEOF' | bash "$HOOK"
{"command": "cd \"/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/bulk_transfer_api_app\" && python3 -m pytest tests/test_retry_transient.py -v 2>&1 | tail -30", "exit_code": 1, "stdout": "FAILED 10 tests"}
JSONEOF

TDD_PHASE=$(cat "${TEST_TMP}/.claude/.devforge-tdd-state" | cut -d'|' -f1)
assert_eq "INIT→RED on pytest with escaped quotes path" "RED" "$TDD_PHASE"

# ─────────────────────────────────────────────────────────────
# Test 3: RED → GREEN on test pass
# ─────────────────────────────────────────────────────────────
echo "Test 3: RED → GREEN on test pass"
echo "siae-tdd" > "${TEST_TMP}/.claude/.devforge-session-skills"
echo "RED|unknown|test-confirmed|$(date +%s)" > "${TEST_TMP}/.claude/.devforge-tdd-state"

echo '{"command": "pytest tests/ -v", "exit_code": 0, "stdout": "PASSED 3 tests"}' | bash "$HOOK"

TDD_PHASE=$(cat "${TEST_TMP}/.claude/.devforge-tdd-state" | cut -d'|' -f1)
assert_eq "RED→GREEN on pytest pass" "GREEN" "$TDD_PHASE"

# ─────────────────────────────────────────────────────────────
# Test 4: Non-test command is ignored (state unchanged)
# ─────────────────────────────────────────────────────────────
echo "Test 4: Non-test command leaves state unchanged"
echo "siae-tdd" > "${TEST_TMP}/.claude/.devforge-session-skills"
echo "INIT|pending|awaiting-test|$(date +%s)" > "${TEST_TMP}/.claude/.devforge-tdd-state"

echo '{"command": "ls -la", "exit_code": 0, "stdout": "total 42"}' | bash "$HOOK"

TDD_PHASE=$(cat "${TEST_TMP}/.claude/.devforge-tdd-state" | cut -d'|' -f1)
assert_eq "Non-test command keeps INIT" "INIT" "$TDD_PHASE"

# ─────────────────────────────────────────────────────────────
# Test 5: Command with nested JSON (multiline-ish)
# ─────────────────────────────────────────────────────────────
echo "Test 5: Jest command with complex path transitions INIT → RED"
echo "siae-tdd" > "${TEST_TMP}/.claude/.devforge-session-skills"
echo "INIT|pending|awaiting-test|$(date +%s)" > "${TEST_TMP}/.claude/.devforge-tdd-state"

cat <<'JSONEOF' | bash "$HOOK"
{"command": "cd \"/Users/user/My Projects/app\" && npx jest --verbose", "exit_code": 1, "stdout": "Tests: 2 failed, 1 passed"}
JSONEOF

TDD_PHASE=$(cat "${TEST_TMP}/.claude/.devforge-tdd-state" | cut -d'|' -f1)
assert_eq "INIT→RED on jest with escaped quotes" "RED" "$TDD_PHASE"

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════"
echo "Results: ${PASS} passed, ${FAIL} failed"
echo "═══════════════════════════════"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
