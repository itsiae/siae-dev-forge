#!/usr/bin/env bash
# Test e2e: catena post-commit-review (init_session → devforge_log commit_created) (Task 06)
# Nessun codice nuovo: verifica che commit_created erediti repo_remote/auth_* top-level dal logger.
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
echo "$EV" | SHA="$SHA" python3 -c "
import json,sys,os
e=json.load(sys.stdin)
sha=os.environ['SHA']
assert e['repo_remote']=='https://github.com/itsiae/sport-licenze.git', e.get('repo_remote')
assert e['auth_email']=='carmen.lasala@siae.it', e.get('auth_email')
assert e['auth_account_uuid']=='abc-123', e.get('auth_account_uuid')
meta=e['meta'] if isinstance(e['meta'],dict) else json.loads(e['meta'])
assert meta.get('commit_sha')==sha, meta.get('commit_sha')
" 2>/dev/null || { echo "FAIL: campi attribuzione mancanti/errati. Evento: $EV"; FAIL=1; }

[ "$FAIL" = "0" ] && echo "PASS test_commit_created_attribution_e2e" || exit 1
