#!/usr/bin/env bash
# test_task_id.sh — unit tests for lib/task-id.sh (ADR-001 task-scoped enforcement)
# ─────────────────────────────────────────────────────────────────
# Covers: devforge_compute_task_id, devforge_task_id_transition,
# devforge_task_skill_invoked, devforge_task_skill_validated,
# devforge_task_skill_mark_validated.
# ─────────────────────────────────────────────────────────────────
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
LIB_FILE="${REPO_ROOT}/lib/task-id.sh"

if [ ! -f "$LIB_FILE" ]; then
    echo "FAIL — $LIB_FILE not found"
    exit 1
fi

# shellcheck disable=SC1090
source "$LIB_FILE"

_assert_eq() {
    local name="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        echo "  PASS  $name"; PASS=$((PASS+1))
    else
        echo "  FAIL  $name — expected=[$expected] actual=[$actual]"; FAIL=$((FAIL+1))
    fi
}

_assert_ok() {
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then
        echo "  PASS  $name"; PASS=$((PASS+1))
    else
        echo "  FAIL  $name"; FAIL=$((FAIL+1))
    fi
}

_assert_ko() {
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then
        echo "  FAIL  $name — command unexpectedly succeeded"; FAIL=$((FAIL+1))
    else
        echo "  PASS  $name"; PASS=$((PASS+1))
    fi
}

# ─────────────────────────────────────────────────────────────────
# Fixture: make a minimal itsiae git repo in a tmp dir, cd into it
# ─────────────────────────────────────────────────────────────────
_setup_itsiae_repo() {
    local dir; dir=$(mktemp -d)
    (
        cd "$dir"
        git init -q
        git remote add origin "git@github.com:itsiae/test-repo.git"
        git commit --allow-empty -m "init" -q
        git checkout -q -b feat/demo
    )
    echo "$dir"
}

_setup_non_itsiae_repo() {
    local dir; dir=$(mktemp -d)
    (
        cd "$dir"
        git init -q
        git remote add origin "git@github.com:other-org/test-repo.git"
        git commit --allow-empty -m "init" -q
    )
    echo "$dir"
}

echo "=== 1. Source-safe: no side effects on load ==="
_assert_eq "no state dir created just by sourcing" "" \
    "$(test -d "${HOME}/.devforge-task-skills-source-test" && echo WRONG || echo '')"

echo ""
echo "=== 2. compute_task_id in itsiae repo returns 12 hex chars ==="
REPO=$(_setup_itsiae_repo)
TID=$(cd "$REPO" && devforge_compute_task_id)
LEN=${#TID}
_assert_eq "task_id length = 12" "12" "$LEN"
# Must be hex
case "$TID" in
    *[!0-9a-f]*) echo "  FAIL  task_id not hex: $TID"; FAIL=$((FAIL+1));;
    *) echo "  PASS  task_id is hex"; PASS=$((PASS+1));;
esac

echo ""
echo "=== 3. compute_task_id is stable (same input → same output) ==="
TID1=$(cd "$REPO" && devforge_compute_task_id)
TID2=$(cd "$REPO" && devforge_compute_task_id)
_assert_eq "stable task_id" "$TID1" "$TID2"

echo ""
echo "=== 4. Non-itsiae repo returns empty string ==="
OTHER=$(_setup_non_itsiae_repo)
TID_OTHER=$(cd "$OTHER" && devforge_compute_task_id)
_assert_eq "non-itsiae task_id empty" "" "$TID_OTHER"

echo ""
echo "=== 5. Not in any git repo returns empty ==="
TMP_NOGIT=$(mktemp -d)
TID_NOGIT=$(cd "$TMP_NOGIT" && devforge_compute_task_id)
_assert_eq "no git repo task_id empty" "" "$TID_NOGIT"
rm -rf "$TMP_NOGIT"

echo ""
echo "=== 6. Branch change yields different task_id ==="
TID_BEFORE=$(cd "$REPO" && devforge_compute_task_id)
(cd "$REPO" && git checkout -q -b feat/other)
TID_AFTER=$(cd "$REPO" && devforge_compute_task_id)
if [ "$TID_BEFORE" != "$TID_AFTER" ]; then
    echo "  PASS  branch change yields different task_id"; PASS=$((PASS+1))
else
    echo "  FAIL  branch change did not change task_id"; FAIL=$((FAIL+1))
fi
(cd "$REPO" && git checkout -q feat/demo)

echo ""
echo "=== 7. Design doc mtime revision yields different task_id ==="
(cd "$REPO" && mkdir -p docs/plans && echo "v1" > docs/plans/foo-design.md)
TID_V1=$(cd "$REPO" && devforge_compute_task_id)
sleep 1
(cd "$REPO" && echo "v2" >> docs/plans/foo-design.md)
TID_V2=$(cd "$REPO" && devforge_compute_task_id)
if [ "$TID_V1" != "$TID_V2" ]; then
    echo "  PASS  design doc revision yields different task_id"; PASS=$((PASS+1))
else
    echo "  FAIL  design doc revision did not change task_id"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 8. skill_invoked append + idempotent ==="
