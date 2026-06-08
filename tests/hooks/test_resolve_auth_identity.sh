#!/usr/bin/env bash
# Test: devforge_resolve_auth_identity legge ~/.claude.json oauthAccount (Task 01)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${PLUGIN_ROOT}/lib/logger.sh"
FAIL=0

# Caso 1: oauthAccount presente → estrae i 4 campi pipe-delimited
export DEVFORGE_CLAUDE_JSON=$(mktemp)
cat > "$DEVFORGE_CLAUDE_JSON" <<'JSON'
{"oauthAccount":{"emailAddress":"carmen.lasala@siae.it","accountUuid":"abc-123","organizationUuid":"org-9","organizationName":"Information Technology"}}
JSON
OUT=$(devforge_resolve_auth_identity)
[ "$OUT" = "carmen.lasala@siae.it|abc-123|org-9|Information Technology" ] || { echo "FAIL c1: '$OUT'"; FAIL=1; }

# Caso 2: no oauthAccount (Bedrock/API-key) → tutti empty
echo '{"someOther":1}' > "$DEVFORGE_CLAUDE_JSON"
OUT=$(devforge_resolve_auth_identity)
[ "$OUT" = "|||" ] || { echo "FAIL c2: '$OUT'"; FAIL=1; }

# Caso 3: file assente → tutti empty, no crash
export DEVFORGE_CLAUDE_JSON="/nonexistent/path/xyz.json"
OUT=$(devforge_resolve_auth_identity)
[ "$OUT" = "|||" ] || { echo "FAIL c3: '$OUT'"; FAIL=1; }

# Caso 4: pipe nel valore non rompe il delimitatore
export DEVFORGE_CLAUDE_JSON=$(mktemp)
printf '{"oauthAccount":{"emailAddress":"a@b.it","accountUuid":"u","organizationUuid":"o","organizationName":"Pipe|Org"}}' > "$DEVFORGE_CLAUDE_JSON"
OUT=$(devforge_resolve_auth_identity)
[ "$OUT" = "a@b.it|u|o|Pipe Org" ] || { echo "FAIL c4: '$OUT'"; FAIL=1; }

[ "$FAIL" = "0" ] && echo "PASS test_resolve_auth_identity" || exit 1
