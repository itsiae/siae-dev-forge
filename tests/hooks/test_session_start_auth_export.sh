#!/usr/bin/env bash
# Test: session-start esporta DEVFORGE_AUTH_* + parsing snippet (Task 03)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FAIL=0

# Verifica strutturale: session-start chiama resolve ed esporta le 2 env.
grep -q 'DEVFORGE_AUTH_EMAIL' "${PLUGIN_ROOT}/hooks/session-start" || { echo "FAIL: session-start non esporta DEVFORGE_AUTH_EMAIL"; FAIL=1; }
grep -q 'DEVFORGE_AUTH_ACCOUNT_UUID' "${PLUGIN_ROOT}/hooks/session-start" || { echo "FAIL: session-start non esporta DEVFORGE_AUTH_ACCOUNT_UUID"; FAIL=1; }
grep -q 'devforge_resolve_auth_identity' "${PLUGIN_ROOT}/hooks/session-start" || { echo "FAIL: session-start non chiama devforge_resolve_auth_identity"; FAIL=1; }

# Verifica funzionale dello snippet di parsing (estratto identico a quello del hook)
source "${PLUGIN_ROOT}/lib/logger.sh"
export DEVFORGE_CLAUDE_JSON=$(mktemp)
cat > "$DEVFORGE_CLAUDE_JSON" <<'JSON'
{"oauthAccount":{"emailAddress":"x@siae.it","accountUuid":"uuid-1","organizationUuid":"o","organizationName":"IT"}}
JSON
AUTH_RESOLVED=$(devforge_resolve_auth_identity 2>/dev/null || printf '|||')
DF_AUTH_EMAIL="${AUTH_RESOLVED%%|*}"
_rest="${AUTH_RESOLVED#*|}"; DF_AUTH_UUID="${_rest%%|*}"
[ "$DF_AUTH_EMAIL" = "x@siae.it" ] || { echo "FAIL: parse email '$DF_AUTH_EMAIL'"; FAIL=1; }
[ "$DF_AUTH_UUID" = "uuid-1" ] || { echo "FAIL: parse uuid '$DF_AUTH_UUID'"; FAIL=1; }

[ "$FAIL" = "0" ] && echo "PASS test_session_start_auth_export" || exit 1
