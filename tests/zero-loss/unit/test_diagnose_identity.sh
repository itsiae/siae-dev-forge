#!/usr/bin/env bash
# Unit tests: task-08 — P2: probe diagnose-identity.sh
#
# Verifica che scripts/diagnose-identity.sh:
#   T1: gira sotto set -euo pipefail senza errori di runtime
#   T2: stampa tutte le chiavi previste
#   T3: stampa una riga VERDICT
#   T4: con CLAUDE_CONFIG_DIR impostato a un path il cui .claude.json esiste
#       → "CLAUDE_CONFIG_DIR onorato=si" + "VERDICT: ISOLATED"
#   T5: con oauth_email vuoto (file .claude.json senza oauthAccount)
#       → "VERDICT: NO-AUTH"
#   T6: con CLAUDE_CONFIG_DIR non settato e .claude.json in HOME
#       → "VERDICT: SHARED-DEGENERATE"
#   T7: oauth_account_uuid mascherato (≤9 char visibili prima di "…")
#
# Nota: NON aggiungere trap EXIT dentro funzioni invocate via $(...) — distrugge
# il trap del chiamante nel subshell.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCRIPT="${REPO_ROOT}/scripts/diagnose-identity.sh"

fail=0
pass=0

assert() {
    local name="$1" actual="$2" expected="$3"
    if [ "$actual" = "$expected" ]; then
        echo "  PASS: $name"
        pass=$((pass + 1))
    else
        echo "  FAIL: $name — expected '$expected' got '$actual'"
        fail=$((fail + 1))
    fi
}

assert_contains() {
    local name="$1" haystack="$2" needle="$3"
    if printf '%s' "$haystack" | grep -qF "$needle"; then
        echo "  PASS: $name"
        pass=$((pass + 1))
    else
        echo "  FAIL: $name — output non contiene '$needle'"
        fail=$((fail + 1))
    fi
}

assert_not_contains() {
    local name="$1" haystack="$2" needle="$3"
    if printf '%s' "$haystack" | grep -qF "$needle"; then
        echo "  FAIL: $name — output contiene '$needle' (non dovrebbe)"
        fail=$((fail + 1))
    else
        echo "  PASS: $name"
        pass=$((pass + 1))
    fi
}

# Pre-flight: lo script esiste ed è eseguibile
if [ ! -f "$SCRIPT" ]; then
    echo "FATAL: script non trovato: $SCRIPT"
    exit 2
fi
if [ ! -x "$SCRIPT" ]; then
    echo "FATAL: script non eseguibile: $SCRIPT"
    exit 2
fi

# Helper: crea workspace isolato con .claude.json contenente oauth fittizio
_make_work_with_auth() {
    local work="$1"
    mkdir -p "$work/.claude"
    cat > "$work/.claude.json" <<'ENDJSON'
{
  "oauthAccount": {
    "emailAddress": "persona.test@siae.it",
    "accountUuid": "abcd1234-5678-90ef-abcd-1234567890ef",
    "organizationUuid": "org-uuid-test",
    "organizationName": "SIAE Test Org"
  }
}
ENDJSON
}

# ---------------------------------------------------------------------------
echo "TEST 1 — lo script gira senza errori (exit 0)"
WORK1=$(mktemp -d)
trap 'rm -rf "$WORK1"' EXIT

_make_work_with_auth "$WORK1"

out1=$(HOME="$WORK1" DEVFORGE_CLAUDE_JSON="$WORK1/.claude.json" \
       bash "$SCRIPT" 2>/dev/null)
rc1=$?
assert "T1: exit code 0" "$rc1" "0"

# ---------------------------------------------------------------------------
echo "TEST 2 — stampa tutte le chiavi previste"
# Chiavi obbligatorie nel output
for key in HOME CLAUDE_CONFIG_DIR claude_json_path claude_json_exists \
           oauth_email oauth_account_uuid os_user host_short json_interpreter \
           "CLAUDE_CONFIG_DIR onorato"; do
    assert_contains "T2: chiave '$key' presente" "$out1" "${key}="
done

# ---------------------------------------------------------------------------
echo "TEST 3 — stampa una riga VERDICT"
assert_contains "T3: riga VERDICT presente" "$out1" "VERDICT:"

