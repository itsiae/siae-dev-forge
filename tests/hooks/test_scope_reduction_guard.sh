#!/usr/bin/env bash
# test_scope_reduction_guard.sh — TDD hook scope-reduction-guard (PreToolUse:Write)
# Confronta requisiti del design doc vs piano: warn >30% / block >60% non tracciati.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HOOK="${REPO_ROOT}/hooks/scope-reduction-guard"

PASS=0; FAIL=0
ok(){ if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

TEST_HOME="$(mktemp -d)"; trap 'rm -rf "$TEST_HOME" "$TEST_REPO"' EXIT; mkdir -p "$TEST_HOME/.claude"
TEST_REPO="$(mktemp -d)"; mkdir -p "$TEST_REPO/docs/plans"

# design doc con 3 requisiti, keyword distintive: login / logout / bcrypt
cat > "$TEST_REPO/docs/plans/2026-01-01-foo-design.md" <<'D'
## 7. Criteri di accettazione
- AC-1: il sistema esegue il login validando le credenziali
- AC-2: il logout invalida correttamente la sessione utente
- AC-3: la password viene memorizzata con hashing bcrypt
D

# invoca l'hook nel cwd del test repo, file_path=piano, content=$1
run(){ printf '{"tool_input":{"file_path":"docs/plans/2026-01-01-foo/overview.md","content":"%s"}}' "$1" | (cd "$TEST_REPO" && HOME="$TEST_HOME" bash "$HOOK" 2>/dev/null); }

echo "TEST scope-reduction-guard"

# T1: piano COMPLETO (tutti e 3 i requisiti tracciati) -> pass (no block, no warn)
out=$(run "Task: implementare login con credenziali, logout che invalida la sessione, e password con bcrypt.")
ok "T1: piano completo -> no block" '! printf "%s" "$out" | grep -q "\"decision\": \"block\""'

# T2: 1/3 mancante (33%, >30% <60%) -> warn advisory (additionalContext, NON block)
out=$(run "Task: implementare login con credenziali e logout della sessione.")
ok "T2: 33% mancante -> warn (no block)" '! printf "%s" "$out" | grep -q "\"decision\": \"block\""'
ok "T2b: warn presente (additionalContext)" 'printf "%s" "$out" | grep -qi "additionalContext\|scope\|requisit"'

# T3: 2/3 mancante (66%, >60%) -> block
out=$(run "Task: implementare solo il login.")
ok "T3: 66% mancante -> block" 'printf "%s" "$out" | grep -q "\"decision\": \"block\""'

# T4: nessun design doc -> exit 0 pass
EMPTY_REPO="$(mktemp -d)"; mkdir -p "$EMPTY_REPO/docs/plans"
out=$(printf '{"tool_input":{"file_path":"docs/plans/x/overview.md","content":"qualsiasi"}}' | (cd "$EMPTY_REPO" && HOME="$TEST_HOME" bash "$HOOK" 2>/dev/null)); rm -rf "$EMPTY_REPO"
ok "T4: nessun design doc -> no block" '! printf "%s" "$out" | grep -q "\"decision\": \"block\""'

# T5: design con 0 requisiti estratti -> no div/0, no block
ZERO_REPO="$(mktemp -d)"; mkdir -p "$ZERO_REPO/docs/plans"; printf '# Design senza requisiti\nSolo prosa.\n' > "$ZERO_REPO/docs/plans/2026-01-01-z-design.md"
out=$(printf '{"tool_input":{"file_path":"docs/plans/z/overview.md","content":"x"}}' | (cd "$ZERO_REPO" && HOME="$TEST_HOME" bash "$HOOK" 2>/dev/null)); rm -rf "$ZERO_REPO"
ok "T5: design 0 requisiti -> no block (no div/0)" '! printf "%s" "$out" | grep -q "\"decision\": \"block\""'

# T6: file NON piano (random .md) -> pass silenzioso
out=$(printf '{"tool_input":{"file_path":"README.md","content":"x"}}' | (cd "$TEST_REPO" && HOME="$TEST_HOME" bash "$HOOK" 2>/dev/null))
ok "T6: file non-piano -> no block" '! printf "%s" "$out" | grep -q "\"decision\": \"block\""'

echo ""; echo "PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]
