#!/usr/bin/env bash
# Test: pallino 🟡 sul label quando telemetria in fallback (sentinel presente) (Feature C)
# Piano docs/plans/2026-06-18-statusline-activation-viz/ task-04
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATUSLINE="$(cd "$SCRIPT_DIR/../../statusline" && pwd)/devforge-statusline.sh"
PASS=0; FAIL=0

render_home() { printf '{}' | HOME="$1" bash "$STATUSLINE" 2>/dev/null | head -1; }

# --- Caso 1: sentinel presente -> 🟡 ---
H1="$(mktemp -d)"; mkdir -p "$H1/.claude"; touch "$H1/.claude/.devforge-no-fsync-warned"
OUT1="$(render_home "$H1")"
if printf '%s' "$OUT1" | grep -q "🟡"; then PASS=$((PASS+1)); echo "  PASS  sentinel -> 🟡"; else FAIL=$((FAIL+1)); echo "  FAIL  sentinel senza 🟡 (out: $OUT1)"; fi
rm -rf "$H1"

# --- Caso 2: sentinel assente -> no 🟡 ---
H2="$(mktemp -d)"; mkdir -p "$H2/.claude"
OUT2="$(render_home "$H2")"
if printf '%s' "$OUT2" | grep -q "🟡"; then FAIL=$((FAIL+1)); echo "  FAIL  nessun sentinel ma 🟡 mostrato"; else PASS=$((PASS+1)); echo "  PASS  nessun sentinel -> no 🟡"; fi
rm -rf "$H2"

echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
