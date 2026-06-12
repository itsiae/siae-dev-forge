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

echo ""
echo "Totale: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
