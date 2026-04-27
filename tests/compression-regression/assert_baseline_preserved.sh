#!/usr/bin/env bash
# Improvement: la test suite esistente non regredisce.
# Baseline pre-PR-1 era: 168 PASS / 6 FAIL / 1 SKIP.
# Baseline post-T12 (PR-1): 161 PASS / 6 FAIL / 1 SKIP (-7 atteso: 7 test
# archiviati assieme a hooks/user-prompt-context, coperto da
# tests/hooks/test_devforge_context.sh + compression-regression).
set -eu
cd "$(git rev-parse --show-toplevel)"

echo "=== Run full baseline suite ==="
OUTPUT_FILE=$(mktemp)
bash tests/run-all.sh > "$OUTPUT_FILE" 2>&1 || true

PASS_COUNT=$(grep -oE '✅ PASS: `[0-9]+`' "$OUTPUT_FILE" | grep -oE '[0-9]+' | head -1 || echo 0)
FAIL_COUNT=$(grep -oE '❌ FAIL: `[0-9]+`' "$OUTPUT_FILE" | grep -oE '[0-9]+' | head -1 || echo 0)

echo "Current run: PASS=$PASS_COUNT  FAIL=$FAIL_COUNT"

BASELINE_PASS=161
BASELINE_FAIL=6

if [ "$PASS_COUNT" -ge "$BASELINE_PASS" ]; then
    echo "  PASS  PASS count preserved ($PASS_COUNT >= $BASELINE_PASS)"
    P=0
else
    echo "  FAIL  PASS regression ($PASS_COUNT < $BASELINE_PASS)"
    P=1
fi

if [ "$FAIL_COUNT" -le "$BASELINE_FAIL" ]; then
    echo "  PASS  FAIL count no worse ($FAIL_COUNT <= $BASELINE_FAIL)"
    F=0
else
    echo "  FAIL  FAIL regression ($FAIL_COUNT > $BASELINE_FAIL)"
    F=1
fi

# Bonus: log delta vs baseline
echo ""
echo "Delta: ΔPASS=+$((PASS_COUNT - BASELINE_PASS))  ΔFAIL=$((FAIL_COUNT - BASELINE_FAIL))"

rm -f "$OUTPUT_FILE"
exit $((P + F))
