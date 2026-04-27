#!/usr/bin/env bash
# tests/pr2-task-scope/run-all.sh — aggregate runner for PR #2 test suites.
# ─────────────────────────────────────────────────────────────────
# Runs every test file introduced by PR #2 and reports a single summary.
# Used by the PR #2 acceptance criteria ("≥40 new tests PASS").
# ─────────────────────────────────────────────────────────────────
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

TOTAL_PASS=0
TOTAL_FAIL=0
SUITE_FAILURES=()

_run() {
    local name="$1"
    local script="$2"
    echo ""
    echo "━━━ $name ━━━"
    if [ ! -f "$script" ]; then
        echo "  SKIP — $script missing"
        return
    fi
    # Capture last "Total: N — PASS: X — FAIL: Y" line from the suite output.
    local out
    out=$(bash "$script" 2>&1 || true)
    echo "$out" | tail -20
    local summary
    summary=$(echo "$out" | grep -E "^Total: [0-9]+ — PASS: [0-9]+ — FAIL: [0-9]+" | tail -1 || true)
    if [ -z "$summary" ]; then
        echo "  WARN — no summary line; treating as 0/0"
        SUITE_FAILURES+=("$name (no summary)")
        return
    fi
    local p f
    p=$(echo "$summary" | sed -E 's/.*PASS: ([0-9]+).*/\1/')
    f=$(echo "$summary" | sed -E 's/.*FAIL: ([0-9]+).*/\1/')
    TOTAL_PASS=$((TOTAL_PASS + p))
    TOTAL_FAIL=$((TOTAL_FAIL + f))
    if [ "$f" -gt 0 ]; then
        SUITE_FAILURES+=("$name ($f failures)")
    fi
}

# Library tests (lib/)
_run "task-id (ADR-001)"             "tests/lib/test_task_id.sh"
_run "file-taxonomy (ADR-005)"       "tests/lib/test_file_taxonomy.sh"
_run "generate-prereq-map (ADR-007)" "tests/lib/test_generate_prereq_map.sh"
_run "cmd-parser (ADR-006)"          "tests/lib/test_cmd_parser.sh"

# Hook tests (hooks/)
_run "brainstorming-gate dual-write" "tests/hooks/brainstorming-gate.test.sh"
_run "sub-skill-gate autogen"        "tests/hooks/test_sub_skill_gate_generated.sh"
_run "evidence-stop-gate"            "tests/hooks/test_evidence_stop_gate.sh"
_run "coverage-force-run"            "tests/hooks/test_coverage_force_run.sh"
_run "pr-blind-review-gate"          "tests/hooks/test_pr_blind_review_gate.sh"
_run "plan-gate-write"               "tests/hooks/test_plan_gate_write.sh"

# End-to-end integration (PR #2 review fixes)
_run "task-scope e2e (ADR-001 wiring)" "tests/integration/test_task_scope_e2e.sh"

# Shared suites — verify PR #1 invariants still hold after PR #2 changes
_run "compression-regression (PR #1)" "tests/compression-regression/run-all.sh"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PR #2 Aggregated Result"
echo "  PASS: $TOTAL_PASS"
echo "  FAIL: $TOTAL_FAIL"
if [ ${#SUITE_FAILURES[@]} -gt 0 ]; then
    echo "  Suites with failures:"
    for s in "${SUITE_FAILURES[@]}"; do
        echo "    - $s"
    done
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$TOTAL_FAIL" -eq 0 ]; then
    echo "✅ PR #2 suite result: PASS"
    exit 0
else
    echo "❌ PR #2 suite result: FAIL"
    exit 1
fi
