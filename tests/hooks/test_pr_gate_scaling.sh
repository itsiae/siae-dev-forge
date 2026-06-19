#!/usr/bin/env bash
# test_pr_gate_scaling.sh — i gate PR scalano ad advisory su diff risk=low.
# Design: docs/plans/2026-06-19-pr-gate-proportional-scaling-design.md
# NB: HOME è una dir SEPARATA dal repo temp — altrimenti git add -A nel repo
# catturerebbe home/.claude/* inquinando il diff (lezione: HOME fuori dal working tree).
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"

_mkrepo() {
    local td; td=$(mktemp -d)
    ( cd "$td" && git init -q && git config user.email t@t && git config user.name t \
      && echo s > s.txt && git add -A && git commit -qm s && git branch -m main \
      && git remote add origin https://github.com/itsiae/fake.git \
      && git checkout -qb work ) >/dev/null 2>&1
    echo "$td"
}
# $1=hook-name $2=repodir → stdout del gate. HOME separata (no inquinamento diff).
_run_gate() {
    local home; home=$(mktemp -d); mkdir -p "$home/.claude"; : > "$home/.claude/.devforge-session-skills"
    git -C "$2" update-ref refs/remotes/origin/main "$(git -C "$2" rev-parse main)" >/dev/null 2>&1
    printf '{"tool_input":{"command":"gh pr create --base main"}}' \
      | ( cd "$2" && HOME="$home" DEVFORGE_USE_SESSION_SCOPE=1 \
          bash "${REPO_ROOT}/hooks/$1" 2>/dev/null )
    rm -rf "$home"
}

for GATE in pr-premortem-gate pr-blind-review-gate; do
  echo "=== $GATE AC-7/9: diff doc-only + skill NON validata → advisory (no block) ==="
  TD=$(_mkrepo)
  ( cd "$TD" && echo x > a.md && git add -A && git commit -qm m ) >/dev/null 2>&1
  OUT=$(_run_gate "$GATE" "$TD")
  if ! echo "$OUT" | grep -q '"decision": "block"'; then echo "  PASS"; PASS=$((PASS+1)); else echo "  FAIL: $OUT"; FAIL=$((FAIL+1)); fi
  rm -rf "$TD"

  echo "=== $GATE AC-8/9: diff con hooks/ + skill NON validata → block (no-regression) ==="
  TD=$(_mkrepo)
  ( cd "$TD" && mkdir -p hooks && echo y > hooks/foo && git add -A && git commit -qm m ) >/dev/null 2>&1
  OUT=$(_run_gate "$GATE" "$TD")
  if echo "$OUT" | grep -q '"decision": "block"'; then echo "  PASS"; PASS=$((PASS+1)); else echo "  FAIL: $OUT"; FAIL=$((FAIL+1)); fi
  rm -rf "$TD"
done

echo "=== AC-10: floor security — pre-commit NON modificato da questo task ==="
if git -C "$REPO_ROOT" diff origin/main...HEAD --name-only 2>/dev/null | grep -qx 'hooks/pre-commit'; then
  echo "  FAIL: pre-commit modificato"; FAIL=$((FAIL+1))
else
  echo "  PASS: pre-commit intatto"; PASS=$((PASS+1))
fi

echo ""; echo "RESULT: PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]
