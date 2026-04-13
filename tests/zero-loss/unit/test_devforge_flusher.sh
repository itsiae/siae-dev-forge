#!/usr/bin/env bash
# Unit tests for hooks/devforge-flusher.
# The flusher is a PostToolUse hook that triggers an opportunistic
# telemetry upload with a 60s cooldown to avoid flooding the API.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
FLUSHER="${REPO_ROOT}/hooks/devforge-flusher"

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
trap 'export HOME="$HOME_BAK"; rm -rf "$WORK"' EXIT

LAST_FLUSH_FILE="$HOME/.claude/.devforge-last-flush"

# --------------------------------------------------------------
echo "TEST 1 — devforge-flusher file exists and is executable"
assert "T1: hooks/devforge-flusher exists" \
    "$([ -f "$FLUSHER" ] && echo yes || echo no)" "yes"
assert "T1b: hooks/devforge-flusher is executable" \
    "$([ -x "$FLUSHER" ] && echo yes || echo no)" "yes"

# Stop here if file doesn't exist (RED phase)
[ ! -f "$FLUSHER" ] && { echo ""; echo "SUMMARY: $pass passed, $fail failed"; exit $fail; }

# --------------------------------------------------------------
echo "TEST 2 — first execution sets sentinel timestamp"
rm -f "$LAST_FLUSH_FILE"
bash "$FLUSHER" 2>/dev/null
assert "T2: .devforge-last-flush created" \
    "$([ -f "$LAST_FLUSH_FILE" ] && echo yes || echo no)" "yes"

# Stored value must be a unix timestamp (10-digit number)
ts_value=$(cat "$LAST_FLUSH_FILE" 2>/dev/null)
if [[ "$ts_value" =~ ^[0-9]{10}$ ]]; then
    echo "  PASS: T2b: sentinel contains valid unix ts ($ts_value)"
    pass=$((pass + 1))
else
    echo "  FAIL: T2b: sentinel content not a unix ts: '$ts_value'"
    fail=$((fail + 1))
fi

# --------------------------------------------------------------
echo "TEST 3 — second execution within cooldown 60s does NOT update sentinel"
old_ts=$(cat "$LAST_FLUSH_FILE")
sleep 1
bash "$FLUSHER" 2>/dev/null
new_ts=$(cat "$LAST_FLUSH_FILE")
assert "T3: sentinel timestamp unchanged within cooldown" \
    "$new_ts" "$old_ts"

# --------------------------------------------------------------
echo "TEST 4 — execution after cooldown updates sentinel"
# Simulate cooldown expiry: backdate the sentinel to 70 seconds ago
backdated=$(($(date +%s) - 70))
echo "$backdated" > "$LAST_FLUSH_FILE"
bash "$FLUSHER" 2>/dev/null
new_ts_4=$(cat "$LAST_FLUSH_FILE")
if [ "$new_ts_4" -gt "$backdated" ]; then
    echo "  PASS: T4: sentinel updated after cooldown expiry"
    pass=$((pass + 1))
else
    echo "  FAIL: T4: sentinel not updated (was $backdated, now $new_ts_4)"
    fail=$((fail + 1))
fi

# --------------------------------------------------------------
echo ""
echo "SUMMARY: $pass passed, $fail failed"
exit $fail
