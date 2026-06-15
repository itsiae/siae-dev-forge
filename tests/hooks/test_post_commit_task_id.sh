#!/usr/bin/env bash
# Test: hooks/post-commit-review aggiunge meta.task_id a commit_created (e pr_* strutturale)
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="${PLUGIN_ROOT}/hooks/post-commit-review"
PASS=0; FAIL=0
ok() { if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

# Esegue il hook in un repo con remote dato; ritorna il valore meta.task_id dell'evento
# commit_created (stringa vuota se assente).
task_id_of_commit_created() {
    local remote="$1" H R payload act
    H="$(mktemp -d)"; mkdir -p "$H/.claude"
    R="$(mktemp -d)"
    ( cd "$R" && git init -q && git config user.email t@t.it && git config user.name t \
      && git remote add origin "$remote" \
      && echo a > a.txt && git add a.txt && git commit -qm init \
      && echo b >> a.txt && git commit -qam second ) >/dev/null 2>&1
    payload=$(python3 -c "import json;print(json.dumps({'tool_input':{'command':'git commit -m x'}}))")
    ( cd "$R" && printf '%s' "$payload" | HOME="$H" bash "$HOOK" >/dev/null 2>&1 || true )
    act="$H/.claude/devforge-activity.jsonl"
    python3 - "$act" <<'PY'
import json,sys
try:
    for ln in open(sys.argv[1]):
        e=json.loads(ln)
        if e.get("event")=="commit_created":
            print((e.get("meta") or {}).get("task_id",""))
            break
except Exception:
    print("")
PY
}

# In-scope itsiae → task_id non vuoto (12 hex)
TID_IN=$(task_id_of_commit_created "https://github.com/itsiae/test-repo.git")
ok "in-scope: commit_created.meta.task_id non vuoto" "[ -n '$TID_IN' ]"
ok "in-scope: task_id è 12-hex" "printf '%s' '$TID_IN' | grep -qE '^[0-9a-f]{12}\$'"

# Fuori scope (remote non-itsiae) → task_id vuoto
TID_OUT=$(task_id_of_commit_created "https://github.com/other/test-repo.git")
ok "fuori scope: task_id vuoto" "[ -z '$TID_OUT' ]"

# Strutturale: pr_opened / pr_merged / pr_metrics includono task_id nel meta
ok "pr_opened meta include task_id" "grep -A2 'pr_opened' '$HOOK' | grep -q 'task_id'"
ok "pr_merged meta include task_id" "grep -A2 'pr_merged' '$HOOK' | grep -q 'task_id'"
ok "pr_metrics meta include task_id" "grep -A2 'pr_metrics' '$HOOK' | grep -q 'task_id'"

echo ""; echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
