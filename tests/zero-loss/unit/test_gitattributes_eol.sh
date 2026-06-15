#!/usr/bin/env bash
# Unit tests: .gitattributes must enforce eol=lf on hooks/* and lib/*.sh.
# AC1: git check-attr eol returns lf for critical hook/lib files.
# AC2: no CR bytes in hooks/* and lib/*.sh (no CRLF contamination).
#
# Task 01 — F1: line-ending safety (.gitattributes eol=lf)

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

fail=0
pass=0

assert() {
    local name="$1" actual="$2" expected="$3"
    if [ "$actual" = "$expected" ]; then
        echo "  PASS: $name"; pass=$((pass + 1))
    else
        echo "  FAIL: $name — expected '$expected' got '$actual'"; fail=$((fail + 1))
    fi
}

# --------------------------------------------------------------
echo "TEST 1 — .gitattributes exists at repo root"
assert "T1: .gitattributes exists" \
    "$([ -f "$REPO_ROOT/.gitattributes" ] && echo yes || echo no)" "yes"

[ "$fail" -gt 0 ] && { echo ""; echo "SUMMARY: $pass passed, $fail failed"; exit $fail; }

# --------------------------------------------------------------
echo "TEST 2 — git check-attr eol returns lf for critical files"
# Per ogni file critico: (a) verifica che esista nel repo, (b) verifica eol=lf.
# File existence check evita falsi PASS se un file viene rinominato/rimosso.
for target_file in \
    "hooks/post-commit-review" \
    "hooks/run-hook.cmd" \
    "lib/logger.sh" \
    "lib/install-trailer-hook.sh"
do
    if [ ! -f "$REPO_ROOT/$target_file" ]; then
        echo "  FAIL: T2: $target_file does not exist in repo (renamed/deleted?)"; fail=$((fail + 1))
        continue
    fi
    attr_val=$(git -C "$REPO_ROOT" check-attr eol -- "$target_file" 2>/dev/null \
               | sed 's/.*: eol: //')
    assert "T2: eol=lf for $target_file" "$attr_val" "lf"
done

# --------------------------------------------------------------
echo "TEST 3 — no CR bytes in hooks/* and lib/*.sh"
cr_files=$(grep -rl $'\r' "$REPO_ROOT/hooks/"* "$REPO_ROOT/lib/"*.sh 2>/dev/null | wc -l | tr -d ' ')
assert "T3: zero files with CR byte in hooks/* and lib/*.sh" "$cr_files" "0"

# --------------------------------------------------------------
echo ""
echo "SUMMARY: $pass passed, $fail failed"
exit $fail