ISO_HOME=$(mktemp -d)
(
    HOME="$ISO_HOME"
    TID="abc123def456"
    devforge_task_skill_invoked "$TID" siae-brainstorming
    devforge_task_skill_invoked "$TID" siae-brainstorming  # idempotent
    devforge_task_skill_invoked "$TID" siae-tdd
)
SKILLS_FILE="${ISO_HOME}/.claude/.devforge-task-skills/abc123def456/skills_invoked"
COUNT=$(wc -l < "$SKILLS_FILE" | tr -d ' ')
_assert_eq "skills_invoked count after idempotent appends" "2" "$COUNT"

echo ""
echo "=== 9. skill_validated positive + negative ==="
(
    HOME="$ISO_HOME"
    devforge_task_skill_mark_validated "abc123def456" siae-brainstorming
)
# Positive
(
    HOME="$ISO_HOME"
    devforge_task_skill_validated "abc123def456" siae-brainstorming
) && { echo "  PASS  validated returns 0 when skill present"; PASS=$((PASS+1)); } \
   || { echo "  FAIL  validated should return 0"; FAIL=$((FAIL+1)); }
# Negative
(
    HOME="$ISO_HOME"
    devforge_task_skill_validated "abc123def456" siae-tdd
) && { echo "  FAIL  validated returned 0 for non-validated skill"; FAIL=$((FAIL+1)); } \
   || { echo "  PASS  validated returns non-zero when skill absent"; PASS=$((PASS+1)); }

echo ""
echo "=== 10. task_id_transition: same branch + design revised → copy forward ==="
ISO_HOME2=$(mktemp -d)
OLD_TID="aaaaaaaaaaaa"
NEW_TID="bbbbbbbbbbbb"
(
    HOME="$ISO_HOME2"
    mkdir -p "${ISO_HOME2}/.claude/.devforge-task-skills/${OLD_TID}"
    echo "branch_name=feat/demo" > "${ISO_HOME2}/.claude/.devforge-task-skills/${OLD_TID}/metadata"
    echo "design_doc=docs/plans/foo-design.md" >> "${ISO_HOME2}/.claude/.devforge-task-skills/${OLD_TID}/metadata"
    echo "siae-brainstorming" > "${ISO_HOME2}/.claude/.devforge-task-skills/${OLD_TID}/skills_validated"

    mkdir -p "${ISO_HOME2}/.claude/.devforge-task-skills/${NEW_TID}"
    echo "branch_name=feat/demo" > "${ISO_HOME2}/.claude/.devforge-task-skills/${NEW_TID}/metadata"
    echo "design_doc=docs/plans/foo-design.md" >> "${ISO_HOME2}/.claude/.devforge-task-skills/${NEW_TID}/metadata"

    devforge_task_id_transition "$OLD_TID" "$NEW_TID"
)
NEW_VALIDATED="${ISO_HOME2}/.claude/.devforge-task-skills/${NEW_TID}/skills_validated"
if [ -f "$NEW_VALIDATED" ] && grep -qxF "siae-brainstorming" "$NEW_VALIDATED"; then
    echo "  PASS  same branch+design carry forward skills_validated"; PASS=$((PASS+1))
else
    echo "  FAIL  copy forward did not happen"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 11. task_id_transition: branch change → NO copy ==="
ISO_HOME3=$(mktemp -d)
(
    HOME="$ISO_HOME3"
    mkdir -p "${ISO_HOME3}/.claude/.devforge-task-skills/${OLD_TID}"
    echo "branch_name=feat/old" > "${ISO_HOME3}/.claude/.devforge-task-skills/${OLD_TID}/metadata"
    echo "design_doc=docs/plans/foo-design.md" >> "${ISO_HOME3}/.claude/.devforge-task-skills/${OLD_TID}/metadata"
    echo "siae-brainstorming" > "${ISO_HOME3}/.claude/.devforge-task-skills/${OLD_TID}/skills_validated"

    mkdir -p "${ISO_HOME3}/.claude/.devforge-task-skills/${NEW_TID}"
    echo "branch_name=feat/new" > "${ISO_HOME3}/.claude/.devforge-task-skills/${NEW_TID}/metadata"
    echo "design_doc=docs/plans/foo-design.md" >> "${ISO_HOME3}/.claude/.devforge-task-skills/${NEW_TID}/metadata"

    devforge_task_id_transition "$OLD_TID" "$NEW_TID"
)
NEW_VALIDATED="${ISO_HOME3}/.claude/.devforge-task-skills/${NEW_TID}/skills_validated"
if [ -f "$NEW_VALIDATED" ] && [ -s "$NEW_VALIDATED" ]; then
    echo "  FAIL  branch change wrongly copied forward"; FAIL=$((FAIL+1))
else
    echo "  PASS  branch change → no copy"; PASS=$((PASS+1))
fi

echo ""
echo "=== 12. concurrent skill_invoked append (atomic) ==="
ISO_HOME4=$(mktemp -d)
TID_CONC="cccccccccccc"
(
    HOME="$ISO_HOME4"
    for i in $(seq 1 10); do
        (devforge_task_skill_invoked "$TID_CONC" "skill-$i") &
    done
    wait
)
CONC_FILE="${ISO_HOME4}/.claude/.devforge-task-skills/${TID_CONC}/skills_invoked"
UNIQUE_COUNT=$(sort -u "$CONC_FILE" | grep -c .)
_assert_eq "concurrent append preserves 10 unique skills" "10" "$UNIQUE_COUNT"

# Cleanup
rm -rf "$REPO" "$OTHER" "$ISO_HOME" "$ISO_HOME2" "$ISO_HOME3" "$ISO_HOME4"

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
