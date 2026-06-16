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
# Test 7 — devforge_identity_bundle: 10 campi (6 git/os + 4 auth), JSON valido, no repo_root
# ─────────────────────────────────────────────────────────────
echo "Test 7: devforge_identity_bundle emits 10-field valid JSON (in a repo)"

IBREPO="${TEST_TMP}/ibrepo"
mkdir -p "$IBREPO"
( cd "$IBREPO" && git init -q && git config user.email "Mario.Rossi@siae.it" && git config user.name "Mario Rossi" )
# Isola dall'~/.claude.json reale: auth_* presenti ma vuoti, chiavi deterministiche ovunque.
BUNDLE7=$( cd "$IBREPO" && DEVFORGE_CLAUDE_JSON="/nonexistent/claude.json" devforge_identity_bundle )
# parsable JSON with exactly the 10 expected keys (6 git/os + 4 auth_*), no repo_root
keys7=$(printf '%s' "$BUNDLE7" | python3 -c "import json,sys; d=json.load(sys.stdin); print(','.join(sorted(d.keys())))" 2>/dev/null || echo "PARSE_FAIL")
assert_eq "bundle has 10 keys (6 git/os + 4 auth), no repo_root" "auth_account_uuid,auth_email,auth_org_name,auth_org_uuid,git_global_email,git_global_name,git_local_email,git_local_name,host,os_user" "$keys7"
local_email7=$(printf '%s' "$BUNDLE7" | python3 -c "import json,sys; print(json.load(sys.stdin)['git_local_email'])" 2>/dev/null || echo "ERR")
assert_eq "git_local_email captured" "Mario.Rossi@siae.it" "$local_email7"

# ─────────────────────────────────────────────────────────────
# Test 8 — devforge_identity_bundle: outside a repo, set -e, no abort
# ─────────────────────────────────────────────────────────────
echo "Test 8: devforge_identity_bundle outside a repo does not abort (set -e)"
NONREPO="${TEST_TMP}/nonrepo"
mkdir -p "$NONREPO"
BUNDLE8=$( cd "$NONREPO" && set -euo pipefail && devforge_identity_bundle; echo "exit:$?" )
ib8_exit=$(printf '%s' "$BUNDLE8" | grep -o 'exit:[0-9]*' | cut -d: -f2)
assert_eq "helper exit 0 outside repo" "0" "${ib8_exit:-1}"
BUNDLE8_JSON=$(printf '%s' "$BUNDLE8" | sed 's/exit:[0-9]*$//')
osuser8=$(printf '%s' "$BUNDLE8_JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); print('OK' if d['os_user'] else 'EMPTY')" 2>/dev/null || echo "PARSE_FAIL")
assert_eq "os_user populated outside repo" "OK" "$osuser8"

# ─────────────────────────────────────────────────────────────
# Test 9 — sanitization: git name with quotes/backslash/newline → valid JSON
# ─────────────────────────────────────────────────────────────
echo "Test 9: identity bundle sanitizes quotes/backslash/newline in git name"
IBREPO9="${TEST_TMP}/ibrepo9"
mkdir -p "$IBREPO9"
( cd "$IBREPO9" && git init -q && git config user.email "a@b.it" && git config user.name 'Ma"rio\Ros'$'\n''si' )
BUNDLE9=$( cd "$IBREPO9" && devforge_identity_bundle )
valid9=$(printf '%s' "$BUNDLE9" | python3 -c "import json,sys; json.load(sys.stdin); print('VALID')" 2>/dev/null || echo "INVALID")
assert_eq "bundle JSON valid with special chars in name" "VALID" "$valid9"

# ─────────────────────────────────────────────────────────────
# Test 10/11 — session-start emits identity in user.json + session_start.meta
# ─────────────────────────────────────────────────────────────
echo "Test 10/11: session-start writes identity to user.json and session_start.meta"
SS_HOME="${TEST_TMP}/sshome"
SS_REPO="${SS_HOME}/repo"
mkdir -p "$SS_REPO"
( cd "$SS_REPO" && git init -q && git config user.email "dev@siae.it" && git config user.name "Dev Test" )
SS_LOG="${SS_HOME}/ss.jsonl"
identity_in_userjson="NO"; identity_in_event="NO"
(
  cd "$SS_REPO"
  HOME="$SS_HOME" DEVFORGE_LOG_FILE="$SS_LOG" DEVFORGE_DISABLE_RECAP=1 \
    bash "${PLUGIN_ROOT}/hooks/session-start" >/dev/null 2>&1 </dev/null || true
)
# user.json identity
UJSON=$(find "$SS_HOME/.claude/devforge-state" -name user.json 2>/dev/null | head -1)
if [ -n "$UJSON" ]; then
  identity_in_userjson=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print('YES' if isinstance(d.get('identity'),dict) and 'os_user' in d['identity'] else 'NO')" "$UJSON" 2>/dev/null || echo "NO")
