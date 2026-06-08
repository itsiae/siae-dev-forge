# Task 02 — `devforge_identity_bundle()` esteso con campi auth

**Stato:** [PENDING]
**File:** `lib/logger.sh` (modifica `devforge_identity_bundle`, riga ~259-272)
**Dipende da:** Task 01
**Obiettivo:** aggiungere `auth_email`, `auth_account_uuid`, `auth_org_uuid`, `auth_org_name` al bundle.

## RED — Test (`tests/hooks/test_identity_bundle_auth.sh`)
```bash
#!/usr/bin/env bash
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
```

## GREEN — Implementazione (`lib/logger.sh`)
Sostituire **solo il corpo** di `devforge_identity_bundle()` (preservare il commento header
righe ~253-258 che spiega "repo_root is NOT included"), aggiungendo la risoluzione auth e i 4 campi al printf:
```bash
devforge_identity_bundle() {
    local gle gln gge ggn osu host
    gle=$(git config user.email 2>/dev/null || true)
    gln=$(git config user.name 2>/dev/null || true)
    gge=$(git config --global user.email 2>/dev/null || true)
    ggn=$(git config --global user.name 2>/dev/null || true)
    osu="${USER:-}"
    [ -z "$osu" ] && osu=$(whoami 2>/dev/null || echo "")
    host=$(hostname -s 2>/dev/null || hostname 2>/dev/null || echo "")

    # Authenticated SSO identity (Task 01). pipe-delimited: email|uuid|org_uuid|org_name
    local auth ae au ou onm rest
    auth=$(devforge_resolve_auth_identity)
    ae="${auth%%|*}"; rest="${auth#*|}"
    au="${rest%%|*}"; rest="${rest#*|}"
    ou="${rest%%|*}"; onm="${rest#*|}"

    printf '{"git_local_email":"%s","git_local_name":"%s","git_global_email":"%s","git_global_name":"%s","os_user":"%s","host":"%s","auth_email":"%s","auth_account_uuid":"%s","auth_org_uuid":"%s","auth_org_name":"%s"}' \
        "$(devforge_sanitize_json_str "$gle")" "$(devforge_sanitize_json_str "$gln")" \
        "$(devforge_sanitize_json_str "$gge")" "$(devforge_sanitize_json_str "$ggn")" \
        "$(devforge_sanitize_json_str "$osu")" "$(devforge_sanitize_json_str "$host")" \
        "$(devforge_sanitize_json_str "$ae")" "$(devforge_sanitize_json_str "$au")" \
        "$(devforge_sanitize_json_str "$ou")" "$(devforge_sanitize_json_str "$onm")"
}
```

## Verifica
```bash
bash tests/hooks/test_identity_bundle_auth.sh
```

## Accettazione
- [ ] Bundle JSON valido con 4 campi auth_* valorizzati da fixture.
- [ ] 6 campi pre-esistenti invariati (no-regression).
- [ ] Caso no-oauthAccount → auth_* = "" (presenti ma vuoti).
