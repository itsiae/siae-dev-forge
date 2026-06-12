#!/usr/bin/env bash
# Test has_tests pattern + tests_files_changed (task-02)
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PASS=0; FAIL=0
ok(){ echo "  PASS: $1"; PASS=$((PASS+1)); }
ko(){ echo "  FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }

PATTERN='(Test\.|_test\.|\.test\.|\.spec\.|/test/|/tests/|/__tests__/|conftest\.py|^test_|^tests/)'
detect(){ echo "$1" | grep -qE "$PATTERN" && echo true || echo false; }
count(){ echo "$1" | grep -cE "$PATTERN" || true; }

# T5 — __tests__/
{ [ "$(detect 'src/__tests__/a.test.ts')" = "true" ]; } && ok "T5 __tests__/" || ko "T5" "no match"
# T6 — conftest
{ [ "$(detect 'tests/conftest.py')" = "true" ] && [ "$(detect 'conftest.py')" = "true" ]; } && ok "T6 conftest" || ko "T6" "no match"
# pre-esistenti (no-regression pattern)
regr_ok=1
for f in 'src/UserServiceTest.java' 'pkg/util_test.go' 'a.spec.ts' 'src/test/X.java' 'tests/test_main.py'; do
  [ "$(detect "$f")" = "true" ] || { ko "pattern-regress" "$f non match"; regr_ok=0; }
done
[ "$regr_ok" = "1" ] && ok "pattern pre-esistenti coperti"

# T7 — no test
multi=$'src/app.ts\nREADME.md'
{ [ "$(detect "$multi")" = "false" ] && [ "$(count "$multi")" = "0" ]; } && ok "T7 no-test false/0" || ko "T7" "detect=$(detect "$multi") count=$(count "$multi")"

# T8 — 3 su 5
five=$'src/a.ts\nsrc/__tests__/a.test.ts\nsrc/b.ts\ntests/test_b.py\nlib/conftest.py'
{ [ "$(count "$five")" = "3" ] && [ "$(detect "$five")" = "true" ]; } && ok "T8 count=3" || ko "T8" "count=$(count "$five")"

# il hook reale deve usare gli stessi pattern + emettere tests_files_changed
HOOK="$PLUGIN_ROOT/hooks/post-commit-review"
{ grep -q '/__tests__/' "$HOOK" && grep -q 'conftest' "$HOOK"; } && ok "hook contiene pattern nuovi" || ko "hook pattern" "manca __tests__ o conftest"
grep -q 'tests_files_changed' "$HOOK" && ok "hook emette tests_files_changed" || ko "hook field" "manca tests_files_changed"

echo "has_tests-enrichment: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
