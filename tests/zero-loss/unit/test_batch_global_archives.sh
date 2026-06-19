#!/usr/bin/env bash
# Task-07 — devforge_batch_global deve drenare anche gli archivi del file globale (BLOCK-1).
# Dopo la rotazione del globale (task-06), devforge-activity-<ts>.archived.jsonl non deve restare
# stranded: per-basename cursor in .global-outbox, migrazione da .cursor-global, cleanup consumati.
# Piano: docs/plans/2026-06-18-telemetry-identity-rotation-crossplatform/task-07
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PASS=0; FAIL=0
ok(){ PASS=$((PASS+1)); echo "  PASS  $1"; }
ko(){ FAIL=$((FAIL+1)); echo "  FAIL  $1"; }

# --- A) archivio globale drenato ---
T="$(mktemp -d)"; mkdir -p "$T/.claude/devforge-state/.global-outbox"
gf="$T/.claude/devforge-activity.jsonl"
printf '{"e":"live1"}\n{"e":"live2"}\n' > "$gf"
arch="$T/.claude/devforge-activity-1000.archived.jsonl"
printf '{"e":"arch1"}\n{"e":"arch2"}\n{"e":"arch3"}\n' > "$arch"
HOME="$T" DEVFORGE_LOG_FILE="$gf" PR="$PLUGIN_ROOT" bash -c '
  source "$PR/lib/telemetry-upload.sh" 2>/dev/null || true
  command -v _devforge_epoch_ns >/dev/null 2>&1 || _devforge_epoch_ns(){ date +%s%N 2>/dev/null||date +%s; }
  devforge_batch_global' 2>/dev/null || true
ob="$T/.claude/devforge-state/.global-outbox"
# le righe dell'archivio devono finire in un batch
arch_in_batch=$(cat "$ob"/batch-*.jsonl 2>/dev/null | grep -c 'arch' || echo 0)
[ "${arch_in_batch:-0}" -eq 3 ] && ok "globale: 3 righe archivio drenate in batch" || ko "globale: righe archivio drenate=$arch_in_batch (atteso 3)"
live_in_batch=$(cat "$ob"/batch-*.jsonl 2>/dev/null | grep -c 'live' || echo 0)
[ "${live_in_batch:-0}" -eq 2 ] && ok "globale: 2 righe live drenate in batch" || ko "globale: righe live drenate=$live_in_batch (atteso 2)"
# cleanup: archivio consumato (cursor>=size) rimosso
[ ! -f "$arch" ] && ok "globale: archivio consumato rimosso (cleanup)" || ko "globale: archivio consumato NON rimosso"
rm -rf "$T"

# --- B) migrazione da vecchio .cursor-global ---
T="$(mktemp -d)"; mkdir -p "$T/.claude/devforge-state/.global-outbox"
gf="$T/.claude/devforge-activity.jsonl"
printf 'AAAAAAAAAA\nBBBBBBBBBB\n' > "$gf"   # 22 byte
echo "11" > "$T/.claude/devforge-state/.global-outbox/.cursor-global"   # vecchio cursore fisso a 11 (=dopo riga1)
HOME="$T" DEVFORGE_LOG_FILE="$gf" PR="$PLUGIN_ROOT" bash -c '
  source "$PR/lib/telemetry-upload.sh" 2>/dev/null || true
  command -v _devforge_epoch_ns >/dev/null 2>&1 || _devforge_epoch_ns(){ date +%s%N 2>/dev/null||date +%s; }
  devforge_batch_global' 2>/dev/null || true
ob="$T/.claude/devforge-state/.global-outbox"
[ -f "$ob/.cursor-devforge-activity.jsonl" ] && [ ! -f "$ob/.cursor-global" ] && ok "globale: migrazione .cursor-global → .cursor-devforge-activity.jsonl" || ko "globale: migrazione cursore non avvenuta"
# solo riga2 (dopo offset 11) deve essere drenata, NON riga1 (già consumata)
got=$(cat "$ob"/batch-*.jsonl 2>/dev/null)
echo "$got" | grep -q 'BBBB' && ! echo "$got" | grep -q 'AAAA' && ok "globale: offset preservato (no ri-upload backlog)" || ko "globale: offset non preservato (got: $got)"
rm -rf "$T"

# --- C) CRLF nel cursore globale → nessun abort aritmetico ---
T="$(mktemp -d)"; mkdir -p "$T/.claude/devforge-state/.global-outbox"
gf="$T/.claude/devforge-activity.jsonl"; printf '{"e":1}\n{"e":2}\n' > "$gf"
printf '0\r\n' > "$T/.claude/devforge-state/.global-outbox/.cursor-devforge-activity.jsonl"
sub=$(HOME="$T" DEVFORGE_LOG_FILE="$gf" PR="$PLUGIN_ROOT" bash -c '
  set -euo pipefail
  source "$PR/lib/telemetry-upload.sh" 2>/dev/null || true
  command -v _devforge_epoch_ns >/dev/null 2>&1 || _devforge_epoch_ns(){ date +%s; }
  devforge_batch_global >/dev/null 2>&1 && echo OK' 2>/dev/null || echo "")
[ "$sub" = "OK" ] && ok "globale: cursore con CRLF → nessun abort" || ko "globale: abort con CRLF nel cursore"
rm -rf "$T"

echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
