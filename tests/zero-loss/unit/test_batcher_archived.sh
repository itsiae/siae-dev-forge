#!/usr/bin/env bash
# Unit tests: devforge_create_batch must process both activity.jsonl
# and rotated activity-<ts>.archived.jsonl files. Per-file cursor tracking
# in outbox/.cursor-<basename>. Cleanup of fully-consumed archived files.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LOGGER="${REPO_ROOT}/lib/logger.sh"
UPLOADER="${REPO_ROOT}/lib/telemetry-upload.sh"

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
mkdir -p "$DEVFORGE_SESSION_DIR/outbox"
trap 'export HOME="$HOME_BAK"; rm -rf "$WORK"' EXIT

source "$LOGGER" 2>/dev/null
source "$UPLOADER" 2>/dev/null

# --------------------------------------------------------------
echo "TEST 1 — batch includes lines from archived files"
# Setup: create archived file with 3 events + current activity.jsonl with 2 events
echo '{"event":"e1"}' > "$DEVFORGE_SESSION_DIR/activity-1000.archived.jsonl"
echo '{"event":"e2"}' >> "$DEVFORGE_SESSION_DIR/activity-1000.archived.jsonl"
echo '{"event":"e3"}' >> "$DEVFORGE_SESSION_DIR/activity-1000.archived.jsonl"
echo '{"event":"e4"}' > "$DEVFORGE_SESSION_DIR/activity.jsonl"
echo '{"event":"e5"}' >> "$DEVFORGE_SESSION_DIR/activity.jsonl"

devforge_create_batch 2>/dev/null

# Concatenate all batch files into a single stream and count event types
all_lines=""
for batch in "$DEVFORGE_SESSION_DIR/outbox"/batch-*.jsonl; do
    [ -f "$batch" ] && all_lines="${all_lines}$(cat "$batch")"$'\n'
done

# Verify all 5 events are in the produced batches
e1_count=$(echo "$all_lines" | grep -c '"event":"e1"' || true)
e3_count=$(echo "$all_lines" | grep -c '"event":"e3"' || true)
e5_count=$(echo "$all_lines" | grep -c '"event":"e5"' || true)

assert "T1: e1 (from archived) in batch" "$e1_count" "1"
assert "T1b: e3 (from archived) in batch" "$e3_count" "1"
assert "T1c: e5 (from current) in batch" "$e5_count" "1"

# --------------------------------------------------------------
echo "TEST 2 — second batch run does NOT re-include already-batched lines"
# Add 2 new lines to current activity, run batcher again
rm -f "$DEVFORGE_SESSION_DIR/outbox"/batch-*.jsonl
echo '{"event":"e6"}' >> "$DEVFORGE_SESSION_DIR/activity.jsonl"
echo '{"event":"e7"}' >> "$DEVFORGE_SESSION_DIR/activity.jsonl"

devforge_create_batch 2>/dev/null

new_batch_content=""
for batch in "$DEVFORGE_SESSION_DIR/outbox"/batch-*.jsonl; do
    [ -f "$batch" ] && new_batch_content="${new_batch_content}$(cat "$batch")"$'\n'
done

# e1 (already batched in archived) should NOT appear again
e1_again=$(echo "$new_batch_content" | grep -c '"event":"e1"' || true)
e6_count=$(echo "$new_batch_content" | grep -c '"event":"e6"' || true)
assert "T2: e1 NOT re-batched" "$e1_again" "0"
assert "T2b: e6 (new line) IS batched" "$e6_count" "1"

# --------------------------------------------------------------
echo "TEST 3 — fully-consumed archived files are removed"
# After the previous runs, activity-1000.archived.jsonl should be fully consumed
# (3 lines, all 3 in batch). It should be deleted at next batcher run.
devforge_create_batch 2>/dev/null  # idempotent run to trigger cleanup

archived_remaining=$(find "$DEVFORGE_SESSION_DIR" -name "activity-*.archived.jsonl" 2>/dev/null | wc -l | tr -d ' ')
assert "T3: archived file removed after full consumption" "$archived_remaining" "0"

# --------------------------------------------------------------
echo ""
echo "SUMMARY: $pass passed, $fail failed"
exit $fail
