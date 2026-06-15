#!/usr/bin/env bash
# Unit tests: task-03 — F2b siti identità-critici instradati su devforge_json_field.
#
# Verifica che con python3 mascherato e node disponibile:
#   T1: devforge_resolve_auth_identity produce auth_email/auth_account_uuid non vuoti
#   T2: devforge_init_session popola DEVFORGE_PINNED_USER/AUTH_EMAIL/AUTH_ACCOUNT_UUID
#   T3: devforge_get_user_raw legge user.json via node (non python3)
#   T4: devforge_get_user_source legge user.json via node (non python3)
#   T5: devforge_session_token_total produce un intero (via devforge_json_field)
#   T6: no-regression — con python3 disponibile i valori sono identici al baseline
#
# Nota: NON aggiungere trap EXIT dentro funzioni invocate via $(...) — distrugge
# il trap del chiamante nel subshell.
#
# Nota ordine source: lib/logger.sh setta DEVFORGE_SESSION_USER_FILE e
# DEVFORGE_SESSION_USER_SOURCE_FILE a path assoluti basati su $HOME al momento
# del source. Quindi HOME deve essere settato PRIMA del source, non dopo.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LOGGER="${REPO_ROOT}/lib/logger.sh"

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

assert_nonempty() {
    local name="$1" actual="$2"
    if [ -n "$actual" ]; then
        echo "  PASS: $name (value='$actual')"
        pass=$((pass + 1))
    else
        echo "  FAIL: $name — expected non-empty, got empty"
        fail=$((fail + 1))
    fi
}

# --- setup isolated workspace (HOME PRIMA del source) ---
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# Impostare HOME prima del source così logger.sh costruisce i path corretti
export HOME="$WORK"
mkdir -p "$WORK/.claude"

# Seed SID file so devforge_init_session lands in the same session dir
echo "testsid" > "$WORK/.claude/.devforge-session-id"

SESSION_DIR="$WORK/.claude/devforge-state/testsid"
mkdir -p "$SESSION_DIR"

# .claude.json fittizio con campi oauthAccount (path via DEVFORGE_CLAUDE_JSON)
cat > "$WORK/.claude.json" <<'EOF'
{
  "oauthAccount": {
    "emailAddress": "portable.test@siae.it",
    "accountUuid": "portable-uuid-1234",
    "organizationUuid": "portable-org-uuid-5678",
    "organizationName": "SIAE Portable"
  }
}
EOF
export DEVFORGE_CLAUDE_JSON="$WORK/.claude.json"

# user.json fittizio (come scritto da session-start)
cat > "$SESSION_DIR/user.json" <<'EOF'
{
  "raw": "portable.test@siae.it",
  "source": "auth_sso",
  "identity": {
    "auth_email": "portable.test@siae.it",
    "auth_account_uuid": "portable-uuid-1234"
  }
}
EOF
echo '{"total":77,"by_tool":{}}' > "$SESSION_DIR/token-stats.json"

# Log file nella dir di sessione (prima del source)
export DEVFORGE_LOG_FILE="$SESSION_DIR/activity.jsonl"
touch "$DEVFORGE_LOG_FILE"

# Source il logger DOPO aver settato HOME → le righe 6-8 usano il HOME corretto
# shellcheck disable=SC1090
source "$LOGGER" 2>/dev/null || { echo "FATAL: cannot source $LOGGER"; exit 2; }

# Ora DEVFORGE_SESSION_USER_FILE punta a $WORK/.claude/.devforge-session-user
# e DEVFORGE_SESSION_DIR è "" (non ancora init). Pre-set SESSION_DIR per i test
# che non chiamano init_session:
DEVFORGE_SESSION_DIR="$SESSION_DIR"

# --- shim directory per mascherare python3 ---
SHIM_DIR="$WORK/shims"
mkdir -p "$SHIM_DIR"

make_shim() {
    local name="$1"
    printf '#!/usr/bin/env bash\nexit 127\n' > "$SHIM_DIR/$name"
    chmod +x "$SHIM_DIR/$name"
}

