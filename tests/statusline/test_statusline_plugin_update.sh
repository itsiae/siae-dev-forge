#!/usr/bin/env bash
# Test: statusline mostra avviso aggiornamento quando esiste flag .plugin-updated (Feature 2b)
# Piano docs/plans/2026-06-18-statusline-python-and-update-notice/ task-03
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATUSLINE="$(cd "$SCRIPT_DIR/../../statusline" && pwd)/devforge-statusline.sh"
PASS=0; FAIL=0

# Crea un HOME sandbox con SID file + dir di sessione. La statusline sorgia logger.sh che
# ricalcola DEVFORGE_SID_FILE da HOME e ricostruisce DEVFORGE_SESSION_DIR -> legge il flag li'.
setup_home_with_sid() { # sid flag_content(optional)
  local tmp; tmp="$(mktemp -d)"
  mkdir -p "$tmp/.claude/devforge-state/$1"
  printf '%s' "$1" > "$tmp/.claude/.devforge-session-id"
  [ -n "${2:-}" ] && printf '%s' "$2" > "$tmp/.claude/devforge-state/$1/.plugin-updated"
  printf '%s' "$tmp"
}

# --- Caso 1: flag presente -> messaggio mostrato ---
H1="$(setup_home_with_sid "testsid1" "1.92.0")"
OUT1="$(printf '{}' | HOME="$H1" bash "$STATUSLINE" 2>/dev/null || true)"
if printf '%s' "$OUT1" | grep -q "DevForge aggiornato a v1.92.0"; then
  PASS=$((PASS+1)); echo "  PASS  flag presente -> avviso aggiornamento mostrato"
else
  FAIL=$((FAIL+1)); echo "  FAIL  flag presente -> avviso NON mostrato"; printf 'OUT: %s\n' "$OUT1"
fi
rm -rf "$H1"

# --- Caso 2: nessun flag -> nessun messaggio ---
H2="$(setup_home_with_sid "testsid2" "")"
OUT2="$(printf '{}' | HOME="$H2" bash "$STATUSLINE" 2>/dev/null || true)"
if printf '%s' "$OUT2" | grep -q "DevForge aggiornato"; then
  FAIL=$((FAIL+1)); echo "  FAIL  nessun flag -> avviso mostrato erroneamente"
else
  PASS=$((PASS+1)); echo "  PASS  nessun flag -> nessun avviso"
fi
rm -rf "$H2"

echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
