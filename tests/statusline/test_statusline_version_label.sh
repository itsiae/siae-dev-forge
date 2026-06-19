#!/usr/bin/env bash
# Test: label riga 1 mostra versione (semver) o (dev) (Feature A/B)
# Piano docs/plans/2026-06-18-statusline-activation-viz/ task-02
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_STATUSLINE="$(cd "$SCRIPT_DIR/../../statusline" && pwd)/devforge-statusline.sh"
LIB_DIR="$(cd "$SCRIPT_DIR/../../lib" && pwd)"
PASS=0; FAIL=0

# Copia statusline + lib in <tmp>/<verdir>/ così basename(PLUGIN_ROOT_SL)=<verdir>
stage_at_version() { # verdir
  local tmp; tmp="$(mktemp -d)"
  mkdir -p "$tmp/$1/statusline" "$tmp/$1/lib"
  cp "$REAL_STATUSLINE" "$tmp/$1/statusline/devforge-statusline.sh"
  cp "$LIB_DIR"/*.sh "$tmp/$1/lib/" 2>/dev/null || true
  printf '%s' "$tmp/$1/statusline/devforge-statusline.sh"
}
root_of() { dirname "$(dirname "$(dirname "$1")")"; }

# --- Caso A: semver -> "DevForge v1.91.0" ---
S1="$(stage_at_version "1.91.0")"
OUT1="$(printf '{}' | bash "$S1" 2>/dev/null | head -1 || true)"
if printf '%s' "$OUT1" | grep -q "DevForge v1.91.0"; then
  PASS=$((PASS+1)); echo "  PASS  semver -> DevForge v1.91.0"
else
  FAIL=$((FAIL+1)); echo "  FAIL  semver (out: $OUT1)"
fi
rm -rf "$(root_of "$S1")"

# --- Caso B: non-semver (dev) -> "DevForge (dev)" ---
S2="$(stage_at_version "siae-dev-forge")"
OUT2="$(printf '{}' | bash "$S2" 2>/dev/null | head -1 || true)"
if printf '%s' "$OUT2" | grep -q "DevForge (dev)"; then
  PASS=$((PASS+1)); echo "  PASS  non-semver -> DevForge (dev)"
else
  FAIL=$((FAIL+1)); echo "  FAIL  dev-mode (out: $OUT2)"
fi
if printf '%s' "$OUT2" | grep -qE "DevForge v[0-9]"; then
  FAIL=$((FAIL+1)); echo "  FAIL  dev-mode mostra erroneamente una versione"
else
  PASS=$((PASS+1)); echo "  PASS  dev-mode senza versione"
fi
rm -rf "$(root_of "$S2")"

echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