clear_shims() {
    rm -f "$SHIM_DIR"/*
}

OLD_PATH="$PATH"

# ---------------------------------------------------------------
echo "TEST 1 — python3 mascherato, node presente: devforge_resolve_auth_identity non vuoto"
clear_shims
make_shim python3
export PATH="$SHIM_DIR:$OLD_PATH"

result=$(devforge_resolve_auth_identity 2>/dev/null)
ae="${result%%|*}"; rest="${result#*|}"
au="${rest%%|*}"

assert_nonempty "T1a: auth_email non vuoto (node fallback)" "$ae"
assert_nonempty "T1b: auth_account_uuid non vuoto (node fallback)" "$au"
assert "T1c: auth_email corretto" "$ae" "portable.test@siae.it"
assert "T1d: auth_account_uuid corretto" "$au" "portable-uuid-1234"

export PATH="$OLD_PATH"
clear_shims

# ---------------------------------------------------------------
echo "TEST 2 — python3 mascherato: devforge_init_session valorizza le 3 variabili di pinning"
# Reset pinning vars prima di init (simula shell fresca)
DEVFORGE_PINNED_USER=""
DEVFORGE_AUTH_EMAIL=""
DEVFORGE_AUTH_ACCOUNT_UUID=""
DEVFORGE_PINNED_SID=""
# Reseed SID file (init_session lo rilege)
echo "testsid" > "$WORK/.claude/.devforge-session-id"

clear_shims
make_shim python3
export PATH="$SHIM_DIR:$OLD_PATH"

devforge_init_session 2>/dev/null

assert_nonempty "T2a: DEVFORGE_PINNED_USER valorizzato" "$DEVFORGE_PINNED_USER"
assert_nonempty "T2b: DEVFORGE_AUTH_EMAIL valorizzato" "$DEVFORGE_AUTH_EMAIL"
assert_nonempty "T2c: DEVFORGE_AUTH_ACCOUNT_UUID valorizzato" "$DEVFORGE_AUTH_ACCOUNT_UUID"
assert "T2d: DEVFORGE_AUTH_EMAIL corretto" "$DEVFORGE_AUTH_EMAIL" "portable.test@siae.it"
assert "T2e: DEVFORGE_AUTH_ACCOUNT_UUID corretto" "$DEVFORGE_AUTH_ACCOUNT_UUID" "portable-uuid-1234"

export PATH="$OLD_PATH"
clear_shims

# ---------------------------------------------------------------
echo "TEST 3 — python3 mascherato: devforge_get_user_raw legge user.json via node"
# Assicura che DEVFORGE_SESSION_DIR punti alla dir con user.json
DEVFORGE_SESSION_DIR="$SESSION_DIR"
clear_shims
make_shim python3
export PATH="$SHIM_DIR:$OLD_PATH"

raw=$(devforge_get_user_raw 2>/dev/null)
assert_nonempty "T3a: raw non vuoto" "$raw"
assert "T3b: raw corretto" "$raw" "portable.test@siae.it"

export PATH="$OLD_PATH"
clear_shims

# ---------------------------------------------------------------
echo "TEST 4 — python3 mascherato: devforge_get_user_source legge user.json via node"
DEVFORGE_SESSION_DIR="$SESSION_DIR"
clear_shims
make_shim python3
export PATH="$SHIM_DIR:$OLD_PATH"

src=$(devforge_get_user_source 2>/dev/null)
assert_nonempty "T4a: source non vuoto" "$src"
assert "T4b: source corretto" "$src" "auth_sso"

export PATH="$OLD_PATH"
clear_shims

# ---------------------------------------------------------------
echo "TEST 5 — python3 mascherato: devforge_session_token_total ritorna intero via devforge_json_field"
DEVFORGE_SESSION_DIR="$SESSION_DIR"
clear_shims
make_shim python3
export PATH="$SHIM_DIR:$OLD_PATH"

total=$(devforge_session_token_total 2>/dev/null)
assert "T5: token total via node" "$total" "77"

export PATH="$OLD_PATH"
clear_shims

# ---------------------------------------------------------------
echo "TEST 6 — no-regression: python3 disponibile, valori identici al baseline"
# Reset pinning per re-init pulita
DEVFORGE_PINNED_USER=""
DEVFORGE_AUTH_EMAIL=""
DEVFORGE_AUTH_ACCOUNT_UUID=""
DEVFORGE_PINNED_SID=""
DEVFORGE_SESSION_DIR="$SESSION_DIR"
echo "testsid" > "$WORK/.claude/.devforge-session-id"

result=$(devforge_resolve_auth_identity 2>/dev/null)
ae="${result%%|*}"; rest="${result#*|}"
au="${rest%%|*}"; rest="${rest#*|}"
ou="${rest%%|*}"; onm="${rest#*|}"
assert "T6a: auth_email no-regression" "$ae" "portable.test@siae.it"
assert "T6b: auth_account_uuid no-regression" "$au" "portable-uuid-1234"
assert "T6c: auth_org_uuid no-regression" "$ou" "portable-org-uuid-5678"
assert "T6d: auth_org_name no-regression" "$onm" "SIAE Portable"

devforge_init_session 2>/dev/null
assert "T6e: DEVFORGE_AUTH_EMAIL no-regression" "$DEVFORGE_AUTH_EMAIL" "portable.test@siae.it"
assert "T6f: DEVFORGE_AUTH_ACCOUNT_UUID no-regression" "$DEVFORGE_AUTH_ACCOUNT_UUID" "portable-uuid-1234"
assert "T6g: DEVFORGE_PINNED_USER no-regression" "$DEVFORGE_PINNED_USER" "portable.test@siae.it"

DEVFORGE_SESSION_DIR="$SESSION_DIR"
raw=$(devforge_get_user_raw 2>/dev/null)
assert "T6h: user_raw no-regression" "$raw" "portable.test@siae.it"

src=$(devforge_get_user_source 2>/dev/null)
assert "T6i: user_source no-regression" "$src" "auth_sso"

total=$(devforge_session_token_total 2>/dev/null)
assert "T6j: token_total no-regression" "$total" "77"

# ---------------------------------------------------------------
echo ""
echo "SUMMARY: $pass passed, $fail failed"
exit $fail