fi
assert_eq "user.json includes identity bundle" "YES" "$identity_in_userjson"
# session_start.meta identity
if [ -f "$SS_LOG" ]; then
  identity_in_event=$(grep '"event":"session_start"' "$SS_LOG" 2>/dev/null | python3 -c "
import json,sys
for l in sys.stdin:
    d=json.loads(l); m=d.get('meta',{})
    if isinstance(m.get('identity'),dict) and 'os_user' in m['identity']: print('YES'); break
else: print('NO')
" 2>/dev/null || echo "NO")
fi
assert_eq "session_start.meta includes identity bundle" "YES" "$identity_in_event"

# ─────────────────────────────────────────────────────────────
# Test 12 — user.json write tolerates an unparsable bundle (silent skip)
# ─────────────────────────────────────────────────────────────
echo "Test 12: user.json write skips identity silently on unparsable bundle"
UJ12="${TEST_TMP}/uj12.json"
python3 -c "
import json,sys
raw,source,canonical,path,bundle=sys.argv[1:6]
d={'raw':raw,'source':source,'canonical':canonical}
try:
    d['identity']=json.loads(bundle)
except Exception:
    pass
json.dump(d,open(path,'w'))
" "r@x" "test" "r@x" "$UJ12" "{not valid json" 2>/dev/null || true
uj12_ok=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print('OK' if 'identity' not in d and d.get('raw')=='r@x' else 'BAD')" "$UJ12" 2>/dev/null || echo "ERR")
assert_eq "user.json valid without identity on bad bundle" "OK" "$uj12_ok"

# ─────────────────────────────────────────────────────────────
# Test 13 — identity bundle validity guard (malformed → {})
# ─────────────────────────────────────────────────────────────
echo "Test 13: malformed bundle is coerced to {} before meta interpolation"
# Reproduce the session-start guard logic in isolation
_guard() { case "$1" in '{'*'}') printf '%s' "$1" ;; *) printf '{}' ;; esac; }
assert_eq "valid bundle passes through" '{"a":1}' "$(_guard '{"a":1}')"
assert_eq "partial/garbage bundle coerced to {}" '{}' "$(_guard 'garbage{partial')"
assert_eq "empty bundle coerced to {}" '{}' "$(_guard '')"

# ─────────────────────────────────────────────────────────────
# Test 14 — token-collector fields: 14-field contract + by_skill/by_model_tokens/pricing JSON + token_state_complete
# ─────────────────────────────────────────────────────────────
echo "Test 14: token-collector fields emits 14 columns with valid by_skill/by_model_tokens/pricing + token_state_complete"
SID14="testsid-fields13"
SESSION_DIR14="${TEST_TMP}/.claude/devforge-state/${SID14}"
mkdir -p "${SESSION_DIR14}"
export DEVFORGE_SESSION_DIR="${SESSION_DIR14}"
cat > "${SESSION_DIR14}/token-stats.json" <<'JSON'
{"input":600,"output":200,"cache_read":200,"cache_write_5m":0,"cache_write_1h":0,
 "cache_write":0,"total":1000,"cost_eur":0.05,
 "by_model":{"claude-opus-4-8":1000},"by_tool":{"Bash":5},
 "by_skill":{"siae-devforge:siae-tdd":{"output":200,"input":600,"cache_write_5m":0,"cache_write_1h":0}},
 "by_model_tokens":{"claude-opus-4-8":{"input":600,"output":200,"cache_read":200,"cache_write_5m":0,"cache_write_1h":0}},
 "model_prevalent":"claude-opus-4-8","updated_at":"2026-06-03T00:00:00Z"}
