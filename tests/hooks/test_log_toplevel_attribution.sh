#!/usr/bin/env bash
# Test: auth_email/auth_account_uuid/repo_remote top-level in ogni evento (Task 05)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FAIL=0
export DEVFORGE_FORCE_BASH_FALLBACK=1

assert_json_field() { # file, field → stampa valore dell'ultima riga
    python3 -c "import json,sys; print(json.loads(open(sys.argv[1]).read().strip().splitlines()[-1]).get(sys.argv[2],'MISSING'))" "$1" "$2"
}

# Repo con origin + env auth pinnate
TMP_REPO=$(mktemp -d); cd "$TMP_REPO"; git init -q
git config user.email "t@t.local"; git config user.name "T"
git remote add origin "https://github.com/itsiae/sport-demo.git"
echo x > f; git add f; git commit -q -m c
source "${PLUGIN_ROOT}/lib/logger.sh"
export DEVFORGE_LOG_FILE=$(mktemp); export DEVFORGE_SESSION_DIR=$(mktemp -d)
export DEVFORGE_AUTH_EMAIL="carmen.lasala@siae.it"; export DEVFORGE_AUTH_ACCOUNT_UUID="abc-123"

devforge_log "commit_created" "success" "{\"commit_sha\":\"deadbeef\"}"
[ "$(assert_json_field "$DEVFORGE_LOG_FILE" auth_email)" = "carmen.lasala@siae.it" ] || { echo "FAIL: auth_email top-level"; FAIL=1; }
[ "$(assert_json_field "$DEVFORGE_LOG_FILE" auth_account_uuid)" = "abc-123" ] || { echo "FAIL: auth_account_uuid top-level"; FAIL=1; }
[ "$(assert_json_field "$DEVFORGE_LOG_FILE" repo_remote)" = "https://github.com/itsiae/sport-demo.git" ] || { echo "FAIL: repo_remote"; FAIL=1; }
grep -qF '"commit_sha":"deadbeef"' "$DEVFORGE_LOG_FILE" || { echo "FAIL: commit_sha nel meta"; FAIL=1; }

# devforge_log_timed: stessi 3 campi + JSON valido
START=$(_devforge_epoch_ns)
devforge_log_timed "skill_completed" "success" "$START" "{}"
[ "$(assert_json_field "$DEVFORGE_LOG_FILE" repo_remote)" = "https://github.com/itsiae/sport-demo.git" ] || { echo "FAIL: repo_remote timed"; FAIL=1; }
[ "$(assert_json_field "$DEVFORGE_LOG_FILE" auth_email)" = "carmen.lasala@siae.it" ] || { echo "FAIL: auth_email timed"; FAIL=1; }
# duration_ms ancora presente (no-regression timed)
[ "$(assert_json_field "$DEVFORGE_LOG_FILE" duration_ms)" != "MISSING" ] || { echo "FAIL: duration_ms perso in log_timed"; FAIL=1; }
python3 -c "import json; [json.loads(l) for l in open('$DEVFORGE_LOG_FILE') if l.strip()]" || { echo "FAIL: JSONL non valido"; FAIL=1; }

# No-regression: campi identita' esistenti invariati
for k in user user_raw user_source actor_canonical; do
    grep -qF "\"$k\":" "$DEVFORGE_LOG_FILE" || { echo "FAIL: regressione, manca $k"; FAIL=1; }
done

# Repo senza origin → repo_remote vuoto, no crash
TMP_REPO2=$(mktemp -d); cd "$TMP_REPO2"; git init -q
git config user.email "t@t.local"; git config user.name "T"; echo y > g; git add g; git commit -q -m c2
export DEVFORGE_LOG_FILE=$(mktemp)
devforge_log "test_run_result" "success" "{}"
[ "$(assert_json_field "$DEVFORGE_LOG_FILE" repo_remote)" = "" ] || { echo "FAIL: repo_remote non vuoto senza origin"; FAIL=1; }

[ "$FAIL" = "0" ] && echo "PASS test_log_toplevel_attribution" || exit 1
