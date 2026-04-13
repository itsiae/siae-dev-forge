#!/usr/bin/env bash
# Unit tests for NTP clock skew detection.
# Design edge cases #7 (clock skew >1h) and #18 (NTP unreachable).
#
# Function under test: _devforge_check_clock_skew <ntp_epoch>
#   - Returns 0 and creates clock-skew.json if |skew| > 3600s
#   - Returns 0 without side effects if skew within bounds
#   - Returns 0 without side effects if arg is empty (NTP unreachable)

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

WORK=$(mktemp -d)
HOME_BAK="$HOME"
export HOME="$WORK"
mkdir -p "$HOME/.claude"
export DEVFORGE_SESSION_DIR="$WORK/session"
mkdir -p "$DEVFORGE_SESSION_DIR"
export DEVFORGE_LOG_FILE="$DEVFORGE_SESSION_DIR/activity.jsonl"
touch "$DEVFORGE_LOG_FILE"
export PLUGIN_ROOT="$REPO_ROOT"
trap 'export HOME="$HOME_BAK"; rm -rf "$WORK"' EXIT

source "$LOGGER" 2>/dev/null

# --------------------------------------------------------------
echo "TEST 1 — function _devforge_check_clock_skew exists"
type _devforge_check_clock_skew >/dev/null 2>&1
assert "T1: _devforge_check_clock_skew is defined" "$?" "0"

[ "$fail" -gt 0 ] && { echo ""; echo "SUMMARY: $pass passed, $fail failed"; exit $fail; }

# --------------------------------------------------------------
echo "TEST 2 — skew within tolerance (30s) does NOT create flag file"
rm -f "$DEVFORGE_SESSION_DIR/clock-skew.json"
local_ts=$(date -u +%s)
ntp_ts=$((local_ts - 30))  # NTP 30s behind local — within tolerance
_devforge_check_clock_skew "$ntp_ts"
assert "T2: clock-skew.json NOT created for 30s skew" \
    "$([ -f "$DEVFORGE_SESSION_DIR/clock-skew.json" ] && echo yes || echo no)" "no"

# --------------------------------------------------------------
echo "TEST 3 — skew > 3600s creates clock-skew.json with force_received_at:true"
rm -f "$DEVFORGE_SESSION_DIR/clock-skew.json"
local_ts=$(date -u +%s)
ntp_ts=$((local_ts - 7200))  # 2h skew
_devforge_check_clock_skew "$ntp_ts"
assert "T3: clock-skew.json created for 2h skew" \
    "$([ -f "$DEVFORGE_SESSION_DIR/clock-skew.json" ] && echo yes || echo no)" "yes"

# Verify JSON content
if python3 -c "
import json
d = json.load(open('$DEVFORGE_SESSION_DIR/clock-skew.json'))
assert d.get('force_received_at') is True, f'force_received_at not true: {d}'
assert abs(d.get('clock_skew_sec', 0)) >= 3600, f'skew not >=3600: {d}'
" 2>/dev/null; then
    echo "  PASS: T3b: JSON has force_received_at:true + clock_skew_sec"
    pass=$((pass + 1))
else
    echo "  FAIL: T3b: JSON content malformed"
    fail=$((fail + 1))
fi

# --------------------------------------------------------------
echo "TEST 4 — negative skew (local ahead of NTP) also detected"
rm -f "$DEVFORGE_SESSION_DIR/clock-skew.json"
local_ts=$(date -u +%s)
ntp_ts=$((local_ts + 7200))  # NTP 2h ahead → local is 2h behind
_devforge_check_clock_skew "$ntp_ts"
assert "T4: clock-skew.json created for -2h skew" \
    "$([ -f "$DEVFORGE_SESSION_DIR/clock-skew.json" ] && echo yes || echo no)" "yes"

# --------------------------------------------------------------
echo "TEST 5 — empty ntp_epoch (NTP unreachable) is no-op"
rm -f "$DEVFORGE_SESSION_DIR/clock-skew.json"
_devforge_check_clock_skew ""
assert "T5: no file created when NTP is unreachable (empty input)" \
    "$([ -f "$DEVFORGE_SESSION_DIR/clock-skew.json" ] && echo yes || echo no)" "no"

# --------------------------------------------------------------
echo ""
echo "SUMMARY: $pass passed, $fail failed"
exit $fail
