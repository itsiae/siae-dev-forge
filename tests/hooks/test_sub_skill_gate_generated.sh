#!/usr/bin/env bash
# test_sub_skill_gate_generated.sh — verify sub-skill-gate loads PREREQ_MAP
# from lib/prereq-map.generated (Task 9 / ADR-007).
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK="${REPO_ROOT}/hooks/sub-skill-gate"
GEN_FILE="${REPO_ROOT}/lib/prereq-map.generated"

if [ ! -f "$HOOK" ] || [ ! -f "$GEN_FILE" ]; then
    echo "FAIL — hook or generated file missing"; exit 1
fi

_assert_blocks() {
    local name="$1" skill="$2"
    local isolated_home; isolated_home=$(mktemp -d)
    local out
    out=$(echo "{\"skill\":\"${skill}\"}" | HOME="$isolated_home" bash "$HOOK" 2>&1 || true)
    rm -rf "$isolated_home"
    if echo "$out" | grep -q '"decision": "block"'; then
        echo "  PASS  $name — blocked"; PASS=$((PASS+1))
    else
        echo "  FAIL  $name — expected block, got:"; echo "$out" | head -3; FAIL=$((FAIL+1))
    fi
}

_assert_allows() {
    local name="$1" skill="$2" pre="$3"
    local isolated_home; isolated_home=$(mktemp -d)
    mkdir -p "$isolated_home/.claude"
    # Write the prereq as invoked — accept both plain and plugin:name form.
    printf '%s\n' "$pre" > "$isolated_home/.claude/.devforge-session-skills"
    local out
    out=$(echo "{\"skill\":\"${skill}\"}" | HOME="$isolated_home" bash "$HOOK" 2>&1 || true)
    rm -rf "$isolated_home"
    # Allow = empty JSON {} (no decision:block key)
    if ! echo "$out" | grep -q '"decision": "block"'; then
        echo "  PASS  $name — allowed"; PASS=$((PASS+1))
    else
        echo "  FAIL  $name — expected allow, got:"; echo "$out" | head -3; FAIL=$((FAIL+1))
    fi
}

echo "=== 1. Generated file present → gate uses it ==="
_assert_blocks "siae-git-workflow without siae-git-env"      "siae-git-workflow"
_assert_blocks "siae-finishing-branch without prereqs"       "siae-finishing-branch"
_assert_blocks "siae-writing-plans without siae-brainstorming" "siae-writing-plans"

echo ""
echo "=== 2. Prereq satisfied → allow ==="
_assert_allows "siae-git-workflow with siae-git-env"         "siae-git-workflow" "siae-git-env"
_assert_allows "siae-writing-plans with siae-brainstorming"  "siae-writing-plans" "siae-brainstorming"

echo ""
echo "=== 3. Generated entries from Task 4 visible in gate behavior ==="
# siae-tdd=siae-brainstorming (Task 4 added via curated)
_assert_blocks "siae-tdd without siae-brainstorming" "siae-tdd"
_assert_allows "siae-tdd with siae-brainstorming"    "siae-tdd" "siae-brainstorming"

echo ""
echo "=== 4. Fallback when generated file missing ==="
BACKUP="${GEN_FILE}.bak.$$"
mv "$GEN_FILE" "$BACKUP"
_assert_blocks "fallback: siae-git-workflow still blocked" "siae-git-workflow"
mv "$BACKUP" "$GEN_FILE"
echo "  (fallback test restored $GEN_FILE)"

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