JSON
FL14=$(python3 "${PLUGIN_ROOT}/lib/token-collector.py" fields 2>/dev/null)
nf14=$(printf '%s' "$FL14" | awk -F'\t' '{print NF}')
assert_eq "fields line has 14 columns" "14" "${nf14}"
# f14 token_state_complete: total=1000>0 e dir risolta → "true"
assert_eq "f14 token_state_complete true (total>0)" "true" "$(printf '%s' "$FL14" | cut -f14)"
# f11 by_skill, f12 by_model_tokens, f13 pricing — all valid JSON, build a meta and parse
META14="{\"by_skill\":$(printf '%s' "$FL14" | cut -f11),\"by_model_tokens\":$(printf '%s' "$FL14" | cut -f12),\"pricing\":$(printf '%s' "$FL14" | cut -f13)}"
parsed14=$(printf '%s' "$META14" | python3 -c "
import json,sys
d=json.load(sys.stdin)
sk=d['by_skill']['siae-devforge:siae-tdd']
print('cache_read' not in sk, d['by_model_tokens']['claude-opus-4-8']['cache_read'], d['pricing']['unit'], d['pricing']['by_model']['claude-opus-4-8']['input'])
" 2>/dev/null || echo "PARSE_FAIL")
assert_eq "by_skill no cache_read, by_model_tokens has cache_read, pricing unit+rate" "True 200 usd_per_1m_tokens 5.0" "${parsed14}"

# ─────────────────────────────────────────────────────────────
# Test 15 — capture-test-result emits test_run_result (Comp.2)
# ─────────────────────────────────────────────────────────────
echo "Test 15: capture-test-result emits test_run_result (status+framework)"
CTR_HOME="${TEST_TMP}/ctrhome"; mkdir -p "${CTR_HOME}/.claude"
CTR_LOG="${CTR_HOME}/ctr.jsonl"; rm -f "$CTR_LOG"
echo '{"tool_input":{"command":"pytest tests/ -q"},"tool_response":{"is_error":true,"output":"1 failed"}}' \
  | HOME="$CTR_HOME" DEVFORGE_LOG_FILE="$CTR_LOG" bash "${PLUGIN_ROOT}/hooks/capture-test-result" >/dev/null 2>&1 || true
trr=$(grep '"event":"test_run_result"' "$CTR_LOG" 2>/dev/null | python3 -c "
import json,sys
for l in sys.stdin:
    m=json.loads(l).get('meta',{})
    if 'status' in m: print(m['status'], m.get('framework')); break
else: print('MISSING')
" 2>/dev/null || echo "MISSING")
assert_eq "test_run_result FAIL + pytest framework" "FAIL pytest" "$trr"

# ─────────────────────────────────────────────────────────────
# Test 16 — capture-test-result emits tdd_cycle on RED→GREEN (Comp.2)
# ─────────────────────────────────────────────────────────────
echo "Test 16: capture-test-result emits tdd_cycle RED->GREEN with elapsed_sec"
echo "siae-devforge:siae-tdd" > "${CTR_HOME}/.claude/.devforge-session-skills"
# Seed RED state entered 5s ago
echo "RED|target|test|$(( $(date +%s) - 5 ))" > "${CTR_HOME}/.claude/.devforge-tdd-state"
rm -f "$CTR_LOG"
echo '{"tool_input":{"command":"pytest tests/ -q"},"tool_response":{"is_error":false,"output":"1 passed"}}' \
  | HOME="$CTR_HOME" DEVFORGE_LOG_FILE="$CTR_LOG" bash "${PLUGIN_ROOT}/hooks/capture-test-result" >/dev/null 2>&1 || true
tdc=$(grep '"event":"tdd_cycle"' "$CTR_LOG" 2>/dev/null | python3 -c "
import json,sys
for l in sys.stdin:
    m=json.loads(l).get('meta',{})
    if m.get('to_phase')=='GREEN': print(m['from_phase'], m['to_phase'], m['elapsed_sec']>=5); break
else: print('MISSING')
" 2>/dev/null || echo "MISSING")
assert_eq "tdd_cycle RED->GREEN elapsed>=5" "RED GREEN True" "$tdc"

# ─────────────────────────────────────────────────────────────
# Test 17 — devforge_session_token_total helper (Comp.3a)
# ─────────────────────────────────────────────────────────────
echo "Test 17: devforge_session_token_total reads total, fallback 0"
SID17="testsid-toktot"; SDIR17="${TEST_TMP}/.claude/devforge-state/${SID17}"; mkdir -p "$SDIR17"
export DEVFORGE_SESSION_DIR="$SDIR17"
printf '{"total":12345,"output":100}' > "${SDIR17}/token-stats.json"
assert_eq "session_token_total reads total" "12345" "$(devforge_session_token_total)"
rm -f "${SDIR17}/token-stats.json"
assert_eq "session_token_total fallback 0 when missing" "0" "$(devforge_session_token_total)"

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════"
echo "Results: ${PASS} passed, ${FAIL} failed"
echo "═══════════════════════════════════════"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
