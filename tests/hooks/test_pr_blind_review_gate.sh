#!/usr/bin/env bash
# test_pr_blind_review_gate.sh — PR #2 Task 10 (ADR-008).
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK="${REPO_ROOT}/hooks/pr-blind-review-gate"

_run() {
    local cmd="$1"
    local skills="${2:-}"
    local tmp_home; tmp_home=$(mktemp -d)
    local tmp_repo; tmp_repo=$(mktemp -d)
    mkdir -p "$tmp_home/.claude"
    [ -n "$skills" ] && echo "$skills" > "$tmp_home/.claude/.devforge-session-skills"
    (
        cd "$tmp_repo"
        git init -q
        git config user.email t@t
        git config user.name t
        git remote add origin "${ORIGIN:-git@github.com:itsiae/test-repo.git}"
        echo a > f && git add f && git commit -q -m init
        printf '%s' "{\"command\":\"$cmd\"}" \
            | HOME="$tmp_home" env DEVFORGE_USE_SESSION_SCOPE=1 ${EXTRA_ENV:-} bash "$HOOK" 2>/dev/null || true
    )
    rm -rf "$tmp_home" "$tmp_repo"
}

echo "=== 1. gh pr create without blind-review → block ==="
OUT=$(_run "gh pr create --title x")
if echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  blocks"; PASS=$((PASS+1))
else
    echo "  FAIL  expected block, got: $OUT"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 2. gh pr create with siae-blind-review → allow ==="
OUT=$(_run "gh pr create --title x" "siae-blind-review,siae-git-workflow")
if ! echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  allowed"; PASS=$((PASS+1))
else
    echo "  FAIL  unexpected block"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 3. gh pr edit without blind-review → block ==="
OUT=$(_run "gh pr edit 42 --body new")
if echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  edit also gated"; PASS=$((PASS+1))
else
    echo "  FAIL  expected block for edit"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 4. gh pr merge → skip (out of scope) ==="
OUT=$(_run "gh pr merge 42 --squash")
if [ -z "$OUT" ] || echo "$OUT" | grep -q '^{}$' || [ "$OUT" = "{}" ]; then
    echo "  PASS  skip on pr merge"; PASS=$((PASS+1))
else
    # allow {} exactly or empty
    if ! echo "$OUT" | grep -q '"decision": "block"'; then
        echo "  PASS  skip on pr merge (no block)"; PASS=$((PASS+1))
    else
        echo "  FAIL  merge wrongly gated: $OUT"; FAIL=$((FAIL+1))
    fi
fi

echo ""
echo "=== 5. gh issue create → skip ==="
OUT=$(_run "gh issue create --title y")
if ! echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  skip on unrelated gh command"; PASS=$((PASS+1))
else
    echo "  FAIL  issue create wrongly gated"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 6. non-itsiae repo → skip ==="
OUT=$(ORIGIN="git@github.com:other-org/test.git" _run "gh pr create --title z")
if ! echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  skip on non-itsiae"; PASS=$((PASS+1))
else
    echo "  FAIL  non-itsiae gated"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 7. DEVFORGE_SKIP_BLIND_REVIEW NON bypassa (var rimossa) ==="
OUT=$(EXTRA_ENV="DEVFORGE_SKIP_BLIND_REVIEW=1" _run "gh pr create --title z")
if echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  var ignorata, gate blocca"; PASS=$((PASS+1))
else
    echo "  FAIL  var ancora onorata (bypass non rimosso)"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 8. piped command not gated ==="
OUT=$(_run "echo gh pr create | cat")
if ! echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  pipeline-right side ignored"; PASS=$((PASS+1))
else
    echo "  FAIL  echoed string triggered gate"; FAIL=$((FAIL+1))
fi

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
