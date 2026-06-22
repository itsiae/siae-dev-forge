#!/usr/bin/env bash
# test_session_end_hook.sh — nuovo hook SessionEnd: emit session_end senza rm stato.
# Design: docs/plans/2026-06-19-stop-gate-session-lifecycle-fix-design.md
# Copre AC-5 (emit conteggi), AC-6 (idempotenza), AC-7 (no rm), AC-8 (accumulati),
# AC-10 (reason=resume preserva stato).
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK="${REPO_ROOT}/hooks/session-end"

# Seed: HOME temp + counters + log file isolato. Ritorna il path di HOME.
_seed_home() {
    local th; th=$(mktemp -d)
    mkdir -p "$th/.claude"
    printf 'siae-tdd,siae-git-workflow,siae-verification\n' > "$th/.claude/.devforge-session-skills"
    printf '4\n' > "$th/.claude/.devforge-session-commits"
    printf '1000000000\n' > "$th/.claude/.devforge-session-start-ns"
    echo "$th"
}

# Invoca il hook con un payload SessionEnd su stdin (reason configurabile).
_run() {  # $1=HOME $2=reason
    printf '{"hook_event_name":"SessionEnd","reason":"%s","session_id":"t"}' "${2:-other}" \
        | HOME="$1" DEVFORGE_LOG_FILE="$1/.claude/devforge.jsonl" bash "$HOOK" 2>/dev/null || true
}

echo "=== AC-5/AC-8: emit session_end con conteggi accumulati + schema ==="
TH=$(_seed_home); _run "$TH" other
LOG="$TH/.claude/devforge.jsonl"
if grep -q '"event":"session_end"' "$LOG" 2>/dev/null \
   && grep -q '"skills_used_count":3' "$LOG" 2>/dev/null \
   && grep -q '"commits_count":4' "$LOG" 2>/dev/null \
   && grep -q '"token_state_complete"' "$LOG" 2>/dev/null \
   && grep -q '"by_model"' "$LOG" 2>/dev/null \
   && grep -q '"by_tool"' "$LOG" 2>/dev/null; then
    echo "  PASS  session_end skills=3 commits=4 + schema completo"; PASS=$((PASS+1))
else
    echo "  FAIL  atteso session_end skills=3 commits=4 + campi schema; log: $(tail -1 "$LOG" 2>/dev/null)"; FAIL=$((FAIL+1))
fi
rm -rf "$TH"

echo "=== AC-6: idempotenza — seconda invocazione non riemette ==="
TH=$(_seed_home); _run "$TH" other; _run "$TH" other
N=$(grep -c '"event":"session_end"' "$TH/.claude/devforge.jsonl" 2>/dev/null || echo 0)
if [ "$N" -eq 1 ]; then
    echo "  PASS  esattamente 1 session_end"; PASS=$((PASS+1))
else
    echo "  FAIL  attesi 1 session_end, trovati $N"; FAIL=$((FAIL+1))
fi
rm -rf "$TH"

echo "=== AC-7: NESSUN rm dei file di stato ==="
TH=$(_seed_home); _run "$TH" other
if [ -f "$TH/.claude/.devforge-session-skills" ] \
   && [ -f "$TH/.claude/.devforge-session-commits" ] \
   && [ -f "$TH/.claude/.devforge-session-start-ns" ]; then
    echo "  PASS  file di stato preservati"; PASS=$((PASS+1))
else
    echo "  FAIL  file di stato cancellati (regressione del bug)"; FAIL=$((FAIL+1))
fi
rm -rf "$TH"

echo "=== AC-10: reason=resume — file preservati ==="
TH=$(_seed_home); _run "$TH" resume
if [ -f "$TH/.claude/.devforge-session-skills" ] \
   && grep -qF 'siae-git-workflow' "$TH/.claude/.devforge-session-skills"; then
    echo "  PASS  resume: ledger intatto"; PASS=$((PASS+1))
else
    echo "  FAIL  resume: ledger perso"; FAIL=$((FAIL+1))
fi
rm -rf "$TH"

echo ""
echo "RESULT: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
