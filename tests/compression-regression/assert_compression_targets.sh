#!/usr/bin/env bash
# Improvement: verifica che i target di compressione siano raggiunti.
set -eu
PASS=0; FAIL=0
cd "$(git rev-parse --show-toplevel)"

_assert_le() {
    local name="$1"; local actual="$2"; local limit="$3"
    if [ "$actual" -le "$limit" ]; then
        echo "  PASS  $name (actual=$actual <= $limit)"; PASS=$((PASS+1))
    else
        echo "  FAIL  $name (actual=$actual > $limit)"; FAIL=$((FAIL+1))
    fi
}

echo "=== Per-skill compression targets ==="
_assert_le "using-devforge <= 90"     "$(wc -l < skills/using-devforge/SKILL.md)" 90
_assert_le "siae-brainstorming <= 220" "$(wc -l < skills/siae-brainstorming/SKILL.md)" 220
_assert_le "siae-tdd <= 180"          "$(wc -l < skills/siae-tdd/SKILL.md)" 180
_assert_le "siae-git-workflow <= 220" "$(wc -l < skills/siae-git-workflow/SKILL.md)" 220
_assert_le "siae-verification <= 180" "$(wc -l < skills/siae-verification/SKILL.md)" 180
_assert_le "siae-blind-review <= 110" "$(wc -l < skills/siae-blind-review/SKILL.md)" 110

echo ""
TOTAL=$(wc -l < skills/using-devforge/SKILL.md)
for s in siae-brainstorming siae-tdd siae-git-workflow siae-verification siae-blind-review; do
    TOTAL=$((TOTAL + $(wc -l < skills/$s/SKILL.md)))
done
_assert_le "TOTAL backbone <= 1000" "$TOTAL" 1000

echo ""
echo "=== Improvement vs baseline (2636 lines) ==="
BASELINE=2636
REDUCTION=$(( (BASELINE - TOTAL) * 100 / BASELINE ))
if [ "$REDUCTION" -ge 50 ]; then
    echo "  PASS  Reduction >= 50% (actual=$REDUCTION%, target=62%)"; PASS=$((PASS+1))
else
    echo "  FAIL  Reduction < 50% (actual=$REDUCTION%)"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== Centralizations present ==="
for f in risk-taxonomy.md operational-limits.md permission-denied-handling.md checkpoint-schema.md; do
    if [ -f "lib/$f" ]; then echo "  PASS  lib/$f exists"; PASS=$((PASS+1))
    else echo "  FAIL  lib/$f missing"; FAIL=$((FAIL+1)); fi
done

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
