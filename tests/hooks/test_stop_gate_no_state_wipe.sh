#!/usr/bin/env bash
# test_stop_gate_no_state_wipe.sh — Stop non deve cancellare lo stato di sessione.
# Design: docs/plans/2026-06-19-stop-gate-session-lifecycle-fix-design.md
# Copre AC-1 (skills preservato), AC-2 (commits/start-ns preservati),
# AC-3 (block no-regression), AC-4 (allow no-regression).
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK="${REPO_ROOT}/hooks/stop-gate"

# transcript SENZA keyword di completamento
_no_completion() {
    cat <<'JSON'
{"messages":[{"role":"user","content":"continua"},{"role":"assistant","content":"sto lavorando sul punto successivo"}]}
JSON
}

_seed() {  # ritorna HOME temp con ledger popolato
    local th; th=$(mktemp -d); mkdir -p "$th/.claude"
    printf 'siae-git-workflow\n' > "$th/.claude/.devforge-session-skills"
    printf '2\n' > "$th/.claude/.devforge-session-commits"
    printf '1000000000\n' > "$th/.claude/.devforge-session-start-ns"
    echo "$th"
}

echo "=== AC-1: Stop no-completion NON cancella session-skills ==="
TH=$(_seed)
_no_completion | HOME="$TH" bash "$HOOK" >/dev/null 2>&1 || true
if [ -f "$TH/.claude/.devforge-session-skills" ] \
   && grep -qF 'siae-git-workflow' "$TH/.claude/.devforge-session-skills"; then
    echo "  PASS  session-skills preservato"; PASS=$((PASS+1))
else
    echo "  FAIL  session-skills cancellato (bug primario)"; FAIL=$((FAIL+1))
fi
rm -rf "$TH"

echo "=== AC-2: Stop stdin vuoto NON cancella commits/start-ns ==="
TH=$(_seed)
printf '' | HOME="$TH" bash "$HOOK" >/dev/null 2>&1 || true
if [ -f "$TH/.claude/.devforge-session-commits" ] \
   && [ -f "$TH/.claude/.devforge-session-start-ns" ]; then
    echo "  PASS  commits/start-ns preservati"; PASS=$((PASS+1))
else
    echo "  FAIL  commits/start-ns cancellati"; FAIL=$((FAIL+1))
fi
rm -rf "$TH"

echo "=== AC-3: completion + no verification → block (no-regression) ==="
TH=$(_seed); printf 'siae-retrospective\n' > "$TH/.claude/.devforge-session-skills"
OUT=$(printf '{"messages":[{"role":"assistant","content":"fatto, completato"}]}' \
    | HOME="$TH" env DEVFORGE_USE_SESSION_SCOPE=1 bash "$HOOK" 2>/dev/null || true)
if echo "$OUT" | grep -q '"decision": "block"' && echo "$OUT" | grep -q 'siae-verification'; then
    echo "  PASS  block emesso"; PASS=$((PASS+1))
else
    echo "  FAIL  atteso block: $(echo "$OUT" | head -2)"; FAIL=$((FAIL+1))
fi
rm -rf "$TH"

echo "=== AC-4: completion + verification → allow (no-regression) ==="
TH=$(_seed); printf 'siae-verification,siae-retrospective\n' > "$TH/.claude/.devforge-session-skills"
OUT=$(printf '{"messages":[{"role":"assistant","content":"fatto, completato"}]}' \
    | HOME="$TH" env DEVFORGE_USE_SESSION_SCOPE=1 bash "$HOOK" 2>/dev/null || true)
if ! echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  allow"; PASS=$((PASS+1))
else
    echo "  FAIL  block inatteso: $(echo "$OUT" | head -2)"; FAIL=$((FAIL+1))
fi
rm -rf "$TH"

echo ""
echo "RESULT: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
