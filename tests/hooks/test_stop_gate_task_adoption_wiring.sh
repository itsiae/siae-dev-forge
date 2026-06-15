#!/usr/bin/env bash
# Test: hooks/stop-gate wira devforge_emit_task_adoption in _devforge_emit_session_end
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="${PLUGIN_ROOT}/hooks/stop-gate"
PASS=0; FAIL=0
ok() { if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

# Strutturale: il wiring è presente dentro la funzione, con guard best-effort.
ok "source adoption-emit.sh presente" "grep -q 'adoption-emit.sh' '$HOOK'"
ok "chiamata devforge_emit_task_adoption presente" "grep -q 'devforge_emit_task_adoption' '$HOOK'"
ok "chiamata con guard best-effort (|| true)" \
   "grep -E 'devforge_emit_task_adoption[[:space:]]*2>/dev/null[[:space:]]*\|\|[[:space:]]*true' '$HOOK' >/dev/null"

# Smoke: stop-gate con stdin vuoto (path _devforge_emit_session_end) non crasha.
TMPHOME="$(mktemp -d)"
OUT=$(printf '' | HOME="$TMPHOME" bash "$HOOK" 2>/dev/null; echo "exit:$?")
ok "smoke: stdin vuoto exit 0" "echo '$OUT' | grep -q 'exit:0'"

echo ""; echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
