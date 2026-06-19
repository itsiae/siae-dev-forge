#!/usr/bin/env bash
# Test: eventi identity_external_domain / identity_unresolved.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FAIL=0
last_event() { python3 -c "import json,sys; print(json.loads(open(sys.argv[1]).read().strip().splitlines()[-1]).get('event','MISSING'))" "$1"; }
field() { python3 -c "import json,sys; e=json.loads(open(sys.argv[1]).read().strip().splitlines()[-1]); m=e.get('meta',{}); m=m if isinstance(m,dict) else json.loads(m); print(m.get(sys.argv[2],'MISSING'))" "$1" "$2"; }

TMP_REPO=$(mktemp -d); cd "$TMP_REPO"; git init -q
git config user.email "t@t.local"; git config user.name "T"; echo x>f; git add f; git commit -q -m c
source "${PLUGIN_ROOT}/lib/logger.sh"
export DEVFORGE_SESSION_DIR=$(mktemp -d)

# --- AC4: dominio esterno → identity_external_domain ---
export DEVFORGE_LOG_FILE=$(mktemp)
export DEVFORGE_AUTH_EMAIL="rossi.danilo83@gmail.com"; export DEVFORGE_AUTH_DOMAIN="siae.it"
devforge_emit_identity_observability
[ "$(last_event "$DEVFORGE_LOG_FILE")" = "identity_external_domain" ] || { echo "FAIL AC4: evento errato"; FAIL=1; }
[ "$(field "$DEVFORGE_LOG_FILE" domain)" = "gmail.com" ] || { echo "FAIL AC4: domain meta errato"; FAIL=1; }

# --- AC4b: dominio interno → nessun evento ---
export DEVFORGE_LOG_FILE=$(mktemp)
export DEVFORGE_AUTH_EMAIL="lorenzo.detomasi@siae.it"
devforge_emit_identity_observability
[ ! -s "$DEVFORGE_LOG_FILE" ] || { echo "FAIL AC4b: emesso evento per dominio interno"; FAIL=1; }

# --- AC5: auth_email vuoto → identity_unresolved ---
export DEVFORGE_LOG_FILE=$(mktemp)
export DEVFORGE_AUTH_EMAIL=""
devforge_emit_identity_observability
[ "$(last_event "$DEVFORGE_LOG_FILE")" = "identity_unresolved" ] || { echo "FAIL AC5: identity_unresolved non emesso"; FAIL=1; }

# --- AC8 (strutturale): l'emit è chiamato SOLO nel branch startup) di session-start ---
# Verifica: STARTUP_LINE < CALL_LINE < primo ';;' dopo startup). Così la chiamata è
# garantita DENTRO il branch startup e non in resume)/clear)/compact)/default.
SS="${PLUGIN_ROOT}/hooks/session-start"
CALL_LINE=$(grep -n "devforge_emit_identity_observability" "$SS" | grep -v ':[[:space:]]*#' | head -1 | cut -d: -f1)
[ -n "$CALL_LINE" ] || { echo "FAIL AC8: chiamata assente in session-start"; FAIL=1; }
if [ -n "$CALL_LINE" ]; then
  # Il branch è 'startup)' come case-label (non il commento "true startup"): àncora a fine riga.
  STARTUP_LINE=$(grep -nE '^\s*startup\)' "$SS" | head -1 | cut -d: -f1)
  [ -n "$STARTUP_LINE" ] || { echo "FAIL AC8: branch startup) non trovato"; FAIL=1; }
  # primo ';;' a partire da STARTUP_LINE (chiude il branch startup)
  CLOSE_LINE=$(awk -v s="${STARTUP_LINE:-0}" 'NR>=s && /;;/ {print NR; exit}' "$SS")
  [ -n "$CLOSE_LINE" ] || { echo "FAIL AC8: chiusura ';;' del branch startup non trovata"; FAIL=1; }
  if [ -n "$STARTUP_LINE" ] && [ -n "$CLOSE_LINE" ]; then
    { [ "$STARTUP_LINE" -lt "$CALL_LINE" ] && [ "$CALL_LINE" -lt "$CLOSE_LINE" ]; } \
      || { echo "FAIL AC8: chiamata fuori dal branch startup (startup=$STARTUP_LINE call=$CALL_LINE close=$CLOSE_LINE)"; FAIL=1; }
  fi
fi

[ "$FAIL" = "0" ] && echo "PASS test_identity_observability" || exit 1
