#!/usr/bin/env bash
# test_uncertainty_escalation.sh — TDD hook uncertainty-escalation (evento Stop)
# Escalation proattiva: >=2 pattern di incertezza FORTI + assenza di '?' -> decision:block.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HOOK="${REPO_ROOT}/hooks/uncertainty-escalation"

PASS=0; FAIL=0
ok(){ if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

TEST_HOME="$(mktemp -d)"; trap 'rm -rf "$TEST_HOME"' EXIT; mkdir -p "$TEST_HOME/.claude"

# Costruisce input JSON evento Stop con ultimo messaggio assistant = $1
mk(){ printf '{"messages":[{"role":"user","content":"q"},{"role":"assistant","content":"%s"}]}' "$1"; }
run(){ mk "$1" | HOME="$TEST_HOME" bash "$HOOK" 2>/dev/null; }

echo "TEST uncertainty-escalation"

# T1: >=2 pattern forti, nessun '?' -> block
out=$(run "non so quale endpoint usare e non ho abbastanza informazioni sul payload.")
ok "T1: >=2 pattern forti senza ? -> block" 'printf "%s" "$out" | grep -q "block"'
ok "T1b: output e JSON valido" 'printf "%s" "$out" | jq . >/dev/null 2>&1'

# T2: stessi pattern MA con '?' (domanda gia posta) -> no block
out=$(run "non so quale endpoint, non ho abbastanza informazioni. Quale preferisci?")
ok "T2: incertezza CON domanda (?) -> no block" '! printf "%s" "$out" | grep -q "\"decision\": \"block\""'

# T3: un solo pattern -> sotto soglia -> no block
out=$(run "non so quale sia la soluzione migliore tra le due.")
ok "T3: <2 pattern -> no block" '! printf "%s" "$out" | grep -q "\"decision\": \"block\""'

# T4: pattern ambigui (forse/dipende) NON devono triggerare (mitigazione falsi positivi)
out=$(run "forse questo approccio, forse quello; dipende da come lo usi, potrebbe essere lento.")
ok "T4: pattern ambigui (forse/dipende/potrebbe) -> no block" '! printf "%s" "$out" | grep -q "\"decision\": \"block\""'

# T5: input vuoto -> exit 0, nessun output (fail-safe)
out=$(printf '' | HOME="$TEST_HOME" bash "$HOOK" 2>/dev/null)
ok "T5: input vuoto -> exit 0 nessun output" '! printf "%s" "$out" | grep -q "\"decision\": \"block\""'

# T6: messaggio normale di completamento -> no block
out=$(run "Ho implementato la feature e tutti i test passano.")
ok "T6: messaggio normale senza incertezza -> no block" '! printf "%s" "$out" | grep -q "\"decision\": \"block\""'

echo ""; echo "PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]
