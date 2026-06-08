# Task 03 — session-start esporta `DEVFORGE_AUTH_*`

**Stato:** [PENDING]
**File:** `hooks/session-start` (dopo riga 76, blocco export contesto sessione)
**Dipende da:** Task 01
**Obiettivo:** pinnare l'identità autenticata anche per gli eventi emessi da session-start stesso
(es. l'evento `session_start`). La scrittura di `user.json.identity` è già coperta dal bundle esteso
(Task 02) via la riga esistente `d['identity']=json.loads(IDENTITY_BUNDLE)` — nessuna modifica a quella logica.

## RED — Test (`tests/hooks/test_session_start_auth_export.sh`)
```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FAIL=0

# Verifica che hooks/session-start contenga l'export delle nuove env dopo aver risolto l'auth.
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
```

## GREEN — Implementazione (`hooks/session-start`)
Dopo la riga 76 (`export DEVFORGE_SESSION_DIR DEVFORGE_PINNED_USER="$USER_CANONICAL" DEVFORGE_PINNED_SID="$DEVFORGE_SID"`), aggiungere:
```bash
# Pin authenticated SSO identity for per-event top-level fields (Task 03).
# Best-effort: empty if ~/.claude.json/oauthAccount absent (Bedrock/API-key).
AUTH_RESOLVED=$(devforge_resolve_auth_identity 2>/dev/null || printf '|||')
DEVFORGE_AUTH_EMAIL="${AUTH_RESOLVED%%|*}"
_AUTH_REST="${AUTH_RESOLVED#*|}"
DEVFORGE_AUTH_ACCOUNT_UUID="${_AUTH_REST%%|*}"
export DEVFORGE_AUTH_EMAIL DEVFORGE_AUTH_ACCOUNT_UUID
```

## Verifica
```bash
bash tests/hooks/test_session_start_auth_export.sh
```

## Accettazione
- [ ] session-start chiama `devforge_resolve_auth_identity` ed esporta le 2 env.
- [ ] Snippet di parsing produce email/uuid corretti dalla fixture.
- [ ] Nessuna modifica alla logica di scrittura `user.json` (l'identity bundle esteso la copre).
