#!/usr/bin/env bash
# Test: cache git keyed per-cwd, nessuna contaminazione cross-repo (#1)
# Piano docs/plans/2026-06-18-statusline-activation-viz/ task-03
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATUSLINE="$(cd "$SCRIPT_DIR/../../statusline" && pwd)/devforge-statusline.sh"
PASS=0; FAIL=0

HOME_SB="$(mktemp -d)"; mkdir -p "$HOME_SB/.claude"

mk_repo() { mkdir -p "$1"; ( cd "$1" && git init -q && git checkout -q -b "$2" && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m init ) 2>/dev/null; }
R1="$(mktemp -d)/repoA"; mk_repo "$R1" "branch-aaa"
R2="$(mktemp -d)/repoB"; mk_repo "$R2" "branch-bbb"

render() { ( cd "$1" && printf '{}' | HOME="$HOME_SB" bash "$STATUSLINE" 2>/dev/null | head -1 ); }

OUT_A="$(render "$R1")"
OUT_B="$(render "$R2")"
if printf '%s' "$OUT_A" | grep -q "branch-aaa"; then PASS=$((PASS+1)); echo "  PASS  repoA mostra branch-aaa"; else FAIL=$((FAIL+1)); echo "  FAIL  repoA (out: $OUT_A)"; fi
if printf '%s' "$OUT_B" | grep -q "branch-bbb" && ! printf '%s' "$OUT_B" | grep -q "branch-aaa"; then
  PASS=$((PASS+1)); echo "  PASS  repoB mostra branch-bbb senza contaminazione"
else
  FAIL=$((FAIL+1)); echo "  FAIL  repoB contaminato (out: $OUT_B)"
fi
ncache=$(ls "$HOME_SB/.claude"/.devforge-git-cache* 2>/dev/null | wc -l | tr -d ' ')
if [ "$ncache" -ge 2 ]; then PASS=$((PASS+1)); echo "  PASS  cache keyed per-cwd ($ncache file)"; else FAIL=$((FAIL+1)); echo "  FAIL  cache non keyed ($ncache file)"; fi

rm -rf "$HOME_SB" "$(dirname "$R1")" "$(dirname "$R2")"
echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
