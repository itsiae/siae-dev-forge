# Task 01 — `devforge_resolve_auth_identity()`

**Stato:** [PENDING]
**File:** `lib/logger.sh` (nuova funzione, dopo `devforge_identity_bundle` ~riga 272)
**Obiettivo:** leggere l'identità SSO autenticata da `~/.claude.json` → `oauthAccount`.

## RED — Test (`tests/hooks/test_resolve_auth_identity.sh`)
```bash
#!/usr/bin/env bash
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
```

## GREEN — Implementazione (`lib/logger.sh`)
```bash
# Resolve authenticated SSO identity from Claude Code's local oauth account file.
# Reads ~/.claude.json -> oauthAccount.{emailAddress,accountUuid,organizationUuid,organizationName}.
# Best-effort: file missing / no oauthAccount (Bedrock/API-key) / no python3 -> all empty.
# Output: single line "email|account_uuid|org_uuid|org_name" (pipes/newlines in values
# replaced with spaces to protect the delimiter contract). Override path via
# DEVFORGE_CLAUDE_JSON for testing.
devforge_resolve_auth_identity() {
    local claude_json="${DEVFORGE_CLAUDE_JSON:-${HOME}/.claude.json}"
    if [ ! -f "$claude_json" ] || ! command -v python3 >/dev/null 2>&1; then
        printf '|||'
        return 0
    fi
    python3 - "$claude_json" <<'PY' 2>/dev/null || printf '|||'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    o = d.get('oauthAccount') or {}
    vals = [str(o.get('emailAddress', '') or ''), str(o.get('accountUuid', '') or ''),
            str(o.get('organizationUuid', '') or ''), str(o.get('organizationName', '') or '')]
    vals = [v.replace('|', ' ').replace('\n', ' ').replace('\r', ' ') for v in vals]
    sys.stdout.write('|'.join(vals))
except Exception:
    sys.stdout.write('|||')
PY
}
```

## Verifica
```bash
bash tests/hooks/test_resolve_auth_identity.sh
```
Atteso: `PASS test_resolve_auth_identity`.

## Accettazione
- [ ] 4 casi PASS (presente / no-oauthAccount / file-assente / pipe-injection).
- [ ] Override `DEVFORGE_CLAUDE_JSON` funziona (testabilità).
- [ ] Nessun crash sotto `set -euo pipefail`.
