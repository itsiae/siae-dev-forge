#!/usr/bin/env bash
# Improvement: verifica che devforge-context rispetti il budget di iniezione.
set -eu
PASS=0; FAIL=0
cd "$(git rev-parse --show-toplevel)"

# Requires: devforge-context hook exists (T11)
if [ ! -f hooks/devforge-context ]; then
    echo "SKIP — hooks/devforge-context not yet created (T11 pending)"
    exit 0
fi

_assert() {
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then echo "  PASS  $name"; PASS=$((PASS+1))
    else echo "  FAIL  $name"; FAIL=$((FAIL+1)); fi
}

echo "=== Budget: first injection <= 2048 bytes ==="
# Fresh state: no .devforge-last-injection-hash → first-time injection
TMPHOME=$(mktemp -d)
OUTPUT=$(HOME=$TMPHOME echo '{}' | bash hooks/devforge-context 2>/dev/null || true)
SIZE=$(printf '%s' "$OUTPUT" | wc -c | tr -d ' ')
if [ "$SIZE" -le 2048 ]; then
    echo "  PASS  first injection <= 2KB (actual=$SIZE)"; PASS=$((PASS+1))
else
    echo "  FAIL  first injection > 2KB (actual=$SIZE)"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== Diff-based: second invocation with same state returns {} ==="
# Run twice with same env → second must be empty (no diff)
SECOND=$(HOME=$TMPHOME echo '{}' | bash hooks/devforge-context 2>/dev/null || true)
SECOND_SIZE=$(printf '%s' "$SECOND" | wc -c | tr -d ' ')
if [ "$SECOND_SIZE" -le 20 ]; then  # empty JSON or zero
    echo "  PASS  second injection zero/minimal (actual=$SECOND_SIZE)"; PASS=$((PASS+1))
else
    echo "  FAIL  second injection not deduped (actual=$SECOND_SIZE)"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== Tier policy: default output NO EXTREMELY_IMPORTANT ==="
if echo "$OUTPUT" | grep -q "EXTREMELY_IMPORTANT"; then
    echo "  FAIL  default output contains EXTREMELY_IMPORTANT (should be tier-guarded)"; FAIL=$((FAIL+1))
else
    echo "  PASS  default output has no EXTREMELY_IMPORTANT"; PASS=$((PASS+1))
fi

rm -rf "$TMPHOME"
echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
