#!/usr/bin/env bash
# Test: _devforge_lock_append usa perl (fsync reale) quando python3+node assenti;
# bash+sync (ultima spiaggia) solo se anche perl assente.
# Piano docs/plans/2026-06-18-statusline-activation-viz/ task-01 (goal: no degradazione telemetria)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PASS=0; FAIL=0

# Crea uno shim PATH con TUTTI i binari reali tranne quelli mascherati (no hang: sleep/shasum/awk presenti)
make_mask() { # dir bins-to-mask...
  local shim="$1"; shift; local mask=" $* "; mkdir -p "$shim"
  local d; local IFS=':'
  for d in $PATH; do [ -d "$d" ] || continue; ln -sf "$d"/* "$shim/" 2>/dev/null || true; done
  unset IFS
  local b; for b in $mask; do rm -f "$shim/$b"; done
}

run_append() { # home shim_path
  local home="$1" shim="$2"
  HOME="$home" DEVFORGE_LOG_FILE="$home/.claude/devforge-activity.jsonl" \
  DEVFORGE_SESSION_DIR="$home/.claude/sess" \
  PATH="$shim" bash -c '
    set -euo pipefail
    source "'"$PLUGIN_ROOT"'/lib/logger.sh" 2>/dev/null || true
    _devforge_lock_append "'"$home"'/.claude/target.jsonl" "{\"event\":\"x\"}"$'"'"'\n'"'"'
  ' 2>/dev/null || true
}

# --- Caso 1: perl presente (python3+node mascherati) -> durabile, NO telemetry_degraded ---
T1="$(mktemp -d)"; mkdir -p "$T1/.claude/sess"
make_mask "$T1/bin" python python3 node
run_append "$T1" "$T1/bin"
line_ok=$([ -s "$T1/.claude/target.jsonl" ] && echo 1 || echo 0)
deg=$(grep -c 'telemetry_degraded' "$T1/.claude/devforge-activity.jsonl" 2>/dev/null || true); deg="${deg//[!0-9]/}"; deg="${deg:-0}"
if [ "$line_ok" = "1" ] && [ "$deg" = "0" ] && [ ! -f "$T1/.claude/.devforge-no-fsync-warned" ]; then
  PASS=$((PASS+1)); echo "  PASS  perl tier: riga scritta, telemetry_degraded NON emesso"
else
  FAIL=$((FAIL+1)); echo "  FAIL  perl tier (line_ok=$line_ok deg=$deg sentinel=$([ -f "$T1/.claude/.devforge-no-fsync-warned" ] && echo Y || echo N))"
fi
rm -rf "$T1"

# --- Caso 2: anche perl mascherato -> bash+sync, sync invocato + telemetry_degraded ---
T2="$(mktemp -d)"; mkdir -p "$T2/.claude/sess"
make_mask "$T2/bin" python python3 node perl sync
# Shim sync custom (lascia marker). 'sync' è nel mask sopra → il symlink reale è già rimosso.
cat > "$T2/bin/sync" <<EOF
#!/usr/bin/env bash
touch "$T2/.sync-called"
EOF
chmod +x "$T2/bin/sync"
run_append "$T2" "$T2/bin"
line_ok=$([ -s "$T2/.claude/target.jsonl" ] && echo 1 || echo 0)
deg=$(grep -c 'telemetry_degraded' "$T2/.claude/devforge-activity.jsonl" 2>/dev/null || true); deg="${deg//[!0-9]/}"; deg="${deg:-0}"
if [ "$line_ok" = "1" ] && [ -f "$T2/.sync-called" ] && [ "$deg" -ge 1 ]; then
  PASS=$((PASS+1)); echo "  PASS  ultima spiaggia: bash+sync invocato + telemetry_degraded emesso"
else
  FAIL=$((FAIL+1)); echo "  FAIL  ultima spiaggia (line_ok=$line_ok sync=$([ -f "$T2/.sync-called" ] && echo Y || echo N) deg=$deg)"
fi
rm -rf "$T2"

echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
