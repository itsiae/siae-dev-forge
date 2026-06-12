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

# ── Test 5: cap limits batches processed per invocation ──
echo "Test 5: cap caps processed batches"
new_env
export DEVFORGE_FLUSH_MAX_BATCHES=3
seed_outbox "sess-E" 10 >/dev/null
_devforge_post_batch() { echo "200"; }
devforge_upload_backlog
acked=$(ls "${HOME}/.claude/devforge-state/sess-E/outbox/acked"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
remaining=$(ls "${HOME}/.claude/devforge-state/sess-E/outbox"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
assert_eq "cap: exactly 3 acked" "3" "$acked"
assert_eq "cap: 7 remaining" "7" "$remaining"
unset DEVFORGE_FLUSH_MAX_BATCHES
cleanup_env

# ── Test 6: oldest-first ordering (lowest epoch in filename acked first) ──
echo "Test 6: oldest-first drain"
new_env
export DEVFORGE_FLUSH_MAX_BATCHES=1
ob="${HOME}/.claude/devforge-state/sess-F/outbox"
mkdir -p "$ob"
printf '{"old":1}\n' > "${ob}/batch-0000000001-pid.jsonl"
printf '{"new":1}\n' > "${ob}/batch-0000000009-pid.jsonl"
_devforge_post_batch() { echo "200"; }
devforge_upload_backlog
# The oldest (epoch ...001) must be the one acked
oldest_acked=$([ -f "${ob}/acked/batch-0000000001-pid.jsonl" ] && echo "yes" || echo "no")
assert_eq "oldest batch acked first" "yes" "$oldest_acked"
unset DEVFORGE_FLUSH_MAX_BATCHES
cleanup_env

# ── Test 7: non-200 increments tries, batch stays until K reached ──
echo "Test 7: tries counter increments, no premature failed/"
new_env
export DEVFORGE_FLUSH_MAX_TRIES=5
ob=$(seed_outbox "sess-G" 1)
_devforge_post_batch() { echo "500"; }
devforge_upload_backlog   # try 1
devforge_upload_backlog   # try 2
still_pending=$(ls "$ob"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
no_failed=$([ -d "$ob/failed" ] && ls "$ob/failed"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ' || echo 0)
assert_eq "after 2 non-200: still pending" "1" "$still_pending"
assert_eq "after 2 non-200: failed/ empty" "0" "$no_failed"
unset DEVFORGE_FLUSH_MAX_TRIES
cleanup_env

# ── Test 8: after K non-200, batch moves to failed/ and is not retried ──
echo "Test 8: dead-letter after K tries"
new_env
export DEVFORGE_FLUSH_MAX_TRIES=3
ob=$(seed_outbox "sess-H" 1)
_devforge_post_batch() { echo "500"; }
devforge_upload_backlog; devforge_upload_backlog; devforge_upload_backlog   # 3 tries
in_failed=$(ls "$ob/failed"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
in_outbox=$(ls "$ob"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
assert_eq "batch in failed/ after K" "1" "$in_failed"
assert_eq "batch no longer in outbox" "0" "$in_outbox"
# Not retried: a 4th call must not touch failed/ count
devforge_upload_backlog
still_failed=$(ls "$ob/failed"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
assert_eq "failed batch not retried" "1" "$still_failed"
unset DEVFORGE_FLUSH_MAX_TRIES
cleanup_env

# ── Test 9: success resets/removes the tries sidecar ──
echo "Test 9: 200 clears tries sidecar"
new_env
ob=$(seed_outbox "sess-I" 1)
batch_name=$(basename "$(ls "$ob"/batch-*.jsonl)")
_devforge_post_batch() { echo "500"; }
devforge_upload_backlog   # creates .tries-<name>
tries_after_fail=$([ -f "${ob}/.tries-${batch_name}" ] && echo "yes" || echo "no")
assert_eq "tries sidecar created on fail" "yes" "$tries_after_fail"
_devforge_post_batch() { echo "200"; }
devforge_upload_backlog   # success → ack + remove sidecar
sidecar_gone=$([ -f "${ob}/.tries-${batch_name}" ] && echo "no" || echo "yes")
assert_eq "tries sidecar removed on success" "yes" "$sidecar_gone"
cleanup_env

# Helper: backdate every file under a dir to N seconds ago (portable BSD/GNU)
backdate_dir() {
    local dir="$1" secs_ago="$2"
    local ep=$(( $(date +%s) - secs_ago ))
    local f
    find "$dir" -exec sh -c '
        if touch -d "@'"$ep"'" "$1" 2>/dev/null; then :; else
            touch -t "$(date -r '"$ep"' +%Y%m%d%H%M.%S 2>/dev/null)" "$1" 2>/dev/null || true
        fi
    ' _ {} \; 2>/dev/null
}

# ── Test 10: dead session (mtime > GC_DAYS) archived as a unit ──
echo "Test 10: dead-session outbox archived"
new_env
export DEVFORGE_FLUSH_GC_DAYS=14
export DEVFORGE_SID="sess-CURRENT"
ob=$(seed_outbox "sess-DEAD" 3)
backdate_dir "${HOME}/.claude/devforge-state/sess-DEAD" $(( 15 * 86400 ))
devforge_gc_dead_outboxes
archived=$([ -d "${HOME}/.claude/devforge-state-archive/sess-DEAD" ] && echo "yes" || echo "no")
gone_from_state=$([ -d "${HOME}/.claude/devforge-state/sess-DEAD" ] && echo "no" || echo "yes")
assert_eq "dead session archived" "yes" "$archived"
assert_eq "dead session removed from state" "yes" "$gone_from_state"
unset DEVFORGE_FLUSH_GC_DAYS DEVFORGE_SID
cleanup_env

# ── Test 11: recent session NOT archived ──
echo "Test 11: recent session preserved"
new_env
export DEVFORGE_FLUSH_GC_DAYS=14
export DEVFORGE_SID="sess-CURRENT"
seed_outbox "sess-RECENT" 2 >/dev/null   # fresh mtime
devforge_gc_dead_outboxes
still_there=$([ -d "${HOME}/.claude/devforge-state/sess-RECENT" ] && echo "yes" || echo "no")
assert_eq "recent session NOT archived" "yes" "$still_there"
unset DEVFORGE_FLUSH_GC_DAYS DEVFORGE_SID
cleanup_env

# ── Test 12: current session NEVER archived even if old ──
echo "Test 12: current session never archived"
new_env
export DEVFORGE_FLUSH_GC_DAYS=14
export DEVFORGE_SID="sess-CURRENT"
ob=$(seed_outbox "sess-CURRENT" 1)
backdate_dir "${HOME}/.claude/devforge-state/sess-CURRENT" $(( 30 * 86400 ))
devforge_gc_dead_outboxes
current_safe=$([ -d "${HOME}/.claude/devforge-state/sess-CURRENT" ] && echo "yes" || echo "no")
assert_eq "current session preserved despite age" "yes" "$current_safe"
unset DEVFORGE_FLUSH_GC_DAYS DEVFORGE_SID
cleanup_env

# ── Test 13: devforge_upload_logs invokes GC (wiring) ──
echo "Test 13: upload_logs triggers gc_maybe"
new_env
export DEVFORGE_SID="sess-CURRENT"
# Stub the heavy bits so we isolate the GC wiring
devforge_create_batch() { :; }
devforge_batch_global() { :; }
devforge_upload_backlog() { :; }
_GC_CALLED=0
devforge_gc_maybe() { _GC_CALLED=1; }
devforge_upload_logs
assert_eq "upload_logs calls gc_maybe" "1" "$_GC_CALLED"
unset DEVFORGE_SID
cleanup_env
# Re-source to restore real functions after stubbing
source "${PLUGIN_ROOT}/lib/telemetry-upload.sh"

# ── Test 14: zero-loss — failed upload never deletes a batch ──
echo "Test 14: zero-loss on failed upload"
new_env
export DEVFORGE_FLUSH_MAX_TRIES=99   # never dead-letter within this test
ob=$(seed_outbox "sess-Z" 4)
_devforge_post_batch() { echo "500"; }
devforge_upload_backlog
total=$(( $(ls "$ob"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ') + $([ -d "$ob/failed" ] && ls "$ob/failed"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ' || echo 0) ))
assert_eq "no batch lost on failed upload" "4" "$total"
unset DEVFORGE_FLUSH_MAX_TRIES
cleanup_env

echo ""
echo "Totale: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
