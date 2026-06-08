# Task 04 — `devforge_init_session()` legge auth da user.json + esporta env

**Stato:** [PENDING]
**File:** `lib/logger.sh` (riga ~12-14 defaults + `devforge_init_session` riga ~392-401)
**Dipende da:** Task 02 (user.json.identity contiene i campi auth)
**Obiettivo:** gli hook che chiamano `devforge_init_session` (es. post-commit-review) pinnano
l'auth dalla sessione, così gli eventi che emettono portano `auth_email`/`auth_account_uuid` top-level.

## RED — Test (`tests/hooks/test_init_session_auth_pin.sh`)
```bash
#!/usr/bin/env bash
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
[ "${DEVFORGE_AUTH_EMAIL:-UNSET}" = "" ] || { echo "FAIL: auth_email non vuoto su identity senza auth: '${DEVFORGE_AUTH_EMAIL:-UNSET}'"; FAIL=1; }

[ "$FAIL" = "0" ] && echo "PASS test_init_session_auth_pin" || exit 1
```

## GREEN — Implementazione (`lib/logger.sh`)
1. Subito DOPO la riga 14 (`DEVFORGE_PINNED_SID="${DEVFORGE_PINNED_SID:-}"`) e PRIMA del commento
   `# Cross-platform epoch nanoseconds` (riga 16), aggiungere i default per `set -u`:
```bash
DEVFORGE_AUTH_EMAIL="${DEVFORGE_AUTH_EMAIL:-}"
DEVFORGE_AUTH_ACCOUNT_UUID="${DEVFORGE_AUTH_ACCOUNT_UUID:-}"
```
2. In `devforge_init_session()`, dentro il blocco `if [ -f "${DEVFORGE_SESSION_DIR}/user.json" ] && command -v python3 ...`, dopo la risoluzione di `DEVFORGE_PINNED_USER`, aggiungere:
```bash
        DEVFORGE_AUTH_EMAIL=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('identity',{}).get('auth_email','') or '')" "${DEVFORGE_SESSION_DIR}/user.json" 2>/dev/null || echo "")
        DEVFORGE_AUTH_ACCOUNT_UUID=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('identity',{}).get('auth_account_uuid','') or '')" "${DEVFORGE_SESSION_DIR}/user.json" 2>/dev/null || echo "")
```
3. Aggiungere le 2 var alla riga `export`:
```bash
    export DEVFORGE_SESSION_DIR DEVFORGE_PINNED_USER DEVFORGE_PINNED_SID DEVFORGE_AUTH_EMAIL DEVFORGE_AUTH_ACCOUNT_UUID
```

## Verifica
```bash
bash tests/hooks/test_init_session_auth_pin.sh
```

## Accettazione
- [ ] `init_session` esporta `DEVFORGE_AUTH_EMAIL`/`DEVFORGE_AUTH_ACCOUNT_UUID` da `user.json.identity`.
- [ ] identity senza campi auth → env = "" senza crash.
- [ ] `DEVFORGE_PINNED_USER` invariato (no-regression).
