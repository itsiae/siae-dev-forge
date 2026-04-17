#!/usr/bin/env bash
# Test: capture-test-result hook — TDD state machine transitions
# Covers the real Claude Code PostToolUse Bash payload schema:
#   tool_input.command + tool_response.is_error (no exit_code field)
# Validates both bugs fixed in fix/hook-tdd:
#   Bug 1: INIT→RED not triggered for failing tests (timeout + wrong jq path)
#   Bug 2: INIT→RED false positive for passing tests (EXIT_CODE="" treated as FAIL)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$(cd "$SCRIPT_DIR/../hooks" && pwd)/capture-test-result"
STATE_FILE="${HOME}/.claude/.devforge-tdd-state"
SKILLS_FILE="${HOME}/.claude/.devforge-session-skills"

PASS=0
FAIL=0

# --- Helpers ---

reset_state() {
    local phase="${1:-INIT}"
    echo "siae-tdd" > "$SKILLS_FILE"
    case "$phase" in
        INIT)    echo "INIT|pending|awaiting-test|$(date +%s)" > "$STATE_FILE" ;;
        RED)     echo "RED|unknown|test-confirmed|$(date +%s)" > "$STATE_FILE" ;;
        GREEN)   echo "GREEN|x|x|$(date +%s)" > "$STATE_FILE" ;;
        REFACTOR) echo "REFACTOR|x|x|$(date +%s)" > "$STATE_FILE" ;;
    esac
}

# Build a real Claude Code PostToolUse Bash payload (no exit_code field, only is_error).
# Uses python3 to guarantee valid JSON regardless of command content.
make_payload() {
    local command="$1" is_error="$2" output="${3:-}"
    python3 -c "
import json, sys
print(json.dumps({
    'session_id': '324b486a-b708-4f9a-9c8a-e0a2ae81a231',
    'hook_event_name': 'PostToolUse',
    'tool_name': 'Bash',
    'tool_input': {'command': sys.argv[1]},
    'tool_response': {'output': sys.argv[3], 'is_error': sys.argv[2] == 'true'}
}))" "$command" "$is_error" "$output"
}

assert_phase() {
    local label="$1" expected="$2"
    local actual
    actual=$(cut -d'|' -f1 < "$STATE_FILE")
    if [ "$actual" = "$expected" ]; then
        echo "PASS: $label → $actual"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label — expected=$expected actual=$actual"
        FAIL=$((FAIL + 1))
    fi
}

# ─────────────────────────────────────────────────────────
# BUG 1: FAIL tests must transition INIT → RED
# (is_error=true, no exit_code in payload — real Claude Code schema)
# ─────────────────────────────────────────────────────────

reset_state INIT
make_payload "pytest test_final_df_checkpoint.py -v" "true" "2 failed in 0.12s" \
    | bash "$HOOK"
assert_phase "T01 pytest FAIL → RED (incident payload)" "RED"

reset_state INIT
make_payload "pytest code/glue/module/test_something.py" "true" "1 failed" \
    | bash "$HOOK"
assert_phase "T02 pytest path FAIL → RED" "RED"

reset_state INIT
make_payload "npx jest --coverage" "true" "1 failed, 0 passed" \
    | bash "$HOOK"
assert_phase "T03 jest FAIL → RED" "RED"

reset_state INIT
make_payload "npm test" "true" "Tests: 1 failed, 1 total" \
    | bash "$HOOK"
assert_phase "T04 npm test FAIL → RED" "RED"

reset_state INIT
make_payload "mvn test -pl module" "true" "Tests run: 2, Failures: 1" \
    | bash "$HOOK"
assert_phase "T05 mvn test FAIL → RED" "RED"

reset_state INIT
make_payload "go test ./..." "true" "FAIL\tpkg 0.002s" \
    | bash "$HOOK"
assert_phase "T06 go test FAIL → RED" "RED"

reset_state INIT
make_payload "cargo test" "true" "test x ... FAILED" \
    | bash "$HOOK"
