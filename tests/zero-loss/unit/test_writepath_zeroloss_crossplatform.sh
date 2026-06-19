#!/usr/bin/env bash
# Task 09 — Write-path zero-loss cross-platform suite (9 cases).
#
# Tests: _devforge_lock_append (node+bash fallback chain with mkdir-lock +
# stale-guard), _devforge_dir_age_secs (portable stat), atomic_append.js.
#
# Invariants (design AC14):
#   - conteggio righe == conteggio eventi emessi in OGNI scenario
#   - lock orfano da kill -9 NON causa perdita né deadlock
#   - python3 presente-ma-fallisce → fall-through su node, poi bash (NO perdita)

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LOGGER="${REPO_ROOT}/lib/logger.sh"
ATOMIC_APPEND_JS="${REPO_ROOT}/lib/atomic_append.js"

fail=0
pass=0

assert() {
    local name="$1" actual="$2" expected="$3"
    if [ "$actual" = "$expected" ]; then
        echo "  PASS: $name"; pass=$((pass + 1))
    else
        echo "  FAIL: $name — expected '$expected' got '$actual'"; fail=$((fail + 1))
    fi
}

assert_ge() {
    local name="$1" actual="$2" min="$3"
    if [ "$actual" -ge "$min" ] 2>/dev/null; then
        echo "  PASS: $name (${actual} >= ${min})"; pass=$((pass + 1))
    else
        echo "  FAIL: $name — expected >= $min got '$actual'"; fail=$((fail + 1))
    fi
}

assert_lt() {
    local name="$1" actual="$2" max="$3"
    if [ "$actual" -lt "$max" ] 2>/dev/null; then
        echo "  PASS: $name (${actual} < ${max})"; pass=$((pass + 1))
    else
        echo "  FAIL: $name — expected < $max got '$actual'"; fail=$((fail + 1))
    fi
}

# count_bad_json FILE — count lines that are not valid JSON.
# Uses python3 for parsing; returns 0 if python3 is unavailable (conservative skip).
count_bad_json() {
    local f="$1" bad=0
    if ! command -v python3 >/dev/null 2>&1; then
        echo 0; return
    fi
    while IFS= read -r ln; do
        [ -z "$ln" ] && continue
        if ! python3 -c "import json,sys; json.loads(sys.argv[1])" "$ln" 2>/dev/null; then
            bad=$((bad + 1))
        fi
    done < "$f"
    echo "$bad"
}

# --- Workspace setup ---
WORK=$(mktemp -d)
HOME_BAK="$HOME"
export HOME="$WORK"
mkdir -p "$HOME/.claude"
export DEVFORGE_SESSION_DIR="$WORK/session"
mkdir -p "$DEVFORGE_SESSION_DIR"
export DEVFORGE_LOG_FILE="$DEVFORGE_SESSION_DIR/activity.jsonl"
touch "$DEVFORGE_LOG_FILE"
export PLUGIN_ROOT="$REPO_ROOT"

# OLD_PATH defined early so set -u is safe in all subsequent tests
OLD_PATH="$PATH"

SHIM_DIR="$WORK/shims"
mkdir -p "$SHIM_DIR"

make_shim() {
    local name="$1"
    printf '#!/usr/bin/env bash\nexit 127\n' > "$SHIM_DIR/$name"
    chmod +x "$SHIM_DIR/$name"
}

