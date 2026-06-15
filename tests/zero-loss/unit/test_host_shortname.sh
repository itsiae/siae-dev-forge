#!/usr/bin/env bash
# Unit tests: task-05 — F3: normalizzazione host short-name nel bundle identità.
#
# Verifica che devforge_identity_bundle produca il campo `host` come short-name,
# anche quando `hostname` ritorna un FQDN (es. engsport08.itsiae.it).
#
# Shim strategy: si aggiunge in testa al PATH una directory con uno script
# `hostname` che ritorna il FQDN fittizio, oscurando il binario reale.
#
# Nota: NON aggiungere trap EXIT dentro funzioni invocate via $(...) — distrugge
# il trap del chiamante nel subshell.

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

export HOME="$WORK"
mkdir -p "$WORK/.claude"

echo "testsid" > "$WORK/.claude/.devforge-session-id"

SESSION_DIR="$WORK/.claude/devforge-state/testsid"
mkdir -p "$SESSION_DIR"

# .claude.json fittizio minimale (devforge_resolve_auth_identity lo usa)
cat > "$WORK/.claude.json" <<'EOF'
{
  "oauthAccount": {
    "emailAddress": "host.test@siae.it",
    "accountUuid": "host-uuid-0001",
    "organizationUuid": "host-org-uuid-0001",
    "organizationName": "SIAE Host Test"
  }
}
EOF
export DEVFORGE_CLAUDE_JSON="$WORK/.claude.json"

export DEVFORGE_LOG_FILE="$SESSION_DIR/activity.jsonl"
touch "$DEVFORGE_LOG_FILE"

# Source il logger DOPO aver settato HOME
# shellcheck disable=SC1090
source "$LOGGER" 2>/dev/null || { echo "FATAL: cannot source $LOGGER"; exit 2; }

DEVFORGE_SESSION_DIR="$SESSION_DIR"

# --- shim directory ---
SHIM_DIR="$WORK/shims"
mkdir -p "$SHIM_DIR"

OLD_PATH="$PATH"

# ---------------------------------------------------------------
echo "TEST 1 — hostname shim ritorna FQDN: campo host è lo short-name"
# Shim che simula hostname -s fallendo (exit 1) e hostname base che ritorna FQDN
cat > "$SHIM_DIR/hostname" <<'EOF'
#!/usr/bin/env bash
# Simula `hostname -s` failure e `hostname` che ritorna FQDN
if [ "${1:-}" = "-s" ]; then
    exit 1
fi
echo "engsport08.itsiae.it"
EOF
chmod +x "$SHIM_DIR/hostname"
export PATH="$SHIM_DIR:$OLD_PATH"

bundle=$(devforge_identity_bundle 2>/dev/null)
# Estrai il campo host dal JSON: cerca "host":"<valore>"
host_val=$(printf '%s' "$bundle" | grep -o '"host":"[^"]*"' | sed 's/"host":"//;s/"//')

assert "T1a: host è short-name (no dominio)" "$host_val" "engsport08"

export PATH="$OLD_PATH"
rm -f "$SHIM_DIR/hostname"

# ---------------------------------------------------------------
echo "TEST 2 — hostname shim ritorna FQDN con -s: campo host è lo short-name"
# Shim che simula `hostname -s` che ritorna direttamente il FQDN (caso macOS con DNS search)
cat > "$SHIM_DIR/hostname" <<'EOF'
#!/usr/bin/env bash
# Simula hostname -s che ritorna comunque il FQDN (es. macOS con searchdomain aggiunto)
echo "engsport08.itsiae.it"
EOF
chmod +x "$SHIM_DIR/hostname"
export PATH="$SHIM_DIR:$OLD_PATH"

bundle=$(devforge_identity_bundle 2>/dev/null)
host_val=$(printf '%s' "$bundle" | grep -o '"host":"[^"]*"' | sed 's/"host":"//;s/"//')

assert "T2a: host è short-name anche con -s che ritorna FQDN" "$host_val" "engsport08"

export PATH="$OLD_PATH"
rm -f "$SHIM_DIR/hostname"

# ---------------------------------------------------------------
echo "TEST 3 — no-regression: hostname già short resta invariato"
cat > "$SHIM_DIR/hostname" <<'EOF'
#!/usr/bin/env bash
echo "engsport08"
EOF
chmod +x "$SHIM_DIR/hostname"
export PATH="$SHIM_DIR:$OLD_PATH"

bundle=$(devforge_identity_bundle 2>/dev/null)
host_val=$(printf '%s' "$bundle" | grep -o '"host":"[^"]*"' | sed 's/"host":"//;s/"//')

assert "T3a: host short invariato (no-op)" "$host_val" "engsport08"

export PATH="$OLD_PATH"
rm -f "$SHIM_DIR/hostname"

# ---------------------------------------------------------------
echo "TEST 4 — no-regression: altri 9 campi del bundle invariati con shim FQDN"
cat > "$SHIM_DIR/hostname" <<'EOF'
#!/usr/bin/env bash
if [ "${1:-}" = "-s" ]; then exit 1; fi
echo "engsport08.itsiae.it"
EOF
chmod +x "$SHIM_DIR/hostname"
export PATH="$SHIM_DIR:$OLD_PATH"

bundle=$(devforge_identity_bundle 2>/dev/null)

# Verifica che tutti e 10 i campi attesi siano presenti nel JSON
for field in git_local_email git_local_name git_global_email git_global_name os_user host auth_email auth_account_uuid auth_org_uuid auth_org_name; do
    present=$(printf '%s' "$bundle" | grep -c "\"${field}\":" || true)
    if [ "${present:-0}" -ge 1 ]; then
        echo "  PASS: T4: campo $field presente"
        pass=$((pass + 1))
    else
        echo "  FAIL: T4: campo $field MANCANTE nel bundle"
        fail=$((fail + 1))
    fi
done

export PATH="$OLD_PATH"
rm -f "$SHIM_DIR/hostname"

# ---------------------------------------------------------------
echo ""
echo "SUMMARY: $pass passed, $fail failed"
exit $fail
