#!/usr/bin/env bash
# Task-05/06 — rotazione cross-tier cursor-aware (Capability B).
# La rotazione (oggi python3-only in atomic_write.py) deve scattare anche sui tier node/perl/bash
# così su Windows (no python3) il log ruota a soglia e il cap si applica. + cursor-move (no dup/perdita).
# Piano: docs/plans/2026-06-18-telemetry-identity-rotation-crossplatform/task-05,06
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PASS=0; FAIL=0
ok(){ PASS=$((PASS+1)); echo "  PASS  $1"; }
ko(){ FAIL=$((FAIL+1)); echo "  FAIL  $1"; }
make_mask(){ local shim="$1"; shift; local mask=" $* "; mkdir -p "$shim"; local d; local IFS=':';
  for d in $PATH; do [ -d "$d" ] || continue; ln -sf "$d"/* "$shim/" 2>/dev/null || true; done; unset IFS;
  local b; for b in $mask; do rm -f "$shim/$b"; done; }

# ---- A) Helper _devforge_rotate_inline diretto (task-05) ----
T="$(mktemp -d)"; mkdir -p "$T/out"
f="$T/devforge-activity.jsonl"
# file > soglia
for i in $(seq 1 40); do printf '{"e":%d,"pad":"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}\n' "$i"; done > "$f"
printf '100' > "$T/out/.cursor-devforge-activity.jsonl"   # cursore live a 100
PR="$PLUGIN_ROOT" bash -c 'source "$PR/lib/logger.sh" 2>/dev/null||true; _devforge_rotate_inline "'"$f"'" 2048 "'"$T/out"'"' 2>/dev/null
arch=$(ls -1 "$T/"devforge-activity-*.archived.jsonl 2>/dev/null | head -1)
[ -n "$arch" ] && [ ! -f "$f" ] && ok "helper: rotazione → archivio creato, file live rimosso" || ko "helper: nessuna rotazione (arch='$arch')"
# cursor-move: il cursore live deve essere migrato sull'archivio
ab=$(basename "$arch" 2>/dev/null)
[ -f "$T/out/.cursor-${ab}" ] && [ "$(cat "$T/out/.cursor-${ab}" 2>/dev/null)" = "100" ] && [ ! -f "$T/out/.cursor-devforge-activity.jsonl" ] \
  && ok "helper: cursor-move (live→archivio, valore 100 preservato)" || ko "helper: cursor-move fallito"
rm -rf "$T"

# file < soglia → no-op
T="$(mktemp -d)"; f="$T/a.jsonl"; printf '{"x":1}\n' > "$f"
PR="$PLUGIN_ROOT" bash -c 'source "$PR/lib/logger.sh" 2>/dev/null||true; _devforge_rotate_inline "'"$f"'" 999999 ""' 2>/dev/null
[ -f "$f" ] && [ -z "$(ls -1 "$T/"a-*.archived.jsonl 2>/dev/null)" ] && ok "helper: sotto soglia → no-op" || ko "helper: rotazione errata sotto soglia"
rm -rf "$T"

# file inesistente → no-op, nessun abort
T="$(mktemp -d)"
sub=$(PR="$PLUGIN_ROOT" bash -c 'set -euo pipefail; source "$PR/lib/logger.sh" 2>/dev/null||true; _devforge_rotate_inline "'"$T/nope.jsonl"'" 2048 "" && echo OK' 2>/dev/null||echo "")
[ "$sub" = "OK" ] && ok "helper: file inesistente → no-op, nessun abort" || ko "helper: abort su file inesistente"
rm -rf "$T"

# collisione nome → suffisso
T="$(mktemp -d)"; f="$T/a.jsonl"
for i in $(seq 1 40); do printf 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n'; done > "$f"
ts=$(date +%s); touch "$T/a-${ts}.archived.jsonl"   # pre-esiste l'archivio col ts corrente
PR="$PLUGIN_ROOT" bash -c 'source "$PR/lib/logger.sh" 2>/dev/null||true; _devforge_rotate_inline "'"$f"'" 1024 ""' 2>/dev/null
n=$(ls -1 "$T/"a-*.archived.jsonl 2>/dev/null | wc -l | tr -d ' ')
[ "$n" -ge 2 ] && ok "helper: collisione nome → suffisso (-N)" || ko "helper: collisione non gestita (archivi=$n)"
rm -rf "$T"

# ---- B) Cross-tier via _devforge_atomic_append (task-06): rotazione su OGNI tier ----
rotate_profile(){ # label  masked...
  local label="$1"; shift
  local TT; TT="$(mktemp -d)"; mkdir -p "$TT/.claude/sess"
  make_mask "$TT/bin" "$@"
  HOME="$TT" DEVFORGE_LOG_FILE="$TT/.claude/sess/activity.jsonl" DEVFORGE_SESSION_DIR="$TT/.claude/sess" \
  DEVFORGE_ROTATE_BYTES=2048 PATH="$TT/bin" PR="$PLUGIN_ROOT" bash -c '
    source "$PR/lib/logger.sh" 2>/dev/null||true
    for i in $(seq 1 60); do _devforge_atomic_append "$DEVFORGE_LOG_FILE" "{\"e\":$i,\"p\":\"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\"}"; done' 2>/dev/null||true
  local a; a=$(ls -1 "$TT/.claude/sess/"activity-*.archived.jsonl 2>/dev/null | wc -l | tr -d ' ')
  # nessuna riga persa: conta solo le righe DATI (escludi eventuale telemetry_degraded del tier bash-only)
  local total; total=$(cat "$TT/.claude/sess/activity.jsonl" "$TT/.claude/sess/"activity-*.archived.jsonl 2>/dev/null | grep -c '"e":' || echo 0)
  [ "${a:-0}" -ge 1 ] && [ "$total" = "60" ] && ok "rotazione tier [$label]: archivio creato + 60 righe intatte" || ko "rotazione tier [$label]: archivi=$a righe=$total"
  rm -rf "$TT"
}
rotate_profile "python3"   ""
rotate_profile "node-only"  python python3
rotate_profile "perl-only"  python python3 node
rotate_profile "bash-only"  python python3 node perl

echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
