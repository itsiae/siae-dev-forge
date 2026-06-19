#!/usr/bin/env bash
# test_diff_risk_classifier.sh — classificazione rischio diff per gate PR scaling.
# Design: docs/plans/2026-06-19-pr-gate-proportional-scaling-design.md
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
LIB="${REPO_ROOT}/lib/diff-risk-classifier.sh"

_mkrepo() {
    local td; td=$(mktemp -d)
    ( cd "$td"
      git init -q; git config user.email t@t; git config user.name t
      echo seed > seed.txt; git add -A; git commit -qm seed; git branch -m main
      git checkout -qb work ) >/dev/null 2>&1
    echo "$td"
}
_run() { ( cd "$1" && source "$LIB" && devforge_classify_diff_risk "main" ); }

echo "=== AC-1: solo .md → low ==="
TD=$(_mkrepo); ( cd "$TD" && echo x > a.md && git add -A && git commit -qm m ) >/dev/null 2>&1
[ "$(_run "$TD")" = "low" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-2: solo .claude-plugin/plugin.json → low ==="
TD=$(_mkrepo); ( cd "$TD" && mkdir -p .claude-plugin && echo '{}' > .claude-plugin/plugin.json && git add -A && git commit -qm m ) >/dev/null 2>&1
[ "$(_run "$TD")" = "low" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-3: hooks/foo misto a .md → code ==="
TD=$(_mkrepo); ( cd "$TD" && echo x > a.md && mkdir -p hooks && echo y > hooks/foo && git add -A && git commit -qm m ) >/dev/null 2>&1
[ "$(_run "$TD")" = "code" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-4: hooks.json → code ==="
TD=$(_mkrepo); ( cd "$TD" && echo '{}' > hooks.json && git add -A && git commit -qm m ) >/dev/null 2>&1
[ "$(_run "$TD")" = "code" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-5: diff vuoto → code ==="
TD=$(_mkrepo)
[ "$(_run "$TD")" = "code" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-6: .py → code ==="
TD=$(_mkrepo); ( cd "$TD" && echo x > a.py && git add -A && git commit -qm m ) >/dev/null 2>&1
[ "$(_run "$TD")" = "code" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-11: rename hooks/x.sh → docs/x.md → code ==="
TD=$(_mkrepo)
( cd "$TD" && git checkout -q main && mkdir -p hooks && echo s > hooks/x.sh && git add -A && git commit -qm base && git checkout -q work && git merge -q main && mkdir -p docs && git mv hooks/x.sh docs/x.md && git commit -qm ren ) >/dev/null 2>&1
[ "$(_run "$TD")" = "code" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-12: docs/runme senza estensione → code ==="
TD=$(_mkrepo); ( cd "$TD" && mkdir -p docs && echo x > docs/runme && git add -A && git commit -qm m ) >/dev/null 2>&1
[ "$(_run "$TD")" = "code" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-13: base branch arg alternativo ==="
TD=$(_mkrepo); ( cd "$TD" && git branch alt main && echo x > a.md && git add -A && git commit -qm m ) >/dev/null 2>&1
[ "$( ( cd "$TD" && source "$LIB" && devforge_classify_diff_risk "alt" ) )" = "low" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-14: .claude-plugin/evil.json → code ==="
TD=$(_mkrepo); ( cd "$TD" && mkdir -p .claude-plugin && echo '{}' > .claude-plugin/evil.json && git add -A && git commit -qm m ) >/dev/null 2>&1
[ "$(_run "$TD")" = "code" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo ""; echo "RESULT: PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]
