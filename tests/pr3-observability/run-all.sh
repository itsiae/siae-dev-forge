#!/usr/bin/env bash
# tests/pr3-observability/run-all.sh — aggregated runner for PR #3 tests.
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
TOTAL_PASS=0
TOTAL_FAIL=0

_run_pytest() {
    local name="$1"; local path="$2"
    echo "━━━ $name ━━━"
    if [ ! -f "$path" ]; then
        echo "  SKIP — $path"
        return
    fi
    local out
    out=$(python3 -m pytest "$path" -v --tb=short 2>&1 || true)
    echo "$out" | tail -20
    local summary
    summary=$(echo "$out" | tail -1)
    local p f
    p=$(echo "$out" | grep -oE "[0-9]+ passed" | head -1 | awk '{print $1}' || echo 0)
    f=$(echo "$out" | grep -oE "[0-9]+ failed" | head -1 | awk '{print $1}' || echo 0)
    TOTAL_PASS=$((TOTAL_PASS + ${p:-0}))
    TOTAL_FAIL=$((TOTAL_FAIL + ${f:-0}))
}

_run_bash() {
    local name="$1"; local path="$2"
    echo ""
    echo "━━━ $name ━━━"
    if [ ! -f "$path" ]; then
        echo "  SKIP — $path"
        return
    fi
    local out
    out=$(bash "$path" 2>&1 || true)
    echo "$out" | tail -15
    local summary
    summary=$(echo "$out" | grep -E "^Total:" | tail -1 || true)
    [ -z "$summary" ] && return
    local p f
    p=$(echo "$summary" | sed -E 's/.*PASS: ([0-9]+).*/\1/')
    f=$(echo "$summary" | sed -E 's/.*FAIL: ([0-9]+).*/\1/')
    TOTAL_PASS=$((TOTAL_PASS + p))
    TOTAL_FAIL=$((TOTAL_FAIL + f))
}

_run_pytest "adoption-analyzer"  "tests/lib/test_adoption_analyzer.py"
_run_bash   "PR #2 aggregator"   "tests/pr2-task-scope/run-all.sh"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PR #3 Aggregated Result"
echo "  PASS: $TOTAL_PASS"
echo "  FAIL: $TOTAL_FAIL"
if [ "$TOTAL_FAIL" -eq 0 ]; then
    echo "✅ PR #3 suite result: PASS"
    exit 0
else
    echo "❌ PR #3 suite result: FAIL"
    exit 1
fi
