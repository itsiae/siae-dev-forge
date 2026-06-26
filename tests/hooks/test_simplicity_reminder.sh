#!/usr/bin/env bash
# test_simplicity_reminder.sh — TDD per hook simplicity-reminder (UserPromptSubmit)
# Contatore GLOBALE cumulativo: inietta il principio ogni 5 prompt, robusto a
# sessioni concorrenti (vedi premortem nel design — niente reset per-sessione).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HOOK="${REPO_ROOT}/hooks/simplicity-reminder"

PASS=0; FAIL=0
ok(){ if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

# HOME isolata: il counter state vive in $HOME/.claude, non nel repo
TEST_HOME="$(mktemp -d)"
trap 'rm -rf "$TEST_HOME"' EXIT
mkdir -p "$TEST_HOME/.claude"

# Esegue il hook (con un session_id qualsiasi nello stdin: il hook NON lo usa,
# il contatore e' globale — qui serve solo a simulare prompt distinti)
run_prompt(){ printf '{"session_id":"%s","prompt":"x"}' "${1:-s}" | HOME="$TEST_HOME" bash "$HOOK" 2>/dev/null; }

echo "TEST simplicity-reminder (contatore globale)"

# --- prompt 1..4 silenziosi, 5 inietta ---
out=$(run_prompt s1)                                  # n=1
ok "T1: 1deg prompt nessuna iniezione" '[ -z "$out" ]'
run_prompt s1 >/dev/null; run_prompt s1 >/dev/null; run_prompt s1 >/dev/null   # n=2,3,4
out=$(run_prompt s1)                                  # n=5
ok "T2: 5deg prompt inietta il principio" 'printf "%s" "$out" | grep -q "YAGNI"'
ok "T5: stdout e JSON valido" 'printf "%s" "$out" | jq . >/dev/null 2>&1'

# --- periodicita: 6..9 silenziosi, 10 inietta ---
for _ in 1 2 3 4; do run_prompt s1 >/dev/null; done   # n=6,7,8,9
out=$(run_prompt s1)                                  # n=10
ok "T4: 10deg prompt inietta (periodicita ogni 5)" 'printf "%s" "$out" | grep -q "YAGNI"'

# --- ROBUSTEZZA CONCORRENZA (mitigazione premortem): session_id DIVERSI non
#     resettano il contatore globale -> al 15deg cumulativo inietta comunque ---
run_prompt s2 >/dev/null   # n=11 (sid diverso)
run_prompt s1 >/dev/null   # n=12
run_prompt s3 >/dev/null   # n=13 (altro sid)
run_prompt s1 >/dev/null   # n=14
out=$(run_prompt s2)       # n=15 -> inietta (NON resettato da sid concorrenti)
ok "T3: contatore cumulativo robusto a session_id concorrenti" 'printf "%s" "$out" | grep -q "YAGNI"'

# --- fail-safe: input malformato -> exit 0, nessun crash ---
printf 'not-json' | HOME="$TEST_HOME" bash "$HOOK" >/dev/null 2>&1; rc=$?
ok "T6: input malformato exit 0 (fail-safe)" '[ "$rc" -eq 0 ]'

echo ""
echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
