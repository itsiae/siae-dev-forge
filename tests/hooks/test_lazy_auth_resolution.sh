#!/usr/bin/env bash
# Test: lazy resolution di auth_email nel logger quando DEVFORGE_AUTH_EMAIL non pinnato.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FAIL=0
assert_json_field() {
    python3 -c "import json,sys; print(json.loads(open(sys.argv[1]).read().strip().splitlines()[-1]).get(sys.argv[2],'MISSING'))" "$1" "$2"
}
make_claude_json() { # email → path file
    local f; f=$(mktemp)
    printf '{"oauthAccount":{"emailAddress":"%s","accountUuid":"uuid-%s"}}' "$1" "$1" > "$f"
    echo "$f"
}

TMP_REPO=$(mktemp -d); cd "$TMP_REPO"; git init -q
git config user.email "t@t.local"; git config user.name "T"
git remote add origin "https://github.com/itsiae/sport-demo.git"
echo x > f; git add f; git commit -q -m c
source "${PLUGIN_ROOT}/lib/logger.sh"

# --- AC1+AC2: nessun pin → auth_email risolto da DEVFORGE_CLAUDE_JSON ---
export DEVFORGE_LOG_FILE=$(mktemp); export DEVFORGE_SESSION_DIR=$(mktemp -d)
unset DEVFORGE_AUTH_EMAIL DEVFORGE_AUTH_ACCOUNT_UUID _DEVFORGE_AUTH_RESOLVED || true
export DEVFORGE_CLAUDE_JSON=$(make_claude_json "lazy.dev@siae.it")
devforge_log "tdd_gate_task_divergence" "info" "{\"task_id\":\"T1\"}"
[ "$(assert_json_field "$DEVFORGE_LOG_FILE" auth_email)" = "lazy.dev@siae.it" ] || { echo "FAIL AC1: auth_email non risolto lazy"; FAIL=1; }
# AC2: anche devforge_log_timed senza pin
unset _DEVFORGE_AUTH_RESOLVED DEVFORGE_AUTH_EMAIL DEVFORGE_AUTH_ACCOUNT_UUID || true
export DEVFORGE_LOG_FILE=$(mktemp)
START=$(_devforge_epoch_ns)
devforge_log_timed "skill_completed" "success" "$START" "{}"
[ "$(assert_json_field "$DEVFORGE_LOG_FILE" auth_email)" = "lazy.dev@siae.it" ] || { echo "FAIL AC2: log_timed lazy"; FAIL=1; }

# --- AC3: pin vince, file NON sovrascrive ---
unset _DEVFORGE_AUTH_RESOLVED || true
export DEVFORGE_LOG_FILE=$(mktemp)
export DEVFORGE_AUTH_EMAIL="pinned@siae.it"
export DEVFORGE_CLAUDE_JSON=$(make_claude_json "other@example.it")
devforge_log "test_run_result" "success" "{}"
[ "$(assert_json_field "$DEVFORGE_LOG_FILE" auth_email)" = "pinned@siae.it" ] || { echo "FAIL AC3: pin non ha precedenza"; FAIL=1; }

# --- AC3b: cache flag isola la rilettura (prova della proprietà "1 lettura/processo") ---
# Flag settato + email vuota (es. resolution già tentata, Bedrock): un secondo log NON
# deve rileggere ~/.claude.json nonostante il file ora contenga un'email. Se il guard del
# flag venisse rimosso, _devforge_ensure_auth rileggerebbe e auth_email diventerebbe non-vuoto
# → il test fallisce. Questo isola il flag, non la precedenza del pin (AC3).
unset DEVFORGE_AUTH_EMAIL DEVFORGE_AUTH_ACCOUNT_UUID || true
export _DEVFORGE_AUTH_RESOLVED=1
export DEVFORGE_CLAUDE_JSON=$(make_claude_json "shouldnotread@siae.it")
export DEVFORGE_LOG_FILE=$(mktemp)
devforge_log "test_run_result" "success" "{}"
[ "$(assert_json_field "$DEVFORGE_LOG_FILE" auth_email)" = "" ] || { echo "FAIL AC3b: cache flag ignorato, file riletto"; FAIL=1; }
unset _DEVFORGE_AUTH_RESOLVED

# --- AC6: no-regression — JSON valido + campi identita' invariati ---
unset _DEVFORGE_AUTH_RESOLVED || true
export DEVFORGE_LOG_FILE=$(mktemp)
export DEVFORGE_AUTH_EMAIL="pinned@siae.it"
devforge_log "test_run_result" "success" "{}"
python3 -c "import json; [json.loads(l) for l in open('$DEVFORGE_LOG_FILE') if l.strip()]" || { echo "FAIL AC6: JSONL invalido"; FAIL=1; }
for k in user user_raw user_source actor_canonical schema_version; do
    grep -qF "\"$k\":" "$DEVFORGE_LOG_FILE" || { echo "FAIL AC6: manca $k"; FAIL=1; }
done

# --- AC7: oauthAccount presente ma resolver degradato (node+python3 non risolvibili) ---
# NOTA: un subshell non eredita le funzioni sourced nel padre. Si lancia un bash -c che
# ri-sourcia logger.sh, ombreggiando SOLO node/python3 con stub che escono 127 (il resto
# del PATH — git/date/coreutils — resta disponibile, così degrada solo la resolution).
AC7_LOG=$(mktemp)
AC7_JSON=$(make_claude_json "degraded@siae.it")
SHADOW=$(mktemp -d)
printf '#!/bin/sh\nexit 127\n' > "$SHADOW/node"; chmod +x "$SHADOW/node"
printf '#!/bin/sh\nexit 127\n' > "$SHADOW/python3"; chmod +x "$SHADOW/python3"
RC=0
PATH="$SHADOW:$PATH" DEVFORGE_LOG_FILE="$AC7_LOG" DEVFORGE_CLAUDE_JSON="$AC7_JSON" \
  DEVFORGE_SESSION_DIR="$DEVFORGE_SESSION_DIR" DEVFORGE_FORCE_BASH_FALLBACK=1 \
  bash -c 'source "'"${PLUGIN_ROOT}"'/lib/logger.sh"; unset DEVFORGE_AUTH_EMAIL _DEVFORGE_AUTH_RESOLVED; devforge_log "test_run_result" "success" "{}"' || RC=$?
[ "$RC" = "0" ] || { echo "FAIL AC7: hook crash con resolver degradato (rc=$RC)"; FAIL=1; }
# auth_email atteso vuoto: la resolution non ha interprete JSON. assert via python3 nel PADRE (PATH normale).
[ "$(assert_json_field "$AC7_LOG" auth_email)" = "" ] || { echo "FAIL AC7: auth_email atteso vuoto in degraded"; FAIL=1; }

[ "$FAIL" = "0" ] && echo "PASS test_lazy_auth_resolution" || exit 1