# ---------------------------------------------------------------------------
echo "TEST 4 — CLAUDE_CONFIG_DIR settato + .claude.json esiste → onorato=si + ISOLATED"
WORK4=$(mktemp -d)
CFG_DIR4="$WORK4/.claude-persona"
mkdir -p "$CFG_DIR4"
cat > "$CFG_DIR4/.claude.json" <<'ENDJSON'
{
  "oauthAccount": {
    "emailAddress": "isolated.user@siae.it",
    "accountUuid": "iso12345-abcd-efgh-ijkl-mnopqrstuvwx",
    "organizationUuid": "org-iso-uuid",
    "organizationName": "SIAE Isolated"
  }
}
ENDJSON

out4=$(HOME="$WORK4" CLAUDE_CONFIG_DIR="$CFG_DIR4" DEVFORGE_CLAUDE_JSON="" \
       bash "$SCRIPT" 2>/dev/null)
rc4=$?
assert "T4a: exit code 0" "$rc4" "0"
assert_contains "T4b: onorato=si" "$out4" "CLAUDE_CONFIG_DIR onorato=si"
assert_contains "T4c: VERDICT ISOLATED" "$out4" "VERDICT: ISOLATED"
rm -rf "$WORK4"

# ---------------------------------------------------------------------------
echo "TEST 5 — oauth_email vuoto → VERDICT: NO-AUTH"
WORK5=$(mktemp -d)
mkdir -p "$WORK5/.claude"
# File .claude.json SENZA oauthAccount (simula bedrock / API key / non autenticato)
cat > "$WORK5/.claude.json" <<'ENDJSON'
{
  "apiKey": "sk-ant-fake-key-for-test"
}
ENDJSON

out5=$(HOME="$WORK5" DEVFORGE_CLAUDE_JSON="$WORK5/.claude.json" \
       bash "$SCRIPT" 2>/dev/null)
rc5=$?
assert "T5a: exit code 0" "$rc5" "0"
assert_contains "T5b: VERDICT NO-AUTH" "$out5" "VERDICT: NO-AUTH"
rm -rf "$WORK5"

# ---------------------------------------------------------------------------
echo "TEST 6 — CLAUDE_CONFIG_DIR non settato, .claude.json in HOME → SHARED-DEGENERATE"
WORK6=$(mktemp -d)
_make_work_with_auth "$WORK6"

out6=$(HOME="$WORK6" DEVFORGE_CLAUDE_JSON="$WORK6/.claude.json" \
       bash "$SCRIPT" 2>/dev/null)
rc6=$?
assert "T6a: exit code 0" "$rc6" "0"
assert_contains "T6b: onorato=no" "$out6" "CLAUDE_CONFIG_DIR onorato=no"
assert_contains "T6c: VERDICT SHARED-DEGENERATE" "$out6" "VERDICT: SHARED-DEGENERATE"
rm -rf "$WORK6"

# ---------------------------------------------------------------------------
echo "TEST 7 — oauth_account_uuid è mascherato (non espone UUID completo)"
# UUID completo in .claude.json: "abcd1234-5678-90ef-abcd-1234567890ef"
# Output atteso: "abcd1234…" (8 char + ellipsis)
uuid_line=$(printf '%s' "$out1" | grep '^oauth_account_uuid=')
uuid_val="${uuid_line#oauth_account_uuid=}"
# Deve contenere "…" (ellipsis)
assert_contains "T7a: uuid mascherato con ellipsis" "$uuid_val" "…"
# NON deve contenere il UUID completo (più di 8+1 char dopo il prefisso)
assert_not_contains "T7b: uuid completo non esposto" "$uuid_val" "abcd1234-5678"

# ---------------------------------------------------------------------------
echo "TEST 8 — no-regression: script non stampa il file .claude.json in chiaro"
# Il contenuto raw del file (apiKey, oauthAccount intero) non deve apparire nell'output
assert_not_contains "T8a: no dump file in chiaro" "$out1" '"oauthAccount"'
assert_not_contains "T8b: no apiKey in chiaro" "$out1" '"apiKey"'

# ---------------------------------------------------------------------------
echo ""
echo "SUMMARY: $pass passed, $fail failed"
exit $fail
