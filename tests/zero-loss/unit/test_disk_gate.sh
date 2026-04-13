#!/usr/bin/env bash
# Unit tests for disk space gate in lib/logger.sh.
# When free disk space < 100MB, devforge_log MUST skip the write
# and append a timestamp to ~/.claude/.devforge-disk-full-events.tmp
# for later recovery (emitted as event when the next flush succeeds).
#
# Implementation uses a mockable df function: _devforge_free_kb.
# Tests override _devforge_free_kb to simulate low disk conditions.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LOGGER="${REPO_ROOT}/lib/logger.sh"

fail=0
pass=0

assert() {
    local name="$1" actual="$2" expected="$3"
    if [ "$actual" = "$expected" ]; then
        echo "  PASS: $name"; pass=$((pass + 1))
    else
        echo "  FAIL: $name — expected '$expected' got '$actual'"; fail=$((fail + 1))
    fi
}

# --- setup isolated workspace ---
WORK=$(mktemp -d)
HOME_BAK="$HOME"
export HOME="$WORK"  # redirect .devforge-* sentinels to tmp
mkdir -p "$HOME/.claude"
export DEVFORGE_SESSION_DIR="$WORK/session"
mkdir -p "$DEVFORGE_SESSION_DIR"
export DEVFORGE_LOG_FILE="$DEVFORGE_SESSION_DIR/activity.jsonl"
touch "$DEVFORGE_LOG_FILE"
trap 'export HOME="$HOME_BAK"; rm -rf "$WORK"' EXIT

# shellcheck disable=SC1090
source "$LOGGER" 2>/dev/null || { echo "FATAL: cannot source $LOGGER"; exit 2; }

# --------------------------------------------------------------
echo "TEST 1 — disk gate function exists"
type _devforge_free_kb >/dev/null 2>&1
assert "T1: _devforge_free_kb is defined" "$?" "0"

# --------------------------------------------------------------
echo "TEST 2 — devforge_log skips write when free < 100MB"
# Mock low disk
_devforge_free_kb() { echo "50000"; }  # 50MB free
rm -f "$DEVFORGE_LOG_FILE" && touch "$DEVFORGE_LOG_FILE"
devforge_log "test_event" "success" '{}' 2>/dev/null
size_after_low=$(stat -f%z "$DEVFORGE_LOG_FILE" 2>/dev/null || stat -c%s "$DEVFORGE_LOG_FILE")
assert "T2: activity.jsonl empty when disk full" "$size_after_low" "0"

# --------------------------------------------------------------
echo "TEST 3 — disk-full event queued in tmp file for recovery"
# After the aborted write, a timestamp line should be in the recovery file
assert "T3: disk-full recovery file exists" \
    "$([ -f "$HOME/.claude/.devforge-disk-full-events.tmp" ] && echo yes || echo no)" "yes"
line_count=$(wc -l < "$HOME/.claude/.devforge-disk-full-events.tmp" | tr -d ' ')
assert "T3b: exactly one recovery entry" "$line_count" "1"

# --------------------------------------------------------------
echo "TEST 4 — devforge_log writes normally when free >= 100MB"
_devforge_free_kb() { echo "500000"; }  # 500MB free
rm -f "$DEVFORGE_LOG_FILE" && touch "$DEVFORGE_LOG_FILE"
devforge_log "test_event" "success" '{}' 2>/dev/null
size_after_ok=$(stat -f%z "$DEVFORGE_LOG_FILE" 2>/dev/null || stat -c%s "$DEVFORGE_LOG_FILE")
# Non-zero = write happened
if [ "$size_after_ok" -gt 0 ]; then
    echo "  PASS: T4: activity.jsonl written when disk ok (size=$size_after_ok)"
    pass=$((pass + 1))
else
    echo "  FAIL: T4: activity.jsonl not written (size=$size_after_ok)"
    fail=$((fail + 1))
fi

# --------------------------------------------------------------
echo ""
echo "SUMMARY: $pass passed, $fail failed"
exit $fail
