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
# Cursor file name must match the pattern used by devforge_create_batch: .cursor-<basename>
echo "${INITIAL_SIZE}" > "${SESSION_DIR3}/outbox/.cursor-activity.jsonl"

# Call create_batch — cursor already at EOF so batch should be empty (or skipped)
devforge_create_batch

# Cursor must still be at INITIAL_SIZE (or not increased beyond it)
cursor_after=$(cat "${SESSION_DIR3}/outbox/.cursor-activity.jsonl" 2>/dev/null || echo "0")
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
echo "0" > "${SESSION_DIR4}/outbox/.cursor-activity.jsonl"

devforge_create_batch

cursor_after=$(cat "${SESSION_DIR4}/outbox/.cursor-activity.jsonl" 2>/dev/null || echo "0")
assert_eq "cursor advanced to file size" "${FULL_SIZE}" "${cursor_after}"

# Batch file must exist and be non-empty
batch_count=$(find "${SESSION_DIR4}/outbox" -maxdepth 1 -name 'batch-*.jsonl' -not -empty 2>/dev/null | wc -l | tr -d ' ')
assert_eq "non-empty batch file created" "1" "${batch_count}"

# ─────────────────────────────────────────────────────────────
# Test 7 — token-collector fields: session_end token breakdown contract
# ─────────────────────────────────────────────────────────────
echo "Test 7: token-collector fields emits 10-field tab line + valid by_model/by_tool JSON"

SID7="testsid-fields"
SESSION_DIR7="${TEST_TMP}/.claude/devforge-state/${SID7}"
mkdir -p "${SESSION_DIR7}"
export DEVFORGE_SESSION_DIR="${SESSION_DIR7}"
cat > "${SESSION_DIR7}/token-stats.json" <<'JSON'
{"input":300,"output":200,"cache_read":400,"cache_write_5m":50,"cache_write_1h":50,
 "cache_write":100,"total":1000,"cost_eur":0.123456,
 "by_model":{"claude-opus-4-8":1000},"by_tool":{"Bash":5,"Read":9,"mcp__sport-kg":2},
 "model_prevalent":"claude-opus-4-8","updated_at":"2026-06-01T00:00:00Z"}
JSON

FIELDS_LINE=$(python3 "${PLUGIN_ROOT}/lib/token-collector.py" fields 2>/dev/null)
nfields=$(printf '%s' "$FIELDS_LINE" | awk -F'\t' '{print NF}')
assert_eq "fields line has 10 columns" "10" "${nfields}"
assert_eq "f1 total" "1000" "$(printf '%s' "$FIELDS_LINE" | cut -f1)"
assert_eq "f5 input" "300" "$(printf '%s' "$FIELDS_LINE" | cut -f5)"
assert_eq "f7 cache_write_5m" "50" "$(printf '%s' "$FIELDS_LINE" | cut -f7)"
BY_TOOL_JSON=$(printf '%s' "$FIELDS_LINE" | cut -f10)
# Build a session_end-style meta and validate it parses as JSON with the new keys
META="{\"by_model\":$(printf '%s' "$FIELDS_LINE" | cut -f9),\"by_tool\":${BY_TOOL_JSON}}"
parsed=$(printf '%s' "$META" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['by_tool']['Bash'], d['by_model']['claude-opus-4-8'])" 2>/dev/null || echo "PARSE_FAIL")
assert_eq "meta JSON valid with by_tool/by_model embedded" "5 1000" "${parsed}"

# ─────────────────────────────────────────────────────────────
# Test 8 — post-skill: token delta per skill in skill_completed
# ─────────────────────────────────────────────────────────────
echo "Test 8: post-skill emits tokens_total_delta/tokens_output_delta in skill_completed"

# post-skill calls devforge_init_session which re-derives DEVFORGE_SESSION_DIR
# from the sid. Discover that same dir so the subprocess finds our stats fixture.
devforge_init_session 2>/dev/null || true
SESSION_DIR8="${DEVFORGE_SESSION_DIR}"
mkdir -p "${SESSION_DIR8}"
# Current cumulative token stats (no .jsonl session → token-collector update is a no-op)
cat > "${SESSION_DIR8}/token-stats.json" <<'JSON'
{"input":600,"output":200,"cache_read":200,"cache_write_5m":0,"cache_write_1h":0,
 "cache_write":0,"total":1000,"cost_eur":0.05,"by_model":{},"by_tool":{},
 "model_prevalent":"","updated_at":"2026-06-01T00:00:00Z"}
JSON
# Previous skill snapshot: 5-field SKILL_TS_FILE (prev total=400, output=80)
SKILL_TS_FILE8="${HOME}/.claude/.devforge-skill-start"
mkdir -p "${HOME}/.claude"
echo '1710000000000000000|siae-devforge:siae-prev|2. Design|400|80' > "$SKILL_TS_FILE8"
TEST_LOG8="${TEST_TMP}/skilltok.jsonl"
export DEVFORGE_LOG_FILE="$TEST_LOG8"
rm -f "$TEST_LOG8"

echo '{"skill":"siae-devforge:siae-brainstorming"}' | bash "${PLUGIN_ROOT}/hooks/post-skill" >/dev/null 2>&1 || true

delta_total=$(grep '"event":"skill_completed"' "$TEST_LOG8" 2>/dev/null | python3 -c "
import json,sys
for l in sys.stdin:
    d=json.loads(l); m=d.get('meta',{})
    if 'tokens_total_delta' in m: print(m['tokens_total_delta']); break
else: print('MISSING')
" 2>/dev/null || echo "MISSING")
assert_eq "tokens_total_delta = 1000-400 = 600" "600" "${delta_total}"

delta_out=$(grep '"event":"skill_completed"' "$TEST_LOG8" 2>/dev/null | python3 -c "
import json,sys
for l in sys.stdin:
    d=json.loads(l); m=d.get('meta',{})
    if 'tokens_output_delta' in m: print(m['tokens_output_delta']); break
else: print('MISSING')
" 2>/dev/null || echo "MISSING")
assert_eq "tokens_output_delta = 200-80 = 120" "120" "${delta_out}"

# ─────────────────────────────────────────────────────────────
# Test 9 — post-skill: legacy 3-field SKILL_TS_FILE → no crash, delta 0
# ─────────────────────────────────────────────────────────────
echo "Test 9: post-skill tolerates legacy 3-field SKILL_TS_FILE (delta=0, no crash)"
echo '1710000000000000000|siae-devforge:siae-legacy|2. Design' > "$SKILL_TS_FILE8"
rm -f "$TEST_LOG8"
echo '{"skill":"siae-devforge:siae-brainstorming"}' | bash "${PLUGIN_ROOT}/hooks/post-skill" >/dev/null 2>&1
legacy_exit=$?
assert_eq "post-skill exit 0 on legacy 3-field file" "0" "${legacy_exit}"
legacy_delta=$(grep '"event":"skill_completed"' "$TEST_LOG8" 2>/dev/null | python3 -c "
import json,sys
for l in sys.stdin:
    d=json.loads(l); m=d.get('meta',{})
    if d.get('meta'): print(m.get('tokens_total_delta','MISSING')); break
else: print('NOEVENT')
" 2>/dev/null || echo "ERR")
assert_eq "legacy file → tokens_total_delta = 0" "0" "${legacy_delta}"

unset DEVFORGE_LOG_FILE
rm -f "$SKILL_TS_FILE8"

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════"
echo "Results: ${PASS} passed, ${FAIL} failed"
echo "═══════════════════════════════════════"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
