#!/usr/bin/env bash
# Test: devforge_init_session pinna auth da user.json.identity (Task 04)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FAIL=0

# HOME isolato per non inquinare lo stato reale
export HOME=$(mktemp -d)
mkdir -p "${HOME}/.claude"
source "${PLUGIN_ROOT}/lib/logger.sh"

# Crea sessione + user.json con identity.auth_*
SID=$(devforge_new_sid)
SDIR="${HOME}/.claude/devforge-state/${SID}"
mkdir -p "$SDIR"
cat > "${SDIR}/user.json" <<'JSON'
{"raw":"x@siae.it","source":"git-config-local","canonical":"x@siae.it","identity":{"auth_email":"carmen.lasala@siae.it","auth_account_uuid":"abc-123"}}
JSON

devforge_init_session
[ "${DEVFORGE_AUTH_EMAIL:-}" = "carmen.lasala@siae.it" ] || { echo "FAIL: DEVFORGE_AUTH_EMAIL='${DEVFORGE_AUTH_EMAIL:-}'"; FAIL=1; }
[ "${DEVFORGE_AUTH_ACCOUNT_UUID:-}" = "abc-123" ] || { echo "FAIL: DEVFORGE_AUTH_ACCOUNT_UUID='${DEVFORGE_AUTH_ACCOUNT_UUID:-}'"; FAIL=1; }

# user.json senza identity.auth_* → env vuote, no crash
cat > "${SDIR}/user.json" <<'JSON'
{"raw":"y@siae.it","source":"os-user","canonical":"y@siae.it","identity":{"os_user":"y"}}
JSON
unset DEVFORGE_AUTH_EMAIL DEVFORGE_AUTH_ACCOUNT_UUID
devforge_init_session
# Intento: non deve trattenere il valore stale 'carmen'; deve essere vuoto (non importa unset vs empty).
[ -z "${DEVFORGE_AUTH_EMAIL:-}" ] || { echo "FAIL: auth_email non vuoto su identity senza auth: '${DEVFORGE_AUTH_EMAIL:-}'"; FAIL=1; }

[ "$FAIL" = "0" ] && echo "PASS test_init_session_auth_pin" || exit 1
