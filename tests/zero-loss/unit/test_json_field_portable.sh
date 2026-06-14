#!/usr/bin/env bash
# Unit tests: devforge_json_field portable JSON reader (node → python3 → degraded).
#
# Verifies:
#   1. With node+python3 available: extracts field correctly via node
#   2. With python3 masked: falls back to node successfully
#   3. With node masked: falls back to python3 successfully
#   4. With both masked: returns empty string
#   5. With both masked: emits telemetry_degraded event with reason=no_json_interpreter
#
# Task 02 — F2a: helper devforge_json_field (node→python3→degraded)

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
export HOME="$WORK"
mkdir -p "$HOME/.claude"
export DEVFORGE_SESSION_DIR="$WORK/session"
mkdir -p "$DEVFORGE_SESSION_DIR"
export DEVFORGE_LOG_FILE="$DEVFORGE_SESSION_DIR/activity.jsonl"
touch "$DEVFORGE_LOG_FILE"

# OLD_PATH defined in SETUP so it is always available under set -u,
# regardless of which tests run (TEST 2 restores it, TEST 3/4/5 also use it).
OLD_PATH="$PATH"

# Build a fake ~/.claude.json with known values
# NOTE: only the extracted field value is shown in test output — we never print the full file.
FAKE_CLAUDE_JSON="$WORK/fake_claude.json"
cat > "$FAKE_CLAUDE_JSON" <<'EOF'
{
  "oauthAccount": {
    "emailAddress": "test.user@example.com",
    "accountUuid": "uuid-1234",
    "organizationUuid": "org-uuid-5678",
    "organizationName": "TestOrg",
    "nullField": null
  },
  "identity": {
    "auth_email": "nested.test@example.com"
  },
  "top": {}
}
EOF
export DEVFORGE_CLAUDE_JSON="$FAKE_CLAUDE_JSON"

EXPECTED_EMAIL="test.user@example.com"
EXPECTED_NESTED="nested.test@example.com"

# --- shim directory for masking interpreters ---
SHIM_DIR="$WORK/shims"
mkdir -p "$SHIM_DIR"

# Shim that exits 127 (command not found equivalent)
make_shim() {
    local name="$1"
    printf '#!/usr/bin/env bash\nexit 127\n' > "$SHIM_DIR/$name"
    chmod +x "$SHIM_DIR/$name"
}

