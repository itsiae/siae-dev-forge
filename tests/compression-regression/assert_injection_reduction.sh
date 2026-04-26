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
# Fresh state: no .devforge-last-injection-hash → first-time injection.
# NB: prefix-assignment `HOME=$X echo '{}' | bash hook` applies HOME only to
# `echo` (left of pipe), leaving the subshell running the hook unaffected.
# Use `env HOME=$TMPHOME bash hook` to actually override HOME for the hook.
TMPHOME=$(mktemp -d)
trap 'rm -rf "$TMPHOME"' EXIT
OUTPUT=$(echo '{}' | env HOME="$TMPHOME" bash hooks/devforge-context 2>/dev/null || true)
SIZE=$(printf '%s' "$OUTPUT" | wc -c | tr -d ' ')
if [ "$SIZE" -le 2048 ]; then
    echo "  PASS  first injection <= 2KB (actual=$SIZE)"; PASS=$((PASS+1))
else
    echo "  FAIL  first injection > 2KB (actual=$SIZE)"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== Diff-based: second invocation with same state returns {} ==="
# Run twice with same env → second must be empty (no diff). Uses `env HOME=...`
# so the hook subshell sees the isolated HOME (see note above).
SECOND=$(echo '{}' | env HOME="$TMPHOME" bash hooks/devforge-context 2>/dev/null || true)
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

echo ""
echo "=== Design doc mtime triggers re-emission (PR #215 MAJOR #2 fix) ==="
# Seed a design doc in isolated HOME repo. When mtime changes, compute_state_hash
# must yield a different value → next invocation must re-emit (not dedup to empty).
TMP_REPO=$(mktemp -d)
(
    cd "$TMP_REPO"
    git init -q
    mkdir -p docs/plans hooks lib
    # Seed design doc
    echo "initial" > docs/plans/test-design.md
    # Symlink hook + lib so the hook finds logger.sh + plugin root
    ln -s "$(cd - >/dev/null; git rev-parse --show-toplevel)/hooks/devforge-context" hooks/devforge-context
    ln -s "$(cd - >/dev/null; git rev-parse --show-toplevel)/lib" lib-link
    rm -rf lib && ln -s lib-link lib
    THIRD_HOME=$(mktemp -d)
    # First emission — baseline
    FIRST=$(echo '{}' | env HOME="$THIRD_HOME" bash hooks/devforge-context 2>/dev/null || true)
    FIRST_SIZE=$(printf '%s' "$FIRST" | wc -c | tr -d ' ')
    # Second with no change → should be deduped
    SAME=$(echo '{}' | env HOME="$THIRD_HOME" bash hooks/devforge-context 2>/dev/null || true)
    SAME_SIZE=$(printf '%s' "$SAME" | wc -c | tr -d ' ')
    # Mutate design doc mtime → different hash → re-emit
    sleep 1
    echo "revised" >> docs/plans/test-design.md
    THIRD=$(echo '{}' | env HOME="$THIRD_HOME" bash hooks/devforge-context 2>/dev/null || true)
    THIRD_SIZE=$(printf '%s' "$THIRD" | wc -c | tr -d ' ')
    rm -rf "$THIRD_HOME"
    [ "$FIRST_SIZE" -gt 0 ] && [ "$SAME_SIZE" -le 20 ] && [ "$THIRD_SIZE" -gt 0 ]
) >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "  PASS  design doc mtime change triggers re-emission"; PASS=$((PASS+1))
else
    echo "  FAIL  design doc mtime change did not trigger re-emission"; FAIL=$((FAIL+1))
fi
rm -rf "$TMP_REPO"

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
