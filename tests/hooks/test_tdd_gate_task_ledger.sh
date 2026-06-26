#!/usr/bin/env bash
# test_tdd_gate_task_ledger.sh — tdd-gate must honor the DURABLE per-task
# ledger (RC-B). The session-skills file is ephemeral: session-start wipes it
# on a true cold start, and post-skill never records siae-tdd if sub-skill-gate
# rejected the Skill call. The per-task ledger (.devforge-task-skills/<id>/
# skills_invoked, written by post-skill) survives those events. The gate's
# allow/block decision must fall back to it, else a compact/reset mid-task
# false-blocks an already-TDD'd task.
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK="${REPO_ROOT}/hooks/tdd-gate"

if [ ! -f "$HOOK" ]; then
    echo "FAIL — $HOOK not found"; exit 1
fi

# Isolated itsiae/* git repo with a production .py file.
WORK=$(mktemp -d)
ISOHOME=$(mktemp -d)
mkdir -p "$ISOHOME/.claude"
(
  cd "$WORK"
  git init -q
  git remote add origin https://github.com/itsiae/fake-repo.git
  git config user.email t@t.it
  git config user.name tester
  mkdir -p src
  echo "x = 1" > src/app.py
  git add -A
  git commit -qm init
)

# Compute task_id exactly as the gate does (same lib, same cwd, same HOME).
# shellcheck source=/dev/null
source "${REPO_ROOT}/lib/task-id.sh"
TASK_ID=$(cd "$WORK" && HOME="$ISOHOME" devforge_compute_task_id)

_run_gate() {
    echo "{\"file_path\":\"${WORK}/src/app.py\"}" | HOME="$ISOHOME" bash "$HOOK" 2>&1 || true
}

echo "=== 1. session-skills empty BUT task ledger has siae-tdd → ALLOW ==="
: > "$ISOHOME/.claude/.devforge-session-skills"          # simulate post-compact wipe
mkdir -p "$ISOHOME/.claude/.devforge-task-skills/${TASK_ID}"
printf 'siae-tdd\n' > "$ISOHOME/.claude/.devforge-task-skills/${TASK_ID}/skills_invoked"
OUT=$(_run_gate)
if ! echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  ledger-only siae-tdd → allowed"; PASS=$((PASS+1))
else
    echo "  FAIL  expected ALLOW via ledger, got:"; echo "$OUT" | head -3; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 2. Negative control: no session-skills AND no ledger → BLOCK ==="
rm -rf "$ISOHOME/.claude/.devforge-task-skills"
: > "$ISOHOME/.claude/.devforge-session-skills"
OUT2=$(_run_gate)
if echo "$OUT2" | grep -q '"decision": "block"'; then
    echo "  PASS  no evidence anywhere → blocked"; PASS=$((PASS+1))
else
    echo "  FAIL  expected BLOCK (no evidence), got:"; echo "$OUT2" | head -3; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 3. Ledger present but WITHOUT siae-tdd → BLOCK (file presence alone is not enough) ==="
mkdir -p "$ISOHOME/.claude/.devforge-task-skills/${TASK_ID}"
printf 'siae-brainstorming\nsiae-finishing-branch\n' \
    > "$ISOHOME/.claude/.devforge-task-skills/${TASK_ID}/skills_invoked"
: > "$ISOHOME/.claude/.devforge-session-skills"
OUT3=$(_run_gate)
if echo "$OUT3" | grep -q '"decision": "block"'; then
    echo "  PASS  ledger without siae-tdd → blocked (grep -qxF exact-line match)"; PASS=$((PASS+1))
else
    echo "  FAIL  expected BLOCK (ledger lacks siae-tdd), got:"; echo "$OUT3" | head -3; FAIL=$((FAIL+1))
fi

rm -rf "$WORK" "$ISOHOME"
echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
