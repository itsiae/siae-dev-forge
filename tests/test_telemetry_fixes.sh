#!/usr/bin/env bash
# Regression tests for PR #187 fixes:
#   1. session-start: USER_CANONICAL must be canonicalized (not raw email)
#   2. devforge_init_session: DEVFORGE_PINNED_USER must be canonicalized from user.json
#   3. devforge_next_seq: lock contention must NOT return sentinel 0
#   4. devforge_create_batch: empty batch must not advance cursor
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

TEST_TMP=$(mktemp -d)
trap 'rm -rf "$TEST_TMP"' EXIT

export HOME="$TEST_TMP"
mkdir -p "${TEST_TMP}/.claude"

PASS=0
FAIL=0

assert_eq() {
    local name="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        echo "  PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $name"
        echo "    expected: '$expected'"
        echo "    actual:   '$actual'"
        FAIL=$((FAIL + 1))
    fi
}

assert_ne() {
    local name="$1" unexpected="$2" actual="$3"
    if [ "$unexpected" != "$actual" ]; then
        echo "  PASS: $name"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $name — got unexpected value '$actual'"
        FAIL=$((FAIL + 1))
    fi
}

# Source logger for unit-level tests
source "${PLUGIN_ROOT}/lib/logger.sh"

# ─────────────────────────────────────────────────────────────
# Test 1 — devforge_canonicalize_user: mixed-case email
# ─────────────────────────────────────────────────────────────
echo "Test 1: devforge_canonicalize_user lowercases mixed-case email"
result=$(devforge_canonicalize_user "Alice@Example.COM")
assert_eq "mixed-case email canonical" "alice@example.com" "$result"

# ─────────────────────────────────────────────────────────────
# Test 2 — devforge_canonicalize_user: GitHub noreply address
# ─────────────────────────────────────────────────────────────
echo "Test 2: devforge_canonicalize_user extracts username from noreply"
result=$(devforge_canonicalize_user "12345678+alice@users.noreply.github.com")
assert_eq "noreply address canonical" "alice" "$result"

# ─────────────────────────────────────────────────────────────
# Test 3 — devforge_init_session: DEVFORGE_PINNED_USER canonicalized
# ─────────────────────────────────────────────────────────────
echo "Test 3: devforge_init_session canonicalizes raw email from user.json"

SID="testsid123"
SESSION_DIR="${TEST_TMP}/.claude/devforge-state/${SID}"
mkdir -p "${SESSION_DIR}"
echo "${SID}" > "${TEST_TMP}/.claude/.devforge-session-id"
echo "0" > "${SESSION_DIR}/seq"

# Write a user.json with a mixed-case raw email
python3 -c "
import json
json.dump({'raw': 'Alice@Example.COM', 'source': 'test', 'canonical': 'Alice@Example.COM'}, open('${SESSION_DIR}/user.json', 'w'))
"

DEVFORGE_PINNED_USER=""
DEVFORGE_PINNED_SID=""
DEVFORGE_SESSION_DIR=""
devforge_init_session

assert_eq "DEVFORGE_PINNED_USER canonicalized" "alice@example.com" "$DEVFORGE_PINNED_USER"

# ─────────────────────────────────────────────────────────────
# Test 4 — devforge_next_seq: lock contention must not return 0
# ─────────────────────────────────────────────────────────────
echo "Test 4: devforge_next_seq returns non-zero on lock contention"

SID2="testsid456"
SESSION_DIR2="${TEST_TMP}/.claude/devforge-state/${SID2}"
mkdir -p "${SESSION_DIR2}"
echo "0" > "${SESSION_DIR2}/seq"
echo "${SID2}" > "${TEST_TMP}/.claude/.devforge-session-id"

export DEVFORGE_SESSION_DIR="${SESSION_DIR2}"
export DEVFORGE_PINNED_SID="${SID2}"

