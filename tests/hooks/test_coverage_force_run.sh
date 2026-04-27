#!/usr/bin/env bash
# test_coverage_force_run.sh — PR #2 Task 8 (ADR-008).
# Ensures the pre-commit hook refuses to proceed when staged tests exist
# but cached coverage is stale (> 30 min) or missing.
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK="${REPO_ROOT}/hooks/pre-commit"

_run() {
    local tmp_home; tmp_home=$(mktemp -d)
    local tmp_repo; tmp_repo=$(mktemp -d)
    mkdir -p "$tmp_home/.claude"
    # Seed session-skills so the git-workflow gate doesn't short-circuit.
    echo "siae-git-workflow" > "$tmp_home/.claude/.devforge-session-skills"
    # Optional: seed coverage cache per scenario
    if [ -n "${COV_AGE:-}" ]; then
        local ts
        ts=$(( $(date +%s) - COV_AGE ))
        echo "85|${ts}" > "$tmp_home/.claude/.devforge-last-coverage"
    fi

    (
        cd "$tmp_repo"
        git init -q
        git config user.email t@t.local
        git config user.name t
        git remote add origin "git@github.com:itsiae/test-repo.git"
        mkdir -p src tests
        echo "hello" > src/app.ts
        git add src/app.ts
        git commit -q -m init
        # Stage a test file for the "staged test" signal
        if [ "${STAGE_TEST:-0}" = "1" ]; then
            echo "t" > tests/app.spec.ts
            git add tests/app.spec.ts
        fi
        # Invoke the hook with a fake `git commit` command
        printf '%s' '{"command":"git commit -m test"}' \
            | HOME="$tmp_home" bash "$HOOK" 2>/dev/null || true
    )
    rm -rf "$tmp_home" "$tmp_repo"
}

echo "=== 1. Staged tests + stale coverage (3h old) → block ==="
OUT=$(COV_AGE=10800 STAGE_TEST=1 _run)
if echo "$OUT" | grep -q '"decision": "block"' && echo "$OUT" | grep -q "Coverage Force-Run"; then
    echo "  PASS  blocks stale coverage"; PASS=$((PASS+1))
else
    echo "  FAIL  expected coverage-force-run block"
    echo "  OUT: $OUT" | head -c 200
    FAIL=$((FAIL+1))
fi

echo ""
echo "=== 2. Staged tests + fresh coverage (<30min) → allow ==="
OUT=$(COV_AGE=60 STAGE_TEST=1 _run)
if ! echo "$OUT" | grep -q "Coverage Force-Run"; then
    echo "  PASS  fresh coverage bypasses force-run"; PASS=$((PASS+1))
else
    echo "  FAIL  should not block with fresh coverage"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 3. No staged tests → allow even with stale coverage ==="
OUT=$(COV_AGE=99999 STAGE_TEST=0 _run)
if ! echo "$OUT" | grep -q "Coverage Force-Run"; then
    echo "  PASS  no staged tests → no force-run"; PASS=$((PASS+1))
else
    echo "  FAIL  force-run triggered without staged tests"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 4. Staged tests + no coverage cache → block ==="
OUT=$(STAGE_TEST=1 _run)
if echo "$OUT" | grep -q "Coverage Force-Run"; then
    echo "  PASS  missing coverage triggers force-run"; PASS=$((PASS+1))
else
    echo "  FAIL  expected block when coverage absent"; FAIL=$((FAIL+1))
fi

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
