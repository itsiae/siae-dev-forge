#!/usr/bin/env bash
# Task-01 — event_id collision-resistant (Capability D).
# devforge_next_seq deve essere atomico SENZA il binario flock (assente su macOS e Windows Git Bash):
# sotto concorrenza, 50 devforge_log devono produrre 50 event_id unici e 50 session_seq unici.
# Maschera flock+python3 (node resta presente per durabilità) per isolare il path bash del seq.
# Piano: docs/plans/2026-06-18-telemetry-identity-rotation-crossplatform/task-01-*.md
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PASS=0; FAIL=0
N=50

# Shim PATH con tutti i binari reali tranne quelli mascherati.
make_mask() { # shim bins-to-mask...
  local shim="$1"; shift; local mask=" $* "; mkdir -p "$shim"
  local d; local IFS=':'
  for d in $PATH; do [ -d "$d" ] || continue; ln -sf "$d"/* "$shim/" 2>/dev/null || true; done
  unset IFS
  local b; for b in $mask; do rm -f "$shim/$b"; done
}

run_round() { # ritorna "righe uid useq" per un round di N devforge_log concorrenti
  local T; T="$(mktemp -d)"; mkdir -p "$T/.claude/sess"
  make_mask "$T/bin" flock python python3   # node resta → durabilità; flock+python3 fuori → path bash seq
  printf 'fixedsid' > "$T/.claude/.devforge-session-id"   # realistico: session-start crea il sid PRIMA
  HOME="$T" DEVFORGE_LOG_FILE="$T/.claude/sess/activity.jsonl" DEVFORGE_SESSION_DIR="$T/.claude/sess" \
  PATH="$T/bin" N="$N" PR="$PLUGIN_ROOT" bash -c '
    source "$PR/lib/logger.sh" 2>/dev/null || true
    touch "$DEVFORGE_LOG_FILE"
    for i in $(seq 1 "$N"); do ( source "$PR/lib/logger.sh" 2>/dev/null; devforge_log "evt$i" success "{\"k\":\"v\"}" ) & done
    wait
  ' 2>/dev/null || true
  local f="$T/.claude/sess/activity.jsonl"
  local rows uid useq
  rows=$(wc -l < "$f" 2>/dev/null | tr -d ' ')
  uid=$(grep -o '"event_id":"[^"]*"' "$f" 2>/dev/null | sort -u | wc -l | tr -d ' ')
  useq=$(grep -o '"session_seq":[0-9]*' "$f" 2>/dev/null | sort -u | wc -l | tr -d ' ')
  echo "${rows:-0} ${uid:-0} ${useq:-0}"
  rm -rf "$T"
}

# Esegui 3 round: la collisione è intermittente, basta UN round con duplicati per fallire.
all_ok=1
for r in 1 2 3; do
  read -r rows uid useq <<<"$(run_round)"
  echo "  round $r: righe=$rows event_id_unici=$uid session_seq_unici=$useq"
  if [ "$rows" != "$N" ] || [ "$uid" != "$N" ] || [ "$useq" != "$N" ]; then all_ok=0; fi
done

if [ "$all_ok" = "1" ]; then
  PASS=$((PASS+1)); echo "  PASS  event_id + session_seq unici su 3 round da $N concorrenti (no flock)"
else
  FAIL=$((FAIL+1)); echo "  FAIL  collisione rilevata: seq non atomico senza flock"
fi

echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