# Simulate lock contention: hold the lock in background, then call devforge_next_seq
LOCK_FILE="${SESSION_DIR2}/seq.lock"
# Hold the lock for 1 second in background
( flock 9; sleep 1 ) 9>"${LOCK_FILE}" &
LOCK_PID=$!
sleep 0.1  # ensure the background process has the lock

seq_result=$(devforge_next_seq)

# Kill the lock holder
kill "$LOCK_PID" 2>/dev/null || true
wait "$LOCK_PID" 2>/dev/null || true

assert_ne "devforge_next_seq contention returns non-zero seq" "0" "$seq_result"

# ─────────────────────────────────────────────────────────────
# Test 5 — devforge_create_batch: empty tail must not advance cursor
# ─────────────────────────────────────────────────────────────
echo "Test 5: devforge_create_batch does not advance cursor on empty batch"

source "${PLUGIN_ROOT}/lib/telemetry-upload.sh"

SID3="testsid789"
SESSION_DIR3="${TEST_TMP}/.claude/devforge-state/${SID3}"
mkdir -p "${SESSION_DIR3}/outbox/acked"
export DEVFORGE_SESSION_DIR="${SESSION_DIR3}"

# Create an activity file with 10 bytes of content
printf '{"e":1}\n' > "${SESSION_DIR3}/activity.jsonl"
INITIAL_SIZE=$(stat -f%z "${SESSION_DIR3}/activity.jsonl" 2>/dev/null || stat -c%s "${SESSION_DIR3}/activity.jsonl")

# Set cursor to exactly the file size so tail produces 0 bytes
echo "${INITIAL_SIZE}" > "${SESSION_DIR3}/outbox/.cursor"

# Call create_batch — cursor already at EOF so batch should be empty (or skipped)
devforge_create_batch

# Cursor must still be at INITIAL_SIZE (or not increased beyond it)
cursor_after=$(cat "${SESSION_DIR3}/outbox/.cursor" 2>/dev/null || echo "0")
assert_eq "cursor unchanged when no new content" "${INITIAL_SIZE}" "${cursor_after}"

# No empty batch files should exist in outbox
empty_batches=$(find "${SESSION_DIR3}/outbox" -maxdepth 1 -name 'batch-*.jsonl' -empty 2>/dev/null | wc -l | tr -d ' ')
assert_eq "no empty batch files in outbox" "0" "${empty_batches}"

# ─────────────────────────────────────────────────────────────
# Test 6 — devforge_create_batch: valid content advances cursor correctly
# ─────────────────────────────────────────────────────────────
echo "Test 6: devforge_create_batch advances cursor on valid new content"

SID4="testsid999"
SESSION_DIR4="${TEST_TMP}/.claude/devforge-state/${SID4}"
mkdir -p "${SESSION_DIR4}/outbox/acked"
export DEVFORGE_SESSION_DIR="${SESSION_DIR4}"

# Write 2 lines, set cursor to 0
printf '{"event":"a"}\n{"event":"b"}\n' > "${SESSION_DIR4}/activity.jsonl"
FULL_SIZE=$(stat -f%z "${SESSION_DIR4}/activity.jsonl" 2>/dev/null || stat -c%s "${SESSION_DIR4}/activity.jsonl")
echo "0" > "${SESSION_DIR4}/outbox/.cursor"

devforge_create_batch

cursor_after=$(cat "${SESSION_DIR4}/outbox/.cursor" 2>/dev/null || echo "0")
assert_eq "cursor advanced to file size" "${FULL_SIZE}" "${cursor_after}"

# Batch file must exist and be non-empty
batch_count=$(find "${SESSION_DIR4}/outbox" -maxdepth 1 -name 'batch-*.jsonl' -not -empty 2>/dev/null | wc -l | tr -d ' ')
assert_eq "non-empty batch file created" "1" "${batch_count}"

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════"
echo "Results: ${PASS} passed, ${FAIL} failed"
echo "═══════════════════════════════════════"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
