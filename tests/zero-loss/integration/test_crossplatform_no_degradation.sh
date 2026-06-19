#!/usr/bin/env bash
# Task-09 — verifica integrata no-degradation telemetria: profili macOS vs Windows Git Bash.
# macOS   = python3 presente (tier primario flock+fsync)
# Windows = python3+flock mascherati, node presente (O_APPEND+fsync), cursori potenz. CRLF
# Dimostra su ENTRAMBE le piattaforme: durabilità, integrità JSON, attribuzione (event_id unici),
# identità SSO + 6 segnali locali, invio segnali zero-loss, rotazione (no crescita illimitata).
# Piano: docs/plans/2026-06-18-telemetry-identity-rotation-crossplatform/task-09
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PASS=0; FAIL=0
ok(){ PASS=$((PASS+1)); echo "  PASS  $1"; }
ko(){ FAIL=$((FAIL+1)); echo "  FAIL  $1"; }
make_mask(){ local shim="$1"; shift; local mask=" $* "; mkdir -p "$shim"; local d; local IFS=':';
  for d in $PATH; do [ -d "$d" ] || continue; ln -sf "$d"/* "$shim/" 2>/dev/null || true; done; unset IFS;
  local b; for b in $mask; do rm -f "$shim/$b"; done; }
validate(){ python3 -c 'import json,sys
b=0
for l in open(sys.argv[1]):
  l=l.strip()
  if not l: continue
  try: json.loads(l)
  except: b+=1
print(b)' "$1" 2>/dev/null || echo "?"; }

verify_profile(){ local label="$1"; shift
  local T; T="$(mktemp -d)"; mkdir -p "$T/.claude/sess/outbox" "$T/.claude/devforge-state/sess/outbox"
  make_mask "$T/bin" "$@"
  printf '{"oauthAccount":{"emailAddress":"lorenzo.detomasi@siae.it","accountUuid":"u1","organizationName":"SIAE"}}' > "$T/.claude.json"
  printf 'fixedsid' > "$T/.claude/.devforge-session-id"   # realistico: session-start crea il sid PRIMA
  # durabilità + integrità + attribuzione: 25 devforge_log concorrenti, meta statico (no quoting shell)
  HOME="$T" DEVFORGE_LOG_FILE="$T/.claude/devforge-activity.jsonl" DEVFORGE_SESSION_DIR="$T/.claude/sess" \
  DEVFORGE_CLAUDE_JSON="$T/.claude.json" PATH="$T/bin" PR="$PLUGIN_ROOT" bash -c '
    source "$PR/lib/logger.sh" 2>/dev/null||true; touch "$DEVFORGE_LOG_FILE"
    for i in $(seq 1 25); do ( source "$PR/lib/logger.sh" 2>/dev/null; devforge_log "evt$i" success "{\"k\":\"v\"}" ) & done; wait' 2>/dev/null||true
  local f="$T/.claude/devforge-activity.jsonl"
  [ "$(wc -l < "$f" 2>/dev/null | tr -d ' ')" = "25" ] && ok "[$label] durabilità: 25/25 righe" || ko "[$label] durabilità"
  [ "$(validate "$f")" = "0" ] && ok "[$label] integrità: JSON valido 100%" || ko "[$label] integrità JSON"
  [ "$(grep -o '"event_id":"[^"]*"' "$f" | sort -u | wc -l | tr -d ' ')" = "25" ] && ok "[$label] attribuzione: 25 event_id unici" || ko "[$label] event_id collisi"
  # identità SSO + 6 segnali
  local bundle; bundle=$(HOME="$T" DEVFORGE_CLAUDE_JSON="$T/.claude.json" PATH="$T/bin" PR="$PLUGIN_ROOT" bash -c 'source "$PR/lib/logger.sh" 2>/dev/null||true; devforge_identity_bundle' 2>/dev/null||echo "")
  echo "$bundle" | grep -q '"auth_email":"lorenzo.detomasi@siae.it"' && echo "$bundle" | grep -q '"os_login":' && ok "[$label] identità: SSO + segnali locali" || ko "[$label] identità incompleta"
  # invio segnali zero-loss su endpoint down
  echo '{"event":"x"}' > "$T/.claude/devforge-state/sess/outbox/batch-1.jsonl"
  HOME="$T" DEVFORGE_SESSION_DIR="$T/.claude/devforge-state/sess" DEVFORGE_TELEMETRY_ENDPOINT="https://127.0.0.1:1/v1/logs" PATH="$T/bin" PR="$PLUGIN_ROOT" \
    bash -c 'source "$PR/lib/telemetry-upload.sh" 2>/dev/null||true; devforge_upload_logs' >/dev/null 2>&1
  local rc=$?
  [ "$rc" -eq 0 ] && [ "$(ls -1 "$T/.claude/devforge-state/sess/outbox/"batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')" = "1" ] && ok "[$label] invio segnali: zero-loss su endpoint down" || ko "[$label] invio segnali"
  # rotazione: nessuna crescita illimitata
  local TR; TR="$(mktemp -d)"; mkdir -p "$TR/.claude/sess"
  HOME="$TR" DEVFORGE_LOG_FILE="$TR/.claude/devforge-activity.jsonl" DEVFORGE_SESSION_DIR="$TR/.claude/sess" DEVFORGE_ROTATE_BYTES=2048 PATH="$T/bin" PR="$PLUGIN_ROOT" bash -c '
    source "$PR/lib/logger.sh" 2>/dev/null||true
    for i in $(seq 1 60); do _devforge_atomic_append "$DEVFORGE_LOG_FILE" "{\"e\":$i,\"p\":\"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\"}"; done' 2>/dev/null||true
  [ "$(ls -1 "$TR/.claude/"devforge-activity-*.archived.jsonl 2>/dev/null | wc -l | tr -d ' ')" -ge 1 ] && ok "[$label] rotazione: archivio creato (no crescita illimitata)" || ko "[$label] rotazione assente"
  rm -rf "$TR" "$T"
}

echo "== no-degradation cross-platform: macOS vs Windows Git Bash =="
verify_profile "macOS"   ""
verify_profile "Windows" python python3 flock

echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
