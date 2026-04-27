#!/usr/bin/env bash
set -eu
cd "$(git rev-parse --show-toplevel)"
PASS=0; FAIL=0
_assert() {
    local name="$1"; local cmd="$2"
    if eval "$cmd" >/dev/null 2>&1; then echo "  PASS  $name"; PASS=$((PASS+1))
    else echo "  FAIL  $name"; FAIL=$((FAIL+1)); fi
}

HOOK=hooks/devforge-context
export HOME=$(mktemp -d); mkdir -p "$HOME/.claude"
trap 'rm -rf "$HOME"' EXIT

_assert "hook exists and executable" "[ -x $HOOK ]"

echo ""
echo "=== Budget: first emission <= 2048 bytes ==="
OUT1=$(echo '{}' | bash $HOOK 2>/dev/null || true)
SIZE1=$(printf '%s' "$OUT1" | wc -c | tr -d ' ')
_assert "first emission <= 2048 bytes (actual=$SIZE1)" "[ $SIZE1 -le 2048 ]"
_assert "first emission non-empty" "[ $SIZE1 -gt 10 ]"

echo ""
echo "=== Diff-based: 2nd emission same state = empty/minimal ==="
OUT2=$(echo '{}' | bash $HOOK 2>/dev/null || true)
SIZE2=$(printf '%s' "$OUT2" | wc -c | tr -d ' ')
_assert "2nd same-state emission <= 20 bytes (actual=$SIZE2)" "[ $SIZE2 -le 20 ]"

echo ""
echo "=== Diff-based: hash changes trigger new emission ==="
# Simulate state change: touch session-skills
echo "siae-tdd" > "$HOME/.claude/.devforge-session-skills"
OUT3=$(echo '{}' | bash $HOOK 2>/dev/null || true)
SIZE3=$(printf '%s' "$OUT3" | wc -c | tr -d ' ')
_assert "state change re-emits (actual=$SIZE3)" "[ $SIZE3 -gt 20 ]"

echo ""
echo "=== Tier policy: default NO EXTREMELY_IMPORTANT ==="
OUT_DEFAULT=$(echo '{}' | bash $HOOK 2>/dev/null || true)
_assert "default output has no EXTREMELY_IMPORTANT tag" \
    "! echo '$OUT_DEFAULT' | grep -q EXTREMELY_IMPORTANT"

echo ""
echo "=== Telemetry: logs prompt_injection_emitted event ==="
export DEVFORGE_LOG_FILE="$HOME/.claude/test-activity.jsonl"
: > "$DEVFORGE_LOG_FILE"
# trigger a new emission (change state)
rm -f "$HOME/.claude/.devforge-session-skills"
echo '{}' | bash $HOOK >/dev/null 2>&1 || true
_assert "prompt_injection_emitted event logged" \
    "grep -q prompt_injection_emitted $DEVFORGE_LOG_FILE"

echo ""
echo "=== JSON output valid ==="
OUT_JSON=$(echo '{}' | bash $HOOK 2>/dev/null || true)
if [ -n "$OUT_JSON" ] && [ "$OUT_JSON" != "{}" ]; then
    echo "$OUT_JSON" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null
    _assert "output is valid JSON" "[ $? -eq 0 ]"
else
    echo "  SKIP  output is minimal, JSON check skipped"
fi

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
