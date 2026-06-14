#!/usr/bin/env bash
# Test: lib/adoption-emit.sh :: devforge_emit_task_adoption
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export PLUGIN_ROOT
LIB="${PLUGIN_ROOT}/lib/adoption-emit.sh"
PASS=0; FAIL=0
check() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1 (atteso '$3', ottenuto '$2')"; FAIL=$((FAIL+1)); fi; }

[ -f "$LIB" ] || { echo "FAIL: $LIB mancante"; exit 1; }

# Stub: cattura la chiamata a devforge_log su file
CAP="$(mktemp)"
devforge_log() { printf '%s|%s|%s\n' "$1" "$2" "$3" >> "$CAP"; }
export -f devforge_log 2>/dev/null || true

# Caso A: task_id presente + meta non vuoto → emette task_adoption
devforge_compute_task_id() { echo "abc123def456"; }
: > "$CAP"
# shellcheck disable=SC1090
. "$LIB"
# stub analyzer via override del comando python3? No: usiamo un wrapper.
adoption_meta_stub() { echo '{"task_id":"abc123def456","core_skills_validated":{}}'; }
# Override interno: la fn deve usare PLUGIN_ROOT/lib/adoption-analyzer.py; per il test
# sovrascriviamo PLUGIN_ROOT con una dir che contiene uno stub eseguibile.
STUBDIR="$(mktemp -d)"; mkdir -p "$STUBDIR/lib"
cat > "$STUBDIR/lib/adoption-analyzer.py" <<'PY'
import sys
if "--task-adoption-meta" in sys.argv:
    tid = sys.argv[sys.argv.index("--task-adoption-meta")+1]
    if tid == "abc123def456":
        print('{"task_id":"abc123def456","core_skills_validated":{}}')
PY
PLUGIN_ROOT="$STUBDIR" devforge_emit_task_adoption
EVT=$(cut -d'|' -f1 < "$CAP" | head -1)
check "Caso A emette task_adoption" "$EVT" "task_adoption"

# Caso B: task_id vuoto (fuori scope) → nessuna emissione
devforge_compute_task_id() { echo ""; }
: > "$CAP"
PLUGIN_ROOT="$STUBDIR" devforge_emit_task_adoption
check "Caso B fuori scope: nessun evento" "$(wc -l < "$CAP" | tr -d ' ')" "0"

# Caso C: meta vuoto (ledger vuoto) → nessuna emissione
devforge_compute_task_id() { echo "emptytask"; }
: > "$CAP"
PLUGIN_ROOT="$STUBDIR" devforge_emit_task_adoption
check "Caso C ledger vuoto: nessun evento" "$(wc -l < "$CAP" | tr -d ' ')" "0"

# Caso D: best-effort — devforge_log assente non fa fallire
unset -f devforge_log
devforge_compute_task_id() { echo "abc123def456"; }
PLUGIN_ROOT="$STUBDIR" devforge_emit_task_adoption; rc=$?
check "Caso D best-effort (devforge_log assente) exit 0" "$rc" "0"

echo ""; echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
