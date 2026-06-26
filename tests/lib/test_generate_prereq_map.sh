#!/usr/bin/env bash
# test_generate_prereq_map.sh — lib/generate-prereq-map.sh (ADR-007)
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
GEN="${REPO_ROOT}/lib/generate-prereq-map.sh"
OUT="${REPO_ROOT}/lib/prereq-map.generated"

if [ ! -f "$GEN" ]; then
    echo "FAIL — $GEN not found"
    exit 1
fi

echo "=== 1. Generator runs without error ==="
TMP_OUT=$(mktemp)
if bash "$GEN" > "$TMP_OUT" 2>&1; then
    echo "  PASS  generator exit 0"; PASS=$((PASS+1))
else
    echo "  FAIL  generator exit non-zero"; FAIL=$((FAIL+1))
    cat "$TMP_OUT"
fi
rm -f "$TMP_OUT"

echo ""
echo "=== 2. prereq-map.generated exists and is non-empty ==="
if [ -s "$OUT" ]; then
    echo "  PASS  $OUT exists and has content"; PASS=$((PASS+1))
else
    echo "  FAIL  $OUT missing or empty"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 3. All data entries follow 'skill=prereq1[,prereq2...]' format ==="
# Skip comment (#) and blank lines — only real entries must match the shape.
BAD_LINES=$(grep -vE '^[a-z][a-z0-9-]*=[a-z][a-z0-9,-]*$' "$OUT" 2>/dev/null \
    | grep -vE '^(#|$)' || true)
if [ -z "$BAD_LINES" ]; then
    echo "  PASS  all data entries follow format"; PASS=$((PASS+1))
else
    echo "  FAIL  malformed lines:"; echo "$BAD_LINES"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 4. Core SIAE backbone prereqs present ==="
_check_entry() {
    local pattern="$1"
    if grep -qF "$pattern" "$OUT"; then
        echo "  PASS  contains $pattern"; PASS=$((PASS+1))
    else
        echo "  FAIL  missing $pattern"; FAIL=$((FAIL+1))
    fi
}
_check_entry "siae-git-workflow=siae-git-env"
_check_entry "siae-finishing-branch="
_check_entry "siae-writing-plans=siae-brainstorming"
_check_entry "siae-executing-plans=siae-writing-plans"
_check_entry "siae-tdd=siae-brainstorming"

echo ""
echo "=== 5. Idempotent: re-running yields identical output ==="
FIRST=$(cat "$OUT")
bash "$GEN" >/dev/null 2>&1
SECOND=$(cat "$OUT")
if [ "$FIRST" = "$SECOND" ]; then
    echo "  PASS  idempotent"; PASS=$((PASS+1))
else
    echo "  FAIL  second run differs"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 6. At least 10 entries (sanity check) ==="
ENTRY_COUNT=$(grep -c . "$OUT" || echo 0)
if [ "$ENTRY_COUNT" -ge 10 ]; then
    echo "  PASS  $ENTRY_COUNT entries"; PASS=$((PASS+1))
else
    echo "  FAIL  only $ENTRY_COUNT entries (expected >= 10)"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 7. No forward-handoff edges mis-parsed as backward prerequisites (RC-A) ==="
# In DevForge a body `REQUIRED SUB-SKILL: X` line means "invoke X as a step
# DURING/AFTER this skill" (forward), never "X must run BEFORE this skill".
# These skills declare such forward steps and have no real backward prereq —
# they must be entry points (no map entry), not blocked on their own sub-step.
_check_absent() {
    local pattern="$1"
    if grep -qE "$pattern" "$OUT"; then
        echo "  FAIL  forward edge present: $pattern"; FAIL=$((FAIL+1))
    else
        echo "  PASS  absent: $pattern"; PASS=$((PASS+1))
    fi
}
_check_absent '^siae-debugging='              # "Dopo la root cause, fixa con siae-tdd"
_check_absent '^siae-receiving-review='        # "Se capisci → fix con siae-tdd"
_check_absent '^siae-codebase-map='            # "Step 7a — sub-skill tiered"
_check_absent '^siae-datalake-etl-setup='      # "Step — esegui sub-skill (env-sync/git)"
_check_absent '^siae-datalake-iac-setup='
_check_absent '^siae-datalake-ingestion-setup='

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
