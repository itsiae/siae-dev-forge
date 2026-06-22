#!/usr/bin/env bash
# Task-08 — CRLF guard (HIGH-12): cursori con \r (Windows core.autocrlf) non devono rompere i
# confronti aritmetici (abort sotto set -e). Copre devforge_create_batch, _devforge_check_rotation.
# Piano: docs/plans/2026-06-18-telemetry-identity-rotation-crossplatform/task-08
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PASS=0; FAIL=0
ok(){ PASS=$((PASS+1)); echo "  PASS  $1"; }
ko(){ FAIL=$((FAIL+1)); echo "  FAIL  $1"; }

# --- A) devforge_create_batch: cursore di sessione con CRLF → nessun abort, batch corretto ---
T="$(mktemp -d)"; mkdir -p "$T/.claude/sess/outbox"
af="$T/.claude/sess/activity.jsonl"; printf '{"e":1}\n{"e":2}\n{"e":3}\n' > "$af"
printf '0\r\n' > "$T/.claude/sess/outbox/.cursor-activity.jsonl"
sub=$(HOME="$T" DEVFORGE_SESSION_DIR="$T/.claude/sess" PR="$PLUGIN_ROOT" bash -c '
  set -euo pipefail
  source "$PR/lib/logger.sh" 2>/dev/null || true
  source "$PR/lib/telemetry-upload.sh" 2>/dev/null || true
  devforge_create_batch >/dev/null 2>&1 && echo OK' 2>/dev/null || echo "")
[ "$sub" = "OK" ] && ok "create_batch: cursore CRLF → nessun abort" || ko "create_batch: abort con CRLF"
nb=$(cat "$T/.claude/sess/outbox/"batch-*.jsonl 2>/dev/null | grep -c '"e"' || echo 0)
[ "${nb:-0}" -eq 3 ] && ok "create_batch: 3 righe batchate da cursore CRLF=0" || ko "create_batch: righe batchate=$nb (atteso 3)"
rm -rf "$T"

# --- B) _devforge_check_rotation: cursore archivio con CRLF → nessun abort ---
T="$(mktemp -d)"; mkdir -p "$T/.claude/sess/outbox"
lf="$T/.claude/devforge-activity.jsonl"; : > "$lf"
arch="$T/.claude/devforge-activity-1.archived.jsonl"; printf 'xxxx\n' > "$arch"
asize=$(stat -f%z "$arch" 2>/dev/null || stat -c%s "$arch")
printf '%s\r\n' "$asize" > "$T/.claude/sess/outbox/.cursor-devforge-activity-1.archived.jsonl"
sub=$(HOME="$T" DEVFORGE_LOG_FILE="$lf" DEVFORGE_SESSION_DIR="$T/.claude/sess" PR="$PLUGIN_ROOT" bash -c '
  set -euo pipefail
  source "$PR/lib/logger.sh" 2>/dev/null || true
  _devforge_check_rotation >/dev/null 2>&1 && echo OK' 2>/dev/null || echo "")
[ "$sub" = "OK" ] && ok "check_rotation: cursore CRLF → nessun abort" || ko "check_rotation: abort con CRLF"
rm -rf "$T"

# --- C) grep di copertura: nessun read di cursore senza tr -d '\r' nei punti chiave ---
miss=0
# devforge_create_batch + _devforge_maybe_remove_archived in telemetry-upload.sh
while IFS= read -r line; do
  echo "$line" | grep -q "tr -d" || { miss=$((miss+1)); echo "    senza guard: $line"; }
done < <(grep -nE 'cursor=\$\(cat|cur=\$\(cat' "$PLUGIN_ROOT/lib/telemetry-upload.sh" "$PLUGIN_ROOT/lib/logger.sh" 2>/dev/null)
[ "$miss" -eq 0 ] && ok "copertura: tutti i read cursore hanno tr -d '\\r'" || ko "copertura: $miss read cursore senza CRLF guard"

echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
