#!/usr/bin/env bash
# tests/lib/diff-truncate.test.sh — unit test per lib/diff-truncate.sh (REQ-DF-03).
# Copre: diff piccolo -> diff completo; diff grande (> soglia) -> stat+name-only+
# nota di troncamento, senza mai bloccarsi (exit sempre 0).
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
LIB="${REPO_ROOT}/lib/diff-truncate.sh"

if [ ! -f "$LIB" ]; then
    echo "FAIL — $LIB not found"
    exit 1
fi

# shellcheck disable=SC1090
source "$LIB"

_mkrepo() {
    local td; td=$(mktemp -d)
    ( cd "$td"
      git init -q; git config user.email t@t; git config user.name t
      echo seed > seed.txt; git add -A; git commit -qm seed; git branch -m main
      git checkout -qb work ) >/dev/null 2>&1
    echo "$td"
}

echo "=== AC-1: diff piccolo (sotto soglia) -> diff completo, exit 0 ==="
TD=$(_mkrepo)
( cd "$TD" && echo "riga1" > small.txt && git add -A && git commit -qm small ) >/dev/null 2>&1
OUT=$(cd "$TD" && devforge_diff_or_summary "main" 2000); RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q '^+riga1$' && ! printf '%s' "$OUT" | grep -q 'diff troncato'; then
    echo PASS; PASS=$((PASS+1))
else
    echo "FAIL — rc=$RC out=<<$OUT>>"; FAIL=$((FAIL+1))
fi
rm -rf "$TD"

echo "=== AC-2: diff grande (sopra soglia bassa di test) -> stat+name-only+nota, exit 0 ==="
TD=$(_mkrepo)
( cd "$TD" && seq 1 50 > big.txt && git add -A && git commit -qm big ) >/dev/null 2>&1
OUT=$(cd "$TD" && devforge_diff_or_summary "main" 10); RC=$?
if [ "$RC" -eq 0 ] \
    && printf '%s' "$OUT" | grep -q 'file changed' \
    && printf '%s' "$OUT" | grep -qx 'big.txt' \
    && printf '%s' "$OUT" | grep -q 'diff troncato oltre 10 righe — richiedi i file mancanti on-demand'; then
    echo PASS; PASS=$((PASS+1))
else
    echo "FAIL — rc=$RC out=<<$OUT>>"; FAIL=$((FAIL+1))
fi
rm -rf "$TD"

echo "=== AC-3: default DEVFORGE_MAX_DIFF_LINES=2000 se max_lines omesso ==="
TD=$(_mkrepo)
( cd "$TD" && echo "riga1" > small2.txt && git add -A && git commit -qm small2 ) >/dev/null 2>&1
OUT=$(cd "$TD" && unset DEVFORGE_MAX_DIFF_LINES; devforge_diff_or_summary "main"); RC=$?
if [ "$RC" -eq 0 ] && ! printf '%s' "$OUT" | grep -q 'diff troncato'; then
    echo PASS; PASS=$((PASS+1))
else
    echo "FAIL — rc=$RC out=<<$OUT>>"; FAIL=$((FAIL+1))
fi
rm -rf "$TD"

echo "=== AC-4: DEVFORGE_MAX_DIFF_LINES da env se max_lines non passato ==="
TD=$(_mkrepo)
( cd "$TD" && seq 1 50 > big2.txt && git add -A && git commit -qm big2 ) >/dev/null 2>&1
OUT=$(cd "$TD" && DEVFORGE_MAX_DIFF_LINES=5 devforge_diff_or_summary "main"); RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q 'diff troncato oltre 5 righe'; then
    echo PASS; PASS=$((PASS+1))
else
    echo "FAIL — rc=$RC out=<<$OUT>>"; FAIL=$((FAIL+1))
fi
rm -rf "$TD"

echo "=== AC-5: base inesistente -> non hang, exit 0, nessun output vuoto pericoloso ==="
TD=$(_mkrepo)
OUT=$(cd "$TD" && devforge_diff_or_summary "refs/heads/does-not-exist" 2000 2>/dev/null); RC=$?
[ "$RC" -eq 0 ] && { echo PASS; PASS=$((PASS+1)); } || { echo "FAIL — rc=$RC"; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo ""; echo "RESULT: PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]
