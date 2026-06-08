# Task 06 — Integration: `commit_created` end-to-end

**Stato:** [PENDING]
**File:** `tests/hooks/test_commit_created_attribution_e2e.sh` (solo test — nessun codice nuovo)
**Dipende da:** Task 04, Task 05
**Obiettivo:** verificare che il percorso reale `post-commit-review` → `devforge_init_session`
→ `devforge_log "commit_created"` produca un evento con `repo_remote`/`auth_email`/`auth_account_uuid`
top-level e `commit_sha` nel meta. Nessuna modifica a `post-commit-review`: eredita i campi da `devforge_log`.

## Motivazione "no code change"
`post-commit-review:47` chiama `devforge_init_session` (che dopo Task 04 esporta `DEVFORGE_AUTH_*`)
e `:77` chiama `devforge_log "commit_created"` (che dopo Task 05 aggiunge i 3 campi top-level).
La catena è già cablata: il test conferma l'integrazione, non aggiunge logica.

## RED → GREEN — Test (`tests/hooks/test_commit_created_attribution_e2e.sh`)
```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FAIL=0
export DEVFORGE_FORCE_BASH_FALLBACK=1
export HOME=$(mktemp -d); mkdir -p "${HOME}/.claude"

# Repo reale con origin
TMP_REPO=$(mktemp -d); cd "$TMP_REPO"; git init -q
git config user.email "t@t.local"; git config user.name "T"
git remote add origin "https://github.com/itsiae/sport-licenze.git"
echo x > f; git add f; git commit -q -m first
SHA=$(git rev-parse HEAD)

# Sessione con user.json.identity.auth_*
source "${PLUGIN_ROOT}/lib/logger.sh"
SID=$(devforge_new_sid); SDIR="${HOME}/.claude/devforge-state/${SID}"; mkdir -p "$SDIR"
cat > "${SDIR}/user.json" <<'JSON'
{"raw":"t@t.local","source":"git-config-local","canonical":"t@t.local","identity":{"auth_email":"carmen.lasala@siae.it","auth_account_uuid":"abc-123"}}
JSON
export DEVFORGE_LOG_FILE=$(mktemp)

# Replica esatta della catena post-commit-review
devforge_init_session
devforge_log "commit_created" "success" "{\"commit_sha\":\"${SHA}\",\"files_changed\":1,\"insertions\":1,\"deletions\":0,\"has_tests\":false}"

EV=$(tail -1 "$DEVFORGE_LOG_FILE")
echo "$EV" | python3 -c "import json,sys; e=json.load(sys.stdin); assert e['repo_remote']=='https://github.com/itsiae/sport-licenze.git', e.get('repo_remote'); assert e['auth_email']=='carmen.lasala@siae.it', e.get('auth_email'); assert e['auth_account_uuid']=='abc-123'; assert json.loads(json.dumps(e['meta'])).get('commit_sha')=='${SHA}' if isinstance(e['meta'],dict) else True" 2>/dev/null \
  || { echo "FAIL: campi attribuzione mancanti/errati. Evento: $EV"; FAIL=1; }
# meta puo' essere stringa o oggetto a seconda del parsing: verifica robusta via grep su commit_sha
grep -qF "\"commit_sha\":\"${SHA}\"" "$DEVFORGE_LOG_FILE" || { echo "FAIL: commit_sha nel meta"; FAIL=1; }

[ "$FAIL" = "0" ] && echo "PASS test_commit_created_attribution_e2e" || exit 1
```

## Verifica
```bash
bash tests/hooks/test_commit_created_attribution_e2e.sh
```

## Accettazione
- [ ] `commit_created` da catena reale porta `repo_remote`+`auth_email`+`auth_account_uuid` top-level.
- [ ] `commit_sha` presente nel meta.
- [ ] Nessuna modifica a `hooks/post-commit-review`.
