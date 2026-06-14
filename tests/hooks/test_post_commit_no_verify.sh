#!/usr/bin/env bash
# Test: hooks/post-commit-review emette gate_bypassed git_no_verify su commit --no-verify/-n
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="${PLUGIN_ROOT}/hooks/post-commit-review"
PASS=0; FAIL=0
ok() { if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

# Setup: fresh HOME (saved-hash vuoto) + repo con 2 commit (HEAD~1 valido). Esegue il
# hook con un payload Bash che porta il comando da analizzare. Ritorna il path activity.jsonl.
run_with_cmd() {
    local cmd="$1" H R payload
    H="$(mktemp -d)"; mkdir -p "$H/.claude"
    R="$(mktemp -d)"
    ( cd "$R" && git init -q && git config user.email t@t.it && git config user.name t \
      && echo a > a.txt && git add a.txt && git commit -qm init \
      && echo b >> a.txt && git commit -qam second ) >/dev/null 2>&1
    payload=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$cmd")
    ( cd "$R" && printf '%s' "$payload" | HOME="$H" bash "$HOOK" >/dev/null 2>&1 || true )
    echo "$H/.claude/devforge-activity.jsonl"
}

has_bypass() { [ -s "$1" ] && grep -q 'gate_bypassed' "$1" && grep -q 'git_no_verify' "$1"; }

# POS 1: --no-verify
A=$(run_with_cmd 'git commit --no-verify -m "msg"')
ok "POS --no-verify emette git_no_verify" "has_bypass '$A'"

# POS 2: -nm (cluster con n)
B=$(run_with_cmd 'git commit -nm "msg"')
ok "POS -nm emette git_no_verify" "has_bypass '$B'"

# NEG: -n dentro il messaggio (deve emettere commit_created ma NON gate_bypassed)
C=$(run_with_cmd 'git commit -m "fix -n test"')
ok "NEG '-n' nel messaggio: commit_created presente" "[ -s '$C' ] && grep -q 'commit_created' '$C'"
ok "NEG '-n' nel messaggio: nessun git_no_verify" "! has_bypass '$C'"

echo ""; echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
