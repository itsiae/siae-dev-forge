#!/usr/bin/env bash
# Unit tests for activity.jsonl rotation behavior in lib/logger.sh.
# Tests the NEW behavior (PR-A target):
#   - threshold 5MB (was 50MB)
#   - pattern `activity-<unix_ts>.archived.jsonl` (was single `.1` backup)
#   - cap totale 50MB on activity + archived, drop oldest archived
#
# RED phase: fails against current logger.sh which has 50MB + `.1`.
# GREEN phase: passes after _devforge_check_rotation is updated.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LOGGER="${REPO_ROOT}/lib/logger.sh"

fail=0
pass=0

assert() {
    local name="$1"
    local actual="$2"
    local expected="$3"
    if [ "$actual" = "$expected" ]; then
        echo "  PASS: $name"
        pass=$((pass + 1))
    else
        echo "  FAIL: $name — expected '$expected' got '$actual'"
        fail=$((fail + 1))
    fi
}

# --- setup isolated workspace ---
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
export DEVFORGE_SESSION_DIR="$WORK"
export DEVFORGE_LOG_FILE="$WORK/activity.jsonl"

# --- source logger under test ---
# shellcheck disable=SC1090
source "$LOGGER" 2>/dev/null || { echo "FATAL: cannot source $LOGGER"; exit 2; }

# --------------------------------------------------------------
echo "TEST 1 — rotation threshold is 5MB (not 50MB)"
# Create a file just over 5MB
dd if=/dev/zero of="$DEVFORGE_LOG_FILE" bs=1024 count=5200 2>/dev/null
_devforge_check_rotation
assert "T1: activity.jsonl size 0 after rotation at 5MB" \
    "$(stat -f%z "$DEVFORGE_LOG_FILE" 2>/dev/null || stat -c%s "$DEVFORGE_LOG_FILE" 2>/dev/null)" \
    "0"

# --------------------------------------------------------------
echo "TEST 2 — rotated file uses archived-<ts>.jsonl pattern (not .1)"
archived_count=$(find "$WORK" -name "activity-*.archived.jsonl" 2>/dev/null | wc -l | tr -d ' ')
assert "T2: one archived file created with pattern activity-<ts>.archived.jsonl" \
    "$archived_count" "1"

legacy_count=$(find "$WORK" -name "activity.jsonl.1" 2>/dev/null | wc -l | tr -d ' ')
assert "T2b: no legacy .1 backup is created" \
    "$legacy_count" "0"

# --------------------------------------------------------------
echo "TEST 3 — no rotation below 5MB threshold"
rm -f "$WORK"/*.jsonl "$WORK"/*.archived.jsonl
dd if=/dev/zero of="$DEVFORGE_LOG_FILE" bs=1024 count=4000 2>/dev/null
_devforge_check_rotation
size_after=$(stat -f%z "$DEVFORGE_LOG_FILE" 2>/dev/null || stat -c%s "$DEVFORGE_LOG_FILE")
# Should NOT rotate at 4MB
assert "T3: file unchanged below 5MB threshold" \
    "$size_after" "4096000"

archived_count_3=$(find "$WORK" -name "activity-*.archived.jsonl" 2>/dev/null | wc -l | tr -d ' ')
assert "T3b: no archived file created below threshold" \
    "$archived_count_3" "0"

# --------------------------------------------------------------
echo "TEST 4 — multiple rotations create multiple archived files"
rm -f "$WORK"/*.jsonl "$WORK"/*.archived.jsonl
for i in 1 2; do
    dd if=/dev/zero of="$DEVFORGE_LOG_FILE" bs=1024 count=5200 2>/dev/null
    _devforge_check_rotation
    sleep 1  # ensure different timestamps
done
multi_count=$(find "$WORK" -name "activity-*.archived.jsonl" 2>/dev/null | wc -l | tr -d ' ')
assert "T4: two archived files after two rotations" \
    "$multi_count" "2"

# --------------------------------------------------------------
echo ""
echo "SUMMARY: $pass passed, $fail failed"
exit $fail