# Clear all shims between tests to avoid cross-contamination
clear_shims() {
    rm -f "$SHIM_DIR"/*
}

trap 'rm -rf "$WORK"' EXIT

# Source the logger (sourcing must not abort under set -euo pipefail)
# shellcheck disable=SC1090
source "$LOGGER" 2>/dev/null || { echo "FATAL: cannot source $LOGGER"; exit 2; }

# --------------------------------------------------------------
echo "TEST 1 — node+python3 both available: extracts field via node"
# No shims — use real PATH
result=$(devforge_json_field "$FAKE_CLAUDE_JSON" "oauthAccount.emailAddress" 2>/dev/null)
assert "T1: field extracted with both interpreters" "$result" "$EXPECTED_EMAIL"

# --------------------------------------------------------------
echo "TEST 2 — python3 masked: falls back to node"
clear_shims
make_shim python3
export PATH="$SHIM_DIR:$PATH"
result=$(devforge_json_field "$FAKE_CLAUDE_JSON" "oauthAccount.emailAddress" 2>/dev/null)
assert "T2: field extracted via node when python3 masked" "$result" "$EXPECTED_EMAIL"
export PATH="$OLD_PATH"

# --------------------------------------------------------------
echo "TEST 3 — node masked: falls back to python3"
clear_shims
make_shim node
export PATH="$SHIM_DIR:$PATH"
result=$(devforge_json_field "$FAKE_CLAUDE_JSON" "oauthAccount.emailAddress" 2>/dev/null)
assert "T3: field extracted via python3 when node masked" "$result" "$EXPECTED_EMAIL"
export PATH="$OLD_PATH"

# --------------------------------------------------------------
echo "TEST 4 — both node and python3 masked: returns empty string"
clear_shims
make_shim node
make_shim python3
export PATH="$SHIM_DIR:$PATH"
result=$(devforge_json_field "$FAKE_CLAUDE_JSON" "oauthAccount.emailAddress" 2>/dev/null)
assert "T4: empty string when both interpreters masked" "$result" ""
export PATH="$OLD_PATH"

# --------------------------------------------------------------
echo "TEST 5 — both masked: emits telemetry_degraded with reason=no_json_interpreter"
# Reset log and session state for clean event detection
rm -f "$DEVFORGE_LOG_FILE" && touch "$DEVFORGE_LOG_FILE"
rm -f "$DEVFORGE_SESSION_DIR/activity.jsonl" && touch "$DEVFORGE_SESSION_DIR/activity.jsonl"

# Use DEVFORGE_FORCE_BASH_FALLBACK=1 so _devforge_atomic_append uses the bash
# degraded path (printf >>) instead of calling python3 (which is shimmed here).
# This lets devforge_log write the telemetry_degraded event even when python3 is absent.
clear_shims
make_shim node
make_shim python3
export PATH="$SHIM_DIR:$PATH"
DEVFORGE_FORCE_BASH_FALLBACK=1 devforge_json_field "$FAKE_CLAUDE_JSON" "oauthAccount.emailAddress" >/dev/null 2>/dev/null || true
export PATH="$OLD_PATH"

# Check that telemetry_degraded event was emitted.
# DEVFORGE_LOG_FILE and session_activity resolve to the same path here
# ($DEVFORGE_SESSION_DIR/activity.jsonl) because this test sets them identically.
# The dual-loop is kept for correctness: devforge_log's same-path guard prevents
# duplicate lines, so summing counts across both files remains safe (no inflation).
degraded_count=0
for logf in "$DEVFORGE_LOG_FILE" "$DEVFORGE_SESSION_DIR/activity.jsonl"; do
    if [ -f "$logf" ]; then
        c=$(grep -c '"telemetry_degraded"' "$logf" 2>/dev/null || true)
        degraded_count=$((degraded_count + c))
    fi
done
reason_count=0
for logf in "$DEVFORGE_LOG_FILE" "$DEVFORGE_SESSION_DIR/activity.jsonl"; do
    if [ -f "$logf" ]; then
        c=$(grep -c '"no_json_interpreter"' "$logf" 2>/dev/null || true)
        reason_count=$((reason_count + c))
    fi
done

if [ "$degraded_count" -gt 0 ]; then
    echo "  PASS: T5a: telemetry_degraded event emitted"
    pass=$((pass + 1))
else
    echo "  FAIL: T5a: telemetry_degraded event NOT found in log"
    fail=$((fail + 1))
fi
if [ "$reason_count" -gt 0 ]; then
    echo "  PASS: T5b: reason=no_json_interpreter found in event"
    pass=$((pass + 1))
else
    echo "  FAIL: T5b: reason=no_json_interpreter NOT found in log"
    fail=$((fail + 1))
fi

# --------------------------------------------------------------
echo "TEST 6 — nested dotted path: identity.auth_email"
# Only requires python3 or node — use real PATH (no shims)
result=$(devforge_json_field "$FAKE_CLAUDE_JSON" "identity.auth_email" 2>/dev/null)
assert "T6: nested dotted path extraction" "$result" "$EXPECTED_NESTED"

# --------------------------------------------------------------
echo "TEST 7 — missing file: returns empty string without error"
result=$(devforge_json_field "$WORK/nonexistent.json" "oauthAccount.emailAddress" 2>/dev/null)
assert "T7: missing file returns empty string" "$result" ""

# --------------------------------------------------------------
echo "TEST 8 — explicit null value: returns empty string without crash"
# {"oauthAccount":{"nullField":null}} — null is falsy; function must return ""
result=$(devforge_json_field "$FAKE_CLAUDE_JSON" "oauthAccount.nullField" 2>/dev/null)
assert "T8: null value returns empty string" "$result" ""

# --------------------------------------------------------------
echo "TEST 9 — missing intermediate key in path: returns empty string without crash"
# {"top":{}} — "top.missing.deep" traverses into {} but "missing" key absent
result=$(devforge_json_field "$FAKE_CLAUDE_JSON" "top.missing.deep" 2>/dev/null)
assert "T9: missing intermediate key returns empty string" "$result" ""

# --------------------------------------------------------------
echo ""
echo "SUMMARY: $pass passed, $fail failed"
exit $fail
