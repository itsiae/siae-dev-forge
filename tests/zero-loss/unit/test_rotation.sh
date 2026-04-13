#!/usr/bin/env bash
# Unit tests for activity.jsonl rotation + 50MB cap.
# Post-PR-A review: rotation is now ATOMIC inside atomic_write.py (under lock).
# The bash _devforge_check_rotation keeps only the 50MB cap enforcement,
# which drops ONLY fully-consumed archived files (cursor >= size).
# Rotation behavior itself is tested in test_atomic_write.py (Python).

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LOGGER="${REPO_ROOT}/lib/logger.sh"

fail=0
pass=0

assert() {
    local name="$1" actual="$2" expected="$3"
    if [ "$actual" = "$expected" ]; then
        echo "  PASS: $name"
        pass=$((pass + 1))
    else
        echo "  FAIL: $name — expected '$expected' got '$actual'"
        fail=$((fail + 1))
    fi
}

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
export DEVFORGE_SESSION_DIR="$WORK"
mkdir -p "$WORK/outbox"
export DEVFORGE_LOG_FILE="$WORK/activity.jsonl"

# shellcheck disable=SC1090
source "$LOGGER" 2>/dev/null || { echo "FATAL: cannot source $LOGGER"; exit 2; }

# --------------------------------------------------------------
echo "TEST 1 — 50MB cap drops archived with cursor == size (fully consumed)"
# Create 11 fake archived files of ~5MB each = 55MB total
for i in 1 2 3 4 5 6 7 8 9 10 11; do
    dd if=/dev/zero of="$WORK/activity-$i.archived.jsonl" bs=1024 count=5000 2>/dev/null
    # Mark each as fully consumed: cursor == file size
    size=$(stat -f%z "$WORK/activity-$i.archived.jsonl" 2>/dev/null || stat -c%s "$WORK/activity-$i.archived.jsonl")
    echo "$size" > "$WORK/outbox/.cursor-activity-$i.archived.jsonl"
    sleep 0.01  # ensure mtime differs
done
echo "{}" > "$DEVFORGE_LOG_FILE"
_devforge_check_rotation
remaining=$(find "$WORK" -maxdepth 1 -name "activity-*.archived.jsonl" 2>/dev/null | wc -l | tr -d ' ')
# Started with 11 × 5MB = 55MB; cap 50MB → at least 1 dropped, stay ≤ 11
if [ "$remaining" -lt 11 ]; then
    echo "  PASS: T1: fully-consumed archived dropped (remaining=$remaining)"
    pass=$((pass + 1))
else
    echo "  FAIL: T1: cap not enforced on consumed archived (remaining=$remaining)"
    fail=$((fail + 1))
fi

# --------------------------------------------------------------
echo "TEST 2 — 50MB cap PRESERVES archived with cursor < size (not uploaded)"
# Reset: create 11 archived but ALL with cursor=0 (not yet batched)
rm -rf "$WORK"/*.archived.jsonl "$WORK/outbox"/.cursor-*
for i in 1 2 3 4 5 6 7 8 9 10 11; do
    dd if=/dev/zero of="$WORK/activity-$i.archived.jsonl" bs=1024 count=5000 2>/dev/null
    echo "0" > "$WORK/outbox/.cursor-activity-$i.archived.jsonl"  # cursor=0 → not consumed
    sleep 0.01
done
echo "{}" > "$DEVFORGE_LOG_FILE"
_devforge_check_rotation
remaining_unsafe=$(find "$WORK" -maxdepth 1 -name "activity-*.archived.jsonl" 2>/dev/null | wc -l | tr -d ' ')
assert "T2: ALL 11 archived preserved (prefer disk pressure over data loss)" \
    "$remaining_unsafe" "11"

# --------------------------------------------------------------
echo "TEST 3 — 50MB cap PRESERVES archived with NO cursor file (missing metadata)"
rm -rf "$WORK"/*.archived.jsonl "$WORK/outbox"/.cursor-*
for i in 1 2 3 4 5 6 7 8 9 10 11; do
    dd if=/dev/zero of="$WORK/activity-$i.archived.jsonl" bs=1024 count=5000 2>/dev/null
    # NO cursor file created — missing metadata, assume not consumed
    sleep 0.01
done
echo "{}" > "$DEVFORGE_LOG_FILE"
_devforge_check_rotation
remaining_nocursor=$(find "$WORK" -maxdepth 1 -name "activity-*.archived.jsonl" 2>/dev/null | wc -l | tr -d ' ')
assert "T3: archived without cursor file preserved" \
    "$remaining_nocursor" "11"

# --------------------------------------------------------------
echo "TEST 4 — rotation is atomic (via atomic_write.py with rotate_at_bytes)"
# Smoke test: verify that atomic_write.py does rotation properly.
# Full coverage is in test_atomic_write.py (Python).
rm -rf "$WORK"/*.archived.jsonl "$WORK/outbox"/.cursor-* "$DEVFORGE_LOG_FILE"
# Fill activity to 6KB
dd if=/dev/zero of="$DEVFORGE_LOG_FILE" bs=1024 count=6 2>/dev/null
# Invoke atomic_write.py with rotate_at 5000 bytes
python3 "${REPO_ROOT}/lib/atomic_write.py" append "$DEVFORGE_LOG_FILE" '{"after":"rotate"}' 5000
archived_count=$(find "$WORK" -maxdepth 1 -name "activity-*.archived.jsonl" 2>/dev/null | wc -l | tr -d ' ')
assert "T4: atomic_write.py rotates when size > threshold" "$archived_count" "1"
current_content=$(cat "$DEVFORGE_LOG_FILE" 2>/dev/null)
assert "T4b: current file has only the new line" "$current_content" '{"after":"rotate"}'

# --------------------------------------------------------------
echo ""
echo "SUMMARY: $pass passed, $fail failed"
exit $fail
