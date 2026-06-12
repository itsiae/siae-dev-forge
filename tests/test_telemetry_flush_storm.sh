#!/usr/bin/env bash
# Tests for telemetry flush storm fix (design 2026-06-12).
# Strategy: override _devforge_post_batch to inject HTTP codes, no real network.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PASS=0
FAIL=0
assert_eq() {
    local name="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then echo "  PASS: $name"; PASS=$((PASS+1));
    else echo "  FAIL: $name"; echo "    expected: '$expected'"; echo "    actual:   '$actual'"; FAIL=$((FAIL+1)); fi
}

# Fresh HOME + state per test
new_env() {
    TEST_TMP=$(mktemp -d)
    export HOME="$TEST_TMP"
    mkdir -p "${TEST_TMP}/.claude/devforge-state"
    export DEVFORGE_TELEMETRY_ENDPOINT="https://mock.invalid/v1/logs"
    export DEVFORGE_TELEMETRY_KEY="test-key"
}
cleanup_env() { rm -rf "$TEST_TMP"; }

# Seed an outbox with N batch files for a fake session
seed_outbox() {
    local sid="$1" n="$2"
    local ob="${HOME}/.claude/devforge-state/${sid}/outbox"
    mkdir -p "$ob"
    local i
    for i in $(seq 1 "$n"); do
        printf '{"e":%d}\n' "$i" > "${ob}/batch-000000000${i}-pid.jsonl"
    done
    echo "$ob"
}

source "${PLUGIN_ROOT}/lib/telemetry-upload.sh"

# ── Test 1: _devforge_post_batch is a defined function ──
echo "Test 1: _devforge_post_batch exists and is overridable"
new_env
_devforge_post_batch() { echo "200"; }   # override
seed_outbox "sess-A" 2 >/dev/null
devforge_upload_backlog
acked=$(ls "${HOME}/.claude/devforge-state/sess-A/outbox/acked"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
assert_eq "all batches acked on 200" "2" "$acked"
cleanup_env

# ── Test 2: lock held → second invocation returns 0 without processing ──
echo "Test 2: lock blocks concurrent invocation"
new_env
lock="${HOME}/.claude/.devforge-flush.lock"
mkdir -p "$lock"   # simulate a flush already in progress (fresh mtime)
seed_outbox "sess-B" 3 >/dev/null
_devforge_post_batch() { echo "200"; }
devforge_upload_backlog
pending=$(ls "${HOME}/.claude/devforge-state/sess-B/outbox"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
assert_eq "locked: batches untouched" "3" "$pending"
cleanup_env

# ── Test 3: stale lock (>120s) recovered, flush proceeds ──
echo "Test 3: stale lock recovered"
new_env
lock="${HOME}/.claude/.devforge-flush.lock"
mkdir -p "$lock"
# Backdate lock dir mtime to 121s ago (portable: touch -t needs a timestamp; use -A on BSD / -d on GNU)
old_epoch=$(( $(date +%s) - 121 ))
if touch -d "@${old_epoch}" "$lock" 2>/dev/null; then :; else
    # BSD touch: -t CCYYMMDDhhmm.SS
    touch -t "$(date -r "${old_epoch}" +%Y%m%d%H%M.%S 2>/dev/null)" "$lock" 2>/dev/null || true
fi
seed_outbox "sess-C" 2 >/dev/null
_devforge_post_batch() { echo "200"; }
devforge_upload_backlog
acked=$(ls "${HOME}/.claude/devforge-state/sess-C/outbox/acked"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
assert_eq "stale lock: flush proceeded" "2" "$acked"
cleanup_env

# ── Test 4: lock released after successful flush ──
echo "Test 4: lock released on exit"
new_env
seed_outbox "sess-D" 1 >/dev/null
_devforge_post_batch() { echo "200"; }
devforge_upload_backlog
lock_present=$([ -d "${HOME}/.claude/.devforge-flush.lock" ] && echo "yes" || echo "no")
assert_eq "lock removed after flush" "no" "$lock_present"
cleanup_env

echo ""
echo "Totale: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
