#!/usr/bin/env bash
# Unit tests: API docs site (Redoc) — same-origin spec, no-drift, workflow valid.
# Task 01 + 02 di docs/plans/2026-06-15-api-docs-private-pages/.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HTML="$REPO_ROOT/docs/api/index.html"
SPEC_COPY="$REPO_ROOT/docs/api/telemetry-insights-api.openapi.yaml"
SPEC_SRC="$REPO_ROOT/docs/plans/2026-06-14-devforge-telemetry-insights-api.openapi.yaml"
WORKFLOW="$REPO_ROOT/.github/workflows/pages.yml"

fail=0
assert() { # name actual expected
    if [ "$2" = "$3" ]; then echo "  PASS: $1"; else echo "  FAIL: $1 — expected '$3' got '$2'"; fail=$((fail+1)); fi
}
assert_true() { # name cond(0=true)
    if [ "$2" -eq 0 ]; then echo "  PASS: $1"; else echo "  FAIL: $1"; fail=$((fail+1)); fi
}

echo "TEST 1 — index.html: Redoc + spec-url same-origin"
[ -f "$HTML" ]; assert_true "T1a: index.html exists" $?
grep -q '<redoc' "$HTML"; assert_true "T1b: contains <redoc>" $?
grep -q 'cdn.redocly.com/redoc' "$HTML"; assert_true "T1c: Redoc bundle from CDN" $?
grep -q 'spec-url="\./telemetry-insights-api.openapi.yaml"' "$HTML"; assert_true "T1d: spec-url relative same-origin" $?
grep -q 'spec-url="http' "$HTML"; rc=$?; assert_true "T1e: spec-url NOT an external http URL" $([ "$rc" -ne 0 ] && echo 0 || echo 1)

echo "TEST 2 — no-drift: spec copy == source"
if [ -f "$SPEC_COPY" ] && [ -f "$SPEC_SRC" ]; then
    diff -q "$SPEC_COPY" "$SPEC_SRC" >/dev/null 2>&1; assert_true "T2a: docs/api spec identical to source (no drift)" $?
else
    echo "  FAIL: T2a: spec copy o source mancante"; fail=$((fail+1))
fi

echo "TEST 3 — workflow pages.yml valido + permessi minimi"
[ -f "$WORKFLOW" ]; assert_true "T3a: pages.yml exists" $?
python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" "$WORKFLOW" 2>/dev/null; assert_true "T3b: YAML parse OK" $?
grep -qE 'pages:[[:space:]]*write' "$WORKFLOW"; assert_true "T3c: permissions pages: write" $?
grep -qE 'id-token:[[:space:]]*write' "$WORKFLOW"; assert_true "T3d: permissions id-token: write" $?
grep -qE 'group:[[:space:]]*pages' "$WORKFLOW"; assert_true "T3e: concurrency group pages" $?
grep -q 'actions/upload-pages-artifact' "$WORKFLOW"; assert_true "T3f: uses upload-pages-artifact" $?
grep -q 'actions/deploy-pages' "$WORKFLOW"; assert_true "T3g: uses deploy-pages" $?
grep -qE "path:[[:space:]]*docs/api" "$WORKFLOW"; assert_true "T3h: artifact path docs/api" $?

echo ""
if [ "$fail" -eq 0 ]; then echo "SUMMARY: all passed, 0 failed"; else echo "SUMMARY: $fail failed"; fi
exit $fail
