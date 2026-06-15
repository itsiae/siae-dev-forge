# Task 02 — `lib/adoption-emit.sh` — `devforge_emit_task_adoption`

**Goal:** nuovo file `lib/adoption-emit.sh` con `devforge_emit_task_adoption`: calcola il
`task_id` corrente, invoca `adoption-analyzer.py --task-adoption-meta`, e se l'output è non
vuoto emette l'evento `task_adoption` via `devforge_log`. Best-effort, non-bloccante. Copre AC1, AC7.

**File coinvolti:**
- Crea: `lib/adoption-emit.sh`
- Crea: `tests/hooks/test_adoption_emit.sh`

**Dipendenza:** Task 01 (modalità `--task-adoption-meta`).

## Step 1 — Scrivi il test fallente

Crea `tests/hooks/test_adoption_emit.sh`:

```bash
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
```

## Step 2 — Esegui e verifica che fallisce

Run: `bash tests/hooks/test_adoption_emit.sh`
Output atteso: `FAIL: .../lib/adoption-emit.sh mancante` (exit 1) — il file non esiste ancora.

## Step 3 — Implementa il codice minimo

Crea `lib/adoption-emit.sh`:

```bash
#!/usr/bin/env bash
# adoption-emit.sh — emit dell'evento telemetria task_adoption (Layer 1).
# Design: docs/plans/2026-06-14-devforge-adoption-telemetry-design.md §5.1
# Source-only library: nessun side effect al load. Dipendenze (best-effort):
#   - devforge_log         (lib/logger.sh)
#   - devforge_compute_task_id (lib/task-id.sh)
#   - python3 + lib/adoption-analyzer.py --task-adoption-meta (Task 01)
# Tutte le emissioni sono non-bloccanti: qualunque fallimento => return 0.

devforge_emit_task_adoption() {
    command -v devforge_log >/dev/null 2>&1 || return 0
    command -v devforge_compute_task_id >/dev/null 2>&1 || return 0

    local task_id
    task_id=$(devforge_compute_task_id 2>/dev/null || echo "")
    [ -n "$task_id" ] || return 0          # fuori scope (repo non-itsiae / no git)

    local plugin_root="${PLUGIN_ROOT:-}"
    [ -n "$plugin_root" ] || return 0
    local analyzer="${plugin_root}/lib/adoption-analyzer.py"
    [ -f "$analyzer" ] || return 0

    local meta
    meta=$(python3 "$analyzer" --task-adoption-meta "$task_id" 2>/dev/null || true)
    [ -n "$meta" ] || return 0             # ledger assente/vuoto => niente evento

    devforge_log "task_adoption" "success" "$meta" 2>/dev/null || true
    return 0
}
```

## Step 4 — Esegui e verifica che passa

Run: `bash tests/hooks/test_adoption_emit.sh`
Output atteso: `PASS=4 FAIL=0` (exit 0).

## Step 5 — Commit

```bash
git add lib/adoption-emit.sh tests/hooks/test_adoption_emit.sh
git commit -m "feat(telemetry): adoption-emit.sh devforge_emit_task_adoption (Layer 1 task-02)"
```

## Criteri di accettazione
- [ ] `task_id` non vuoto + meta non vuoto → un `devforge_log "task_adoption" "success" <meta>`.
- [ ] `task_id` vuoto (fuori scope) → nessuna emissione (AC2 lato emit).
- [ ] meta vuoto (ledger vuoto) → nessuna emissione (AC3 lato emit).
- [ ] `devforge_log`/`devforge_compute_task_id`/python3 assenti → return 0, nessun crash (AC7).
- [ ] 4 PASS / 0 FAIL.
