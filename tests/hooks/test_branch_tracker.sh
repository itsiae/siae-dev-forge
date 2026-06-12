#!/usr/bin/env bash
# Test branch-tracker: emette branch_created su creazione branch (task-01)
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TEST_TMP=$(mktemp -d); trap 'rm -rf "$TEST_TMP"' EXIT
export HOME="$TEST_TMP"; mkdir -p "$HOME/.claude"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
PASS=0; FAIL=0
ok(){ echo "  PASS: $1"; PASS=$((PASS+1)); }
ko(){ echo "  FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }

REPO="$TEST_TMP/repo"; mkdir -p "$REPO"; cd "$REPO"
git init -q && git config user.email t@t && git config user.name t
git commit -q --allow-empty -m init && git branch -m main

LOG="$HOME/.claude/devforge-activity.jsonl"
run_hook(){ : > "$LOG"
  printf '{"tool_input":{"command":"%s"},"cwd":"%s"}' "$1" "$REPO" \
    | bash "$PLUGIN_ROOT/hooks/branch-tracker" >/dev/null 2>&1 || true
}
ev_count(){ grep -c '"event":"branch_created"' "$LOG" 2>/dev/null || true; }
ev_base(){ grep -o '"base_branch":"[^"]*"' "$LOG" | head -1 | sed 's/.*"base_branch":"//;s/"$//'; }

# T1 — checkout -b da main
git checkout -q -b feature/x
run_hook "git checkout -b feature/x"
{ [ "$(ev_count)" = "1" ] && [ "$(ev_base)" = "main" ]; } && ok "T1 checkout -b base=main" || ko "T1" "count=$(ev_count) base=$(ev_base)"

# T2 — switch -c
git switch -q -c feature/y
run_hook "git switch -c feature/y"
{ [ "$(ev_count)" = "1" ] && [ "$(ev_base)" = "feature/x" ]; } && ok "T2 switch -c base=feature/x" || ko "T2" "count=$(ev_count) base=$(ev_base)"

# T3 — checkout branch esistente (no -b) → no evento
git checkout -q main
run_hook "git checkout main"
{ [ "$(ev_count)" = "0" ]; } && ok "T3 checkout existing: no evento" || ko "T3" "count=$(ev_count)"

# T3b — checkout -b fallito (esiste): HEAD non cambia → no evento
git checkout -q main
run_hook "git checkout -b feature/x"
{ [ "$(ev_count)" = "0" ]; } && ok "T3b checkout -b fallito: no evento" || ko "T3b" "count=$(ev_count)"

# T3c — detached HEAD → checkout -b: base vuoto
FIRST=$(git rev-parse HEAD); git checkout -q "$FIRST"
git checkout -q -b feature/d
run_hook "git checkout -b feature/d"
{ [ "$(ev_count)" = "1" ] && [ -z "$(ev_base)" ]; } && ok "T3c detached: base vuoto" || ko "T3c" "count=$(ev_count) base='$(ev_base)'"

# T3d — flag intermedio -q -b → evento emesso
git checkout -q main; git checkout -q -b feature/q
run_hook "git checkout -q -b feature/q"
{ [ "$(ev_count)" = "1" ] && [ "$(ev_base)" = "main" ]; } && ok "T3d checkout -q -b: evento" || ko "T3d" "count=$(ev_count) base=$(ev_base)"

# T4 — branch/repo top-level, no dup nel meta
git checkout -q main; git checkout -q -b feature/z
run_hook "git checkout -b feature/z"
line=$(grep '"event":"branch_created"' "$LOG" | head -1)
has_top=$(echo "$line" | grep -o '"branch":"feature/z"' | head -1)
meta_part=$(echo "$line" | sed 's/.*"meta"://')
meta_dup=$(echo "$meta_part" | grep -o '"branch":' | head -1)
{ [ -n "$has_top" ] && [ -z "$meta_dup" ]; } && ok "T4 branch top-level, no dup meta" || ko "T4" "top='$has_top' metadup='$meta_dup'"

echo "branch-tracker: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
