#!/usr/bin/env bash
# test_coverage_force_run.sh — PR #2 Task 8 (ADR-008) + 2026-06-22 config-only fix.
# The pre-commit coverage gate (Force-Run + 70% threshold) must apply ONLY when
# the commit stages production source code in a coverage-measured language.
#   - Common case (source + test staged): force-run / threshold still enforced.
#   - Config-only or test-only commit (no production source staged): both skipped,
#     because there is no production code to cover (else a catch-22 blocks the
#     commit — force-run demands fresh coverage, any measure is 0%, gate rejects 0%).
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK="${REPO_ROOT}/hooks/pre-commit"

# Scenario knobs (env):
#   COV_AGE   — seconds-ago for the cached coverage timestamp (omit = no cache)
#   COV_PCT   — cached coverage percentage (default 85)
#   STAGE_SRC — 1 = stage an uncommitted production source file (src/feature.py)
#   STAGE_TEST    — 1 = stage a test file (tests/test_feature.py)
#   STAGE_CONFIG  — 1 = stage a non-source config file (.mcp.json)
_run() {
    local tmp_home; tmp_home=$(mktemp -d)
    local tmp_repo; tmp_repo=$(mktemp -d)
    mkdir -p "$tmp_home/.claude"
    echo "siae-git-workflow" > "$tmp_home/.claude/.devforge-session-skills"
    if [ -n "${COV_AGE:-}" ]; then
        local ts
        ts=$(( $(date +%s) - COV_AGE ))
        echo "${COV_PCT:-85}|${ts}" > "$tmp_home/.claude/.devforge-last-coverage"
    fi

    (
        cd "$tmp_repo"
        git init -q
        git config user.email t@t.local
        git config user.name t
        git remote add origin "git@github.com:itsiae/test-repo.git"
        mkdir -p src tests
        echo "x = 1" > src/base.py
        git add src/base.py
        git commit -q -m init
        if [ "${STAGE_SRC:-0}" = "1" ]; then
            echo "def feature(): return 2" > src/feature.py
            git add src/feature.py
        fi
        if [ "${STAGE_TEST:-0}" = "1" ]; then
            echo "def test_feature(): assert True" > tests/test_feature.py
            git add tests/test_feature.py
        fi
        if [ "${STAGE_CONFIG:-0}" = "1" ]; then
            echo '{"mcpServers":{}}' > .mcp.json
            git add .mcp.json
        fi
        printf '%s' '{"command":"git commit -m test"}' \
            | HOME="$tmp_home" bash "$HOOK" 2>/dev/null || true
    )
    rm -rf "$tmp_home" "$tmp_repo"
}

_check() { # $1=label $2=expected(block|allow) $3=needle $4=output
    local got="allow"
    echo "$4" | grep -q '"decision": "block"' && got="block"
    if [ "$got" = "$2" ] && { [ "$2" = "allow" ] || echo "$4" | grep -q "$3"; }; then
        echo "  PASS  $1"; PASS=$((PASS+1))
    else
        echo "  FAIL  $1 (expected $2)"; echo "  OUT: $4" | head -c 200; echo; FAIL=$((FAIL+1))
    fi
}

echo "=== Common case: source + test staged (gate ENFORCED) ==="
_check "1. src+test + stale coverage -> block force-run" block "Coverage Force-Run" \
    "$(COV_AGE=10800 STAGE_SRC=1 STAGE_TEST=1 _run)"
_check "2. src+test + fresh coverage -> allow"           allow "" \
    "$(COV_AGE=60 STAGE_SRC=1 STAGE_TEST=1 _run)"
_check "3. src only, no test -> allow (no force-run)"     allow "" \
    "$(COV_AGE=99999 STAGE_SRC=1 STAGE_TEST=0 _run)"
_check "4. src+test + no coverage cache -> block"         block "Coverage Force-Run" \
    "$(STAGE_SRC=1 STAGE_TEST=1 _run)"
_check "5. src + low fresh coverage -> block threshold"   block "Coverage Gate" \
    "$(COV_AGE=60 COV_PCT=10 STAGE_SRC=1 _run)"

echo ""
echo "=== Fix 2026-06-22: no production source staged (gate SKIPPED) ==="
_check "6. test-only + stale coverage -> allow (skip)"    allow "" \
    "$(COV_AGE=10800 STAGE_TEST=1 _run)"
_check "7. config-only + test + 0% fresh -> allow (skip)" allow "" \
    "$(COV_AGE=60 COV_PCT=0 STAGE_CONFIG=1 STAGE_TEST=1 _run)"
_check "8. config-only + low fresh coverage -> allow"     allow "" \
    "$(COV_AGE=60 COV_PCT=10 STAGE_CONFIG=1 _run)"

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
