#!/usr/bin/env bash
# Integration test: devforge_log in lib/logger.sh MUST route writes through
# lib/atomic_write.py (not raw printf >>) to guarantee lock + fsync.
#
# Evidence:
#   1. After a devforge_log call, .activity.lock exists in DEVFORGE_SESSION_DIR.
#   2. activity.jsonl contains the logged event as valid JSON (no truncation).
#   3. A burst of concurrent devforge_log calls produces N valid lines, zero truncation.

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
# PLUGIN_ROOT needed by logger to find atomic_write.py
export PLUGIN_ROOT="$REPO_ROOT"
trap 'export HOME="$HOME_BAK"; rm -rf "$WORK"' EXIT

# shellcheck disable=SC1090
source "$LOGGER" 2>/dev/null || { echo "FATAL: cannot source $LOGGER"; exit 2; }

# --------------------------------------------------------------
echo "TEST 1 — devforge_log creates .activity.lock (evidence of atomic_write usage)"
devforge_log "test_logger_integration" "success" '{"marker":"A9b"}' 2>/dev/null
assert "T1: .activity.lock exists after log" \
    "$([ -f "$DEVFORGE_SESSION_DIR/.activity.lock" ] && echo yes || echo no)" "yes"

# --------------------------------------------------------------
echo "TEST 2 — activity.jsonl contains valid JSON line with the event"
line_count=$(wc -l < "$DEVFORGE_LOG_FILE" | tr -d ' ')
assert "T2: one line written" "$line_count" "1"

# Verify the written line is valid JSON and contains the marker
if python3 -c "
import json, sys
line = open('$DEVFORGE_LOG_FILE').read().strip()
obj = json.loads(line)
assert obj.get('event') == 'test_logger_integration', f'wrong event: {obj.get(\"event\")}'
assert obj.get('meta', {}).get('marker') == 'A9b', f'wrong marker: {obj.get(\"meta\")}'
" 2>/dev/null; then
    echo "  PASS: T2b: line is valid JSON with event+marker"
    pass=$((pass + 1))
else
    echo "  FAIL: T2b: line is NOT valid JSON or missing fields"
    fail=$((fail + 1))
fi

# --------------------------------------------------------------
echo "TEST 3 — 20 concurrent devforge_log calls produce 20 valid JSON lines"
rm -f "$DEVFORGE_LOG_FILE" "$DEVFORGE_SESSION_DIR/.activity.lock"
touch "$DEVFORGE_LOG_FILE"

# Fork 20 background processes, each calls devforge_log once
for i in $(seq 1 20); do
    (
        # shellcheck disable=SC1090
        source "$LOGGER" 2>/dev/null
        devforge_log "concurrent_test_$i" "success" "{\"idx\":$i}" 2>/dev/null
    ) &
done
wait

final_line_count=$(wc -l < "$DEVFORGE_LOG_FILE" | tr -d ' ')
assert "T3: 20 lines after concurrent writes" "$final_line_count" "20"

# Every line must parse as valid JSON
if python3 -c "
import json, sys
lines = open('$DEVFORGE_LOG_FILE').read().splitlines()
for i, line in enumerate(lines):
    try: json.loads(line)
    except: print(f'line {i} is malformed: {line[:80]}'); sys.exit(1)
" 2>/dev/null; then
    echo "  PASS: T3b: all 20 lines are valid JSON (no truncation)"
    pass=$((pass + 1))
else
    echo "  FAIL: T3b: at least one line is truncated/malformed"
    fail=$((fail + 1))
fi

# --------------------------------------------------------------
# --------------------------------------------------------------
echo "TEST 4 — devforge_log_timed dual-write dedup (CRITICAL fix iter-5)"
rm -f "$DEVFORGE_LOG_FILE" "$DEVFORGE_SESSION_DIR/.activity.lock"
touch "$DEVFORGE_LOG_FILE"
START_NS=$(date +%s%N 2>/dev/null || echo 0)
devforge_log_timed "test_timed" "success" "$START_NS" '{"x":1}' 2>/dev/null
timed_lines=$(wc -l < "$DEVFORGE_LOG_FILE" | tr -d ' ')
assert "T4: devforge_log_timed produces 1 line (no dual-write duplicate)" "$timed_lines" "1"

# --------------------------------------------------------------
echo ""
echo "SUMMARY: $pass passed, $fail failed"
exit $fail