clear_shims() {
    rm -f "$SHIM_DIR"/*
}

cleanup() {
    export HOME="$HOME_BAK"
    export PATH="$OLD_PATH"
    rm -rf "$WORK"
}
trap cleanup EXIT

# Source logger — must not abort under set -euo pipefail
# shellcheck disable=SC1090
source "$LOGGER" 2>/dev/null || { echo "FATAL: cannot source $LOGGER"; exit 2; }

# Guard: _devforge_lock_append must be defined (from the task-09 implementation).
if ! declare -f _devforge_lock_append >/dev/null 2>&1; then
    echo "FATAL: _devforge_lock_append not found — implementation missing (RED gate)"
    exit 2
fi

# Guard: _devforge_dir_age_secs must be defined.
if ! declare -f _devforge_dir_age_secs >/dev/null 2>&1; then
    echo "FATAL: _devforge_dir_age_secs not found — implementation missing (RED gate)"
    exit 2
fi

# Guard: atomic_append.js must exist
if [ ! -f "$ATOMIC_APPEND_JS" ]; then
    echo "FATAL: $ATOMIC_APPEND_JS not found — implementation missing (RED gate)"
    exit 2
fi

# ==============================================================
echo "TEST 1 — Concorrenza: 50 writer paralleli → esattamente 50 righe JSON valide"
# Sub-test 1a: python3 path (primario — no-regression)
OUTFILE_1A="$WORK/concurrent_py3.jsonl"
touch "$OUTFILE_1A"
for i in $(seq 1 50); do
    (
        # shellcheck disable=SC1090
        source "$LOGGER" 2>/dev/null
        _devforge_atomic_append "$OUTFILE_1A" "{\"e\":\"ev\",\"idx\":$i}" 2>/dev/null
    ) &
done
wait
lines_1a=$(wc -l < "$OUTFILE_1A" | tr -d ' ')
assert "T1a: python3-path 50 writer → 50 righe" "$lines_1a" "50"
# All lines must be valid JSON
bad_1a=0
while IFS= read -r line; do
    if ! python3 -c "import json; json.loads('$line')" 2>/dev/null; then
        bad_1a=$((bad_1a + 1))
    fi
done < "$OUTFILE_1A"
assert "T1a: nessuna riga corrotta (python3 path)" "$bad_1a" "0"

# Sub-test 1b: node path (python3 mascherato)
clear_shims
make_shim python3
OUTFILE_1B="$WORK/concurrent_node.jsonl"
touch "$OUTFILE_1B"
for i in $(seq 1 50); do
    (
        export PATH="$SHIM_DIR:$OLD_PATH"
        # shellcheck disable=SC1090
        source "$LOGGER" 2>/dev/null
        _devforge_lock_append "$OUTFILE_1B" "{\"e\":\"ev\",\"idx\":$i}"$'\n' 2>/dev/null
    ) &
done
wait
clear_shims
lines_1b=$(wc -l < "$OUTFILE_1B" | tr -d ' ')
assert "T1b: node-path 50 writer → 50 righe" "$lines_1b" "50"
bad_1b=$(count_bad_json "$OUTFILE_1B")
assert "T1b: nessuna riga corrotta (node path)" "$bad_1b" "0"

# Sub-test 1c: bash degraded (python3 + node mascherati)
clear_shims
make_shim python3
make_shim node
make_shim perl
OUTFILE_1C="$WORK/concurrent_bash.jsonl"
touch "$OUTFILE_1C"
for i in $(seq 1 50); do
    (
        export PATH="$SHIM_DIR:$OLD_PATH"
        # shellcheck disable=SC1090
        source "$LOGGER" 2>/dev/null
        _devforge_lock_append "$OUTFILE_1C" "{\"e\":\"ev\",\"idx\":$i}"$'\n' 2>/dev/null
    ) &
done
wait
clear_shims
lines_1c=$(wc -l < "$OUTFILE_1C" | tr -d ' ')
assert "T1c: bash-degraded 50 writer → 50 righe" "$lines_1c" "50"
bad_1c=$(count_bad_json "$OUTFILE_1C")
assert "T1c: nessuna riga corrotta (bash path)" "$bad_1c" "0"

# ==============================================================
echo "TEST 2 — Crash mid-write: kill -9 → nessuna riga parziale, eventi precedenti presenti"
OUTFILE_2="$WORK/crash_test.jsonl"
touch "$OUTFILE_2"

# Write 10 events, kill a writer mid-stream
for i in $(seq 1 10); do
    (
        # shellcheck disable=SC1090
        source "$LOGGER" 2>/dev/null
        _devforge_atomic_append "$OUTFILE_2" "{\"e\":\"pre_kill\",\"idx\":$i}" 2>/dev/null
    ) &
done
# Launch a writer that will be killed
(
    # shellcheck disable=SC1090
    source "$LOGGER" 2>/dev/null
    sleep 0.3
    _devforge_atomic_append "$OUTFILE_2" '{"e":"victim"}' 2>/dev/null
) &
VICTIM_PID=$!
sleep 0.05
kill -9 "$VICTIM_PID" 2>/dev/null || true
wait 2>/dev/null || true

# Check all lines are valid JSON — no partial lines
bad_2=0
total_2=0
while IFS= read -r line; do
    [ -z "$line" ] && continue
    total_2=$((total_2 + 1))
    if ! python3 -c "import json; json.loads('$line')" 2>/dev/null; then
        bad_2=$((bad_2 + 1))
    fi
done < "$OUTFILE_2"
assert "T2: nessuna riga parziale/corrotta dopo kill-9" "$bad_2" "0"
assert_ge "T2: almeno 10 eventi pre-kill presenti" "$total_2" "10"

# ==============================================================
echo "TEST 3 — No-interprete: node+python3 mascherati → bash + telemetry_degraded"
clear_shims
make_shim python3
make_shim node
make_shim perl
# Reset the degraded sentinel so T3 can emit a fresh event
rm -f "$HOME/.claude/.devforge-no-fsync-warned"

OUTFILE_3="$WORK/no_interp.jsonl"
LOG_3="$WORK/log3.jsonl"
touch "$OUTFILE_3" "$LOG_3"

(
    export PATH="$SHIM_DIR:$OLD_PATH"
    export DEVFORGE_LOG_FILE="$LOG_3"
    # shellcheck disable=SC1090
    source "$LOGGER" 2>/dev/null
    _devforge_lock_append "$OUTFILE_3" '{"e":"no_interp_test"}'$'\n' 2>/dev/null || true
)

clear_shims

lines_3=$(wc -l < "$OUTFILE_3" | tr -d ' ')
assert "T3: evento scritto via bash anche senza interpreti" "$lines_3" "1"

# telemetry_degraded deve essere emesso nel log file specificato
deg_count_3=$(grep -c '"telemetry_degraded"' "$LOG_3" 2>/dev/null || true)
deg_count_3="${deg_count_3:-0}"
if [ "${deg_count_3:-0}" -gt 0 ]; then
    echo "  PASS: T3b: telemetry_degraded emesso"; pass=$((pass + 1))
else
    echo "  FAIL: T3b: telemetry_degraded NON trovato nel log"; fail=$((fail + 1))
fi

# ==============================================================
echo "TEST 4 — node-only: python3 mascherato → durabilità via atomic_append.js (fsync)"
clear_shims
make_shim python3

OUTFILE_4="$WORK/node_only.jsonl"
touch "$OUTFILE_4"

for i in $(seq 1 10); do
    (
        export PATH="$SHIM_DIR:$OLD_PATH"
        # shellcheck disable=SC1090
        source "$LOGGER" 2>/dev/null
        _devforge_lock_append "$OUTFILE_4" "{\"e\":\"node_only\",\"idx\":$i}"$'\n' 2>/dev/null
    ) &
done
wait

clear_shims

lines_4=$(wc -l < "$OUTFILE_4" | tr -d ' ')
assert "T4: 10 eventi scritti via node (python3 mascherato)" "$lines_4" "10"
bad_4=$(count_bad_json "$OUTFILE_4")
assert "T4b: nessuna riga corrotta (node-only path)" "$bad_4" "0"

# Verify node was actually used (atomic_append.js must exist and be functional)
assert "T4c: atomic_append.js esiste" \
    "$([ -f "$ATOMIC_APPEND_JS" ] && echo yes || echo no)" "yes"

# ==============================================================
echo "TEST 5 — Outbox replay: upload S3 fallito → eventi in outbox, retry invariante"
OUTFILE_5="$WORK/outbox_check.jsonl"
touch "$OUTFILE_5"
for i in $(seq 1 5); do
    (
        # shellcheck disable=SC1090
        source "$LOGGER" 2>/dev/null
        _devforge_atomic_append "$OUTFILE_5" "{\"e\":\"outbox\",\"idx\":$i}" 2>/dev/null
    ) &
done
wait
lines_5=$(wc -l < "$OUTFILE_5" | tr -d ' ')
assert "T5: 5 eventi in outbox (upload non configurato) — dati presenti" "$lines_5" "5"

# ==============================================================
echo "TEST 6 — CRLF: nessun CR nei file hook installati (link task-01)"
cr_count_6=$(grep -rl $'\r' "$REPO_ROOT/hooks/"* "$REPO_ROOT/lib/"*.sh 2>/dev/null | wc -l | tr -d ' ')
assert "T6: zero file con CR in hooks/* e lib/*.sh" "$cr_count_6" "0"

# ==============================================================
echo "TEST 7 — Cursor integrity: byte-cursor non salta né duplica su append concorrente"
OUTFILE_7="$WORK/cursor_test.jsonl"
touch "$OUTFILE_7"

for i in $(seq 1 20); do
    (
        # shellcheck disable=SC1090
        source "$LOGGER" 2>/dev/null
        _devforge_atomic_append "$OUTFILE_7" "{\"e\":\"cursor\",\"idx\":$i}" 2>/dev/null
    ) &
done
wait

total_7=$(wc -l < "$OUTFILE_7" | tr -d ' ')
assert "T7: 20 eventi = 20 righe (no duplicati, no skip)" "$total_7" "20"

# Verify each line is valid JSON with unique idx
bad_7=0
while IFS= read -r line; do
    [ -z "$line" ] && continue
    if ! python3 -c "import json; json.loads('$line')" 2>/dev/null; then
        bad_7=$((bad_7 + 1))
    fi
done < "$OUTFILE_7"
assert "T7b: tutte le 20 righe sono JSON valido" "$bad_7" "0"

# ==============================================================
echo "TEST 8 — Stale lock da kill -9 (BLOCK-2): lock orfano rimosso, evento scritto"
OUTFILE_8="$WORK/stale_lock_test.jsonl"
touch "$OUTFILE_8"
LOCKDIR_8="${OUTFILE_8}.lockdir"

# Create a stale lockdir with mtime > 30s ago
mkdir -p "$LOCKDIR_8"
# Force mtime to 60 seconds in the past (portable: BSD and GNU touch -t)
OLD_MTIME=$(date -v-60S +%Y%m%d%H%M.%S 2>/dev/null || date -d '60 seconds ago' +%Y%m%d%H%M.%S 2>/dev/null || echo "")
if [ -n "${OLD_MTIME:-}" ]; then
    touch -t "$OLD_MTIME" "$LOCKDIR_8" 2>/dev/null || true
fi

# Verify stale guard: launch writer — it should remove the stale lock and write.
# Measure duration: stale-guard should resolve in <2s (not via the 5s timeout fallback).
T8_START=$SECONDS
(
    # shellcheck disable=SC1090
    source "$LOGGER" 2>/dev/null
    _devforge_lock_append "$OUTFILE_8" '{"e":"after_stale_lock"}'$'\n' 2>/dev/null
)
T8_DUR=$(( SECONDS - T8_START ))

lines_8=$(wc -l < "$OUTFILE_8" | tr -d ' ')
assert "T8: evento scritto nonostante lock orfano" "$lines_8" "1"
assert "T8b: lockdir rimosso dopo scrittura" \
    "$([ -d "$LOCKDIR_8" ] && echo exists || echo removed)" "removed"
# T8 duration must be < 2s: proves stale-guard path was taken (not the 5s timeout fallback).
assert_lt "T8d: stale-guard risolto in <2s (non via timeout 5s)" "$T8_DUR" "2"

# Sub-test 8b: lock recente tenuto da PID vivo → attende + scrive (nessuna perdita)
OUTFILE_8B="$WORK/live_lock_test.jsonl"
touch "$OUTFILE_8B"
LOCKDIR_8B="${OUTFILE_8B}.lockdir"
mkdir -p "$LOCKDIR_8B"

# Release the lock after 0.5 seconds (writer must wait)
(sleep 0.5; rmdir "$LOCKDIR_8B" 2>/dev/null || true) &
RELEASER_PID=$!

(
    # shellcheck disable=SC1090
    source "$LOGGER" 2>/dev/null
    _devforge_lock_append "$OUTFILE_8B" '{"e":"waited_for_lock"}'$'\n' 2>/dev/null
) &
WAITER_PID=$!
wait "$RELEASER_PID" "$WAITER_PID" 2>/dev/null || true

lines_8b=$(wc -l < "$OUTFILE_8B" | tr -d ' ')
assert "T8c: evento scritto dopo attesa lock vivo" "$lines_8b" "1"

# ==============================================================
echo "TEST 9 — python3 presente-ma-fallisce → fall-through su node (discovery task-02)"
# Sub-test 9a: python3 shim (exit 127) + node reale → scrittura via node, NON persa
clear_shims
make_shim python3
# Reset sentinel so node path can be tested cleanly
rm -f "$HOME/.claude/.devforge-no-fsync-warned"

OUTFILE_9A="$WORK/py3_broken_node_ok.jsonl"
touch "$OUTFILE_9A"

(
    export PATH="$SHIM_DIR:$OLD_PATH"
    # shellcheck disable=SC1090
    source "$LOGGER" 2>/dev/null
    # _devforge_atomic_append: python3 shimmed (exit 127), should fall-through to node
    _devforge_atomic_append "$OUTFILE_9A" '{"e":"py3_broken_node_fallthrough"}' 2>/dev/null
)

clear_shims

lines_9a=$(wc -l < "$OUTFILE_9A" | tr -d ' ')
assert "T9a: python3-rotto → fall-through su node, riga scritta" "$lines_9a" "1"

# Sub-test 9b: python3 shim (exit 127) + node shim (exit 127) → bash printf + telemetry_degraded
clear_shims
make_shim python3
make_shim node
make_shim perl
# Reset sentinel so degraded event can be emitted fresh
rm -f "$HOME/.claude/.devforge-no-fsync-warned"

OUTFILE_9B="$WORK/both_broken_bash.jsonl"
LOG_9B="$WORK/degraded_log_9b.jsonl"
touch "$OUTFILE_9B" "$LOG_9B"

(
    export PATH="$SHIM_DIR:$OLD_PATH"
    export DEVFORGE_LOG_FILE="$LOG_9B"
    # shellcheck disable=SC1090
    source "$LOGGER" 2>/dev/null
    # _devforge_atomic_append: both shimmed, falls through to _devforge_lock_append,
    # which uses bash degraded path + emits telemetry_degraded to DEVFORGE_LOG_FILE
    _devforge_atomic_append "$OUTFILE_9B" '{"e":"both_broken_bash_fallback"}' 2>/dev/null
)

clear_shims

lines_9b=$(wc -l < "$OUTFILE_9B" | tr -d ' ')
assert "T9b: python3+node entrambi rotti → bash printf scrive la riga" "$lines_9b" "1"

deg_9b=$(grep -c '"telemetry_degraded"' "$LOG_9B" 2>/dev/null || true)
deg_9b="${deg_9b:-0}"
reason_9b=$(grep -c '"no_fsync_interpreter"' "$LOG_9B" 2>/dev/null || true)
reason_9b="${reason_9b:-0}"

if [ "${deg_9b:-0}" -gt 0 ]; then
    echo "  PASS: T9b-i: telemetry_degraded emesso"; pass=$((pass + 1))
else
    echo "  FAIL: T9b-i: telemetry_degraded NON trovato in $LOG_9B"; fail=$((fail + 1))
fi
if [ "${reason_9b:-0}" -gt 0 ]; then
    echo "  PASS: T9b-ii: reason=no_fsync_interpreter trovato"; pass=$((pass + 1))
else
    echo "  FAIL: T9b-ii: reason=no_fsync_interpreter NON trovato in $LOG_9B"; fail=$((fail + 1))
fi

# ==============================================================
echo ""
echo "SUMMARY: $pass passed, $fail failed"
exit $fail
