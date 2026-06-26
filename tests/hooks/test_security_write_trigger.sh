#!/usr/bin/env bash
# test_security_write_trigger.sh — TDD hook security-write-trigger (PreToolUse:Edit/Write)
# Advisory (non-blocking) su file security-sensibili se siae-security non invocata.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HOOK="${REPO_ROOT}/hooks/security-write-trigger"

PASS=0; FAIL=0
ok(){ if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

TEST_HOME="$(mktemp -d)"; trap 'rm -rf "$TEST_HOME"' EXIT; mkdir -p "$TEST_HOME/.claude"
SKILLS="$TEST_HOME/.claude/.devforge-session-skills"

run(){ printf '{"tool_input":{"file_path":"%s"}}' "$1" | HOME="$TEST_HOME" bash "$HOOK" 2>/dev/null; }

echo "TEST security-write-trigger"

# T1: file auth SENZA siae-security invocata -> advisory (additionalContext)
: > "$SKILLS"   # nessuna skill
out=$(run "src/auth/LoginService.java")
ok "T1: file auth senza siae-security -> advisory" 'printf "%s" "$out" | grep -q "additionalContext"'
ok "T1b: advisory non blocca (no decision block)" '! printf "%s" "$out" | grep -q "\"decision\": \"block\""'
ok "T1c: output JSON valido" 'printf "%s" "$out" | jq . >/dev/null 2>&1'

# T2: file auth CON siae-security invocata -> silenzioso
echo "siae-security" > "$SKILLS"
out=$(run "src/auth/LoginService.java")
ok "T2: file auth con siae-security -> silenzioso" '! printf "%s" "$out" | grep -q "additionalContext"'

# T3: file NON security (con siae-security irrilevante) -> silenzioso
: > "$SKILLS"
out=$(run "src/utils/StringHelper.java")
ok "T3: file non-security -> silenzioso" '! printf "%s" "$out" | grep -q "additionalContext"'

# T4: file .env senza siae-security -> advisory
out=$(run "config/prod.env")
ok "T4: file .env -> advisory" 'printf "%s" "$out" | grep -q "additionalContext"'

# T5: input vuoto -> exit 0, nessun crash (output JSON o vuoto, mai block)
out=$(printf '' | HOME="$TEST_HOME" bash "$HOOK" 2>/dev/null)
ok "T5: input vuoto -> no block" '! printf "%s" "$out" | grep -q "\"decision\": \"block\""'

echo ""; echo "PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]
