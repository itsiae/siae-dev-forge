#!/usr/bin/env bash
# test_plan_gate_write.sh — PR #2 Task 11 (ADR-008).
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK="${REPO_ROOT}/hooks/plan-gate-write"

_run() {
    local path="$1" skills="${2:-}"
    local tmp_home; tmp_home=$(mktemp -d)
    local tmp_repo; tmp_repo=$(mktemp -d)
    mkdir -p "$tmp_home/.claude"
    [ -n "$skills" ] && echo "$skills" > "$tmp_home/.claude/.devforge-session-skills"
    (
        cd "$tmp_repo"
        git init -q
        git config user.email t@t
        git config user.name t
        git remote add origin "${ORIGIN:-git@github.com:itsiae/x.git}"
        echo a > f && git add f && git commit -q -m init
        mkdir -p docs/plans
        printf '%s' "{\"file_path\":\"${tmp_repo}/${path}\"}" \
            | HOME="$tmp_home" env DEVFORGE_USE_SESSION_SCOPE=1 bash "$HOOK" 2>/dev/null || true
    )
    rm -rf "$tmp_home" "$tmp_repo"
}

echo "=== 1. Write design doc without brainstorming → block ==="
OUT=$(_run "docs/plans/foo-design.md")
if echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  blocks"; PASS=$((PASS+1))
else
    echo "  FAIL  expected block"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 2. Write design doc with brainstorming → allow ==="
OUT=$(_run "docs/plans/foo-design.md" "siae-brainstorming")
if ! echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  allowed"; PASS=$((PASS+1))
else
    echo "  FAIL  unexpected block"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 3. Write plan doc (*-plan.md) → skip (out of scope) ==="
OUT=$(_run "docs/plans/foo-plan.md")
if ! echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  skip on plan doc"; PASS=$((PASS+1))
else
    echo "  FAIL  plan doc wrongly gated"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 4. Write source file → skip ==="
OUT=$(_run "src/foo.ts")
if ! echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  skip on non-design-doc"; PASS=$((PASS+1))
else
    echo "  FAIL  source file wrongly gated"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 5. Non-itsiae repo → skip ==="
OUT=$(ORIGIN="git@github.com:other-org/x.git" _run "docs/plans/foo-design.md")
if ! echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  skip on non-itsiae"; PASS=$((PASS+1))
else
    echo "  FAIL  non-itsiae gated"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 6. Nested path docs/plans/sub/... (still a design.md) ==="
# Only a flat docs/plans/*-design.md should match; nested dirs are out of scope.
# If we match nested, the pattern is too broad; if we don't, the spec is met.
OUT=$(_run "docs/plans/sub/foo-design.md")
if ! echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  nested path not matched"; PASS=$((PASS+1))
else
    echo "  FAIL  nested path wrongly gated"; FAIL=$((FAIL+1))
fi

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