assert_phase "T07 cargo test FAIL → RED" "RED"

reset_state INIT
make_payload "dotnet test" "true" "Failed: 1, Passed: 0" \
    | bash "$HOOK"
assert_phase "T08 dotnet test FAIL → RED" "RED"

reset_state INIT
make_payload "python -m pytest test_module.py" "true" "2 failed" \
    | bash "$HOOK"
assert_phase "T09 python -m pytest FAIL → RED" "RED"

# Numeric exit_code in payload (future-proofing / synthetic payloads)
reset_state INIT
python3 -c "
import json
print(json.dumps({
    'tool_input': {'command': 'pytest test.py'},
    'tool_response': {'exit_code': 1, 'output': '2 failed'}
}))" | bash "$HOOK"
assert_phase "T10 exit_code=1 (numeric field) → RED" "RED"

# ─────────────────────────────────────────────────────────
# BUG 2: PASS tests must NOT advance INIT → RED (false positive fix)
# ─────────────────────────────────────────────────────────

reset_state INIT
make_payload "pytest test.py" "false" "1 passed" \
    | bash "$HOOK"
assert_phase "T11 pytest PASS from INIT stays INIT (false-positive regression)" "INIT"

reset_state INIT
make_payload "npm test" "false" "Tests: 1 passed, 1 total" \
    | bash "$HOOK"
assert_phase "T12 npm test PASS from INIT stays INIT" "INIT"

# ─────────────────────────────────────────────────────────
# GREEN transitions: RED + PASS → GREEN
# ─────────────────────────────────────────────────────────

reset_state RED
make_payload "pytest test.py" "false" "1 passed" \
    | bash "$HOOK"
assert_phase "T13 pytest PASS from RED → GREEN" "GREEN"

reset_state RED
make_payload "npm test" "false" "1 passed" \
    | bash "$HOOK"
assert_phase "T14 jest PASS from RED → GREEN" "GREEN"

reset_state RED
make_payload "go test ./..." "false" "ok  pkg 0.001s" \
    | bash "$HOOK"
assert_phase "T15 go test PASS from RED → GREEN" "GREEN"

# ─────────────────────────────────────────────────────────
# Regression detection: GREEN + FAIL → RED
# ─────────────────────────────────────────────────────────

reset_state GREEN
make_payload "pytest test.py" "true" "1 failed" \
    | bash "$HOOK"
assert_phase "T16 pytest FAIL from GREEN → RED (regression)" "RED"

# ─────────────────────────────────────────────────────────
# Early exit: non-test commands must not touch state
# ─────────────────────────────────────────────────────────

reset_state INIT
make_payload "ls -la /tmp" "false" "" \
    | bash "$HOOK"
assert_phase "T17 non-test command (ls) → INIT unchanged" "INIT"

reset_state INIT
make_payload "git status" "false" "" \
    | bash "$HOOK"
assert_phase "T18 git status → INIT unchanged" "INIT"

# Early exit: framework not in regex (rspec) → state unchanged
reset_state INIT
make_payload "rspec spec/" "true" "1 failure" \
    | bash "$HOOK"
assert_phase "T19 rspec (not in regex) → INIT unchanged (early exit)" "INIT"

# ─────────────────────────────────────────────────────────
# siae-tdd not active: no state changes
# ─────────────────────────────────────────────────────────

echo "" > "$SKILLS_FILE"
echo "INIT|pending|awaiting-test|$(date +%s)" > "$STATE_FILE"
make_payload "pytest test.py" "true" "1 failed" \
    | bash "$HOOK"
assert_phase "T20 siae-tdd not in session → INIT unchanged" "INIT"

# ─────────────────────────────────────────────────────────
# Cleanup + riepilogo
# ─────────────────────────────────────────────────────────

rm -f "$STATE_FILE" "$SKILLS_FILE"

echo ""
echo "Risultato: ${PASS} PASS, ${FAIL} FAIL"
[ "$FAIL" -eq 0 ] || exit 1
