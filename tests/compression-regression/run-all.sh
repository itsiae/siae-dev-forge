#!/usr/bin/env bash
set +e
cd "$(dirname "$0")"
TOTAL_FAIL=0
for script in assert_behavioral_invariants.sh assert_compression_targets.sh assert_injection_reduction.sh assert_baseline_preserved.sh; do
    echo "━━━ $script ━━━"
    bash "$script"
    RC=$?
    TOTAL_FAIL=$((TOTAL_FAIL + RC))
    echo ""
done
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Suite result: $([ $TOTAL_FAIL -eq 0 ] && echo PASS || echo FAIL)"
exit $TOTAL_FAIL
