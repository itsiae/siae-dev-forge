#!/usr/bin/env bash
# Test: devforge_identity_bundle esteso con campi auth_* (Task 02)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${PLUGIN_ROOT}/lib/logger.sh"
FAIL=0

export DEVFORGE_CLAUDE_JSON=$(mktemp)
cat > "$DEVFORGE_CLAUDE_JSON" <<'JSON'
{"oauthAccount":{"emailAddress":"carmen.lasala@siae.it","accountUuid":"abc-123","organizationUuid":"org-9","organizationName":"Information Technology"}}
JSON
BUNDLE=$(devforge_identity_bundle)

# Bundle e' JSON valido
echo "$BUNDLE" | python3 -c "import json,sys; json.load(sys.stdin)" || { echo "FAIL: bundle non e' JSON valido: $BUNDLE"; FAIL=1; }

# Contiene i 4 campi auth con i valori attesi
for kv in '"auth_email":"carmen.lasala@siae.it"' '"auth_account_uuid":"abc-123"' '"auth_org_uuid":"org-9"' '"auth_org_name":"Information Technology"'; do
    echo "$BUNDLE" | grep -qF "$kv" || { echo "FAIL: manca $kv in $BUNDLE"; FAIL=1; }
done

# Campi pre-esistenti ancora presenti (no-regression)
for k in git_local_email git_global_email os_user host; do
    echo "$BUNDLE" | grep -qF "\"$k\":" || { echo "FAIL: regressione, manca $k"; FAIL=1; }
done

# Caso no-oauthAccount: i 4 campi auth presenti ma vuoti
echo '{"x":1}' > "$DEVFORGE_CLAUDE_JSON"
BUNDLE2=$(devforge_identity_bundle)
echo "$BUNDLE2" | grep -qF '"auth_email":""' || { echo "FAIL: auth_email non vuoto su no-oauth: $BUNDLE2"; FAIL=1; }

[ "$FAIL" = "0" ] && echo "PASS test_identity_bundle_auth" || exit 1
