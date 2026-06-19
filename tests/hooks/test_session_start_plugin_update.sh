#!/usr/bin/env bash
# Test: _devforge_detect_plugin_update — first-run / no-change / change / dev-mode (Feature 2a)
# Piano docs/plans/2026-06-18-statusline-python-and-update-notice/ task-02
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$(cd "$SCRIPT_DIR/../../hooks" && pwd)/session-start"
PASS=0; FAIL=0

# Estrae la funzione dal hook reale (single source of truth).
# Si ferma al primo `}` in colonna 0 = chiusura funzione (i blocchi interni usano `fi`).
extract_fn() { sed -n '/^_devforge_detect_plugin_update()/,/^}/p' "$HOOK"; }

run_case() { # plugin_root last_seen_init
  local plugin_root="$1" last_seen_init="$2"
  local tmp; tmp="$(mktemp -d)"
  export HOME="$tmp/home"; mkdir -p "$HOME/.claude"
  export PLUGIN_ROOT="$plugin_root"
  export DEVFORGE_SESSION_DIR="$tmp/session"; mkdir -p "$DEVFORGE_SESSION_DIR"
  [ -n "$last_seen_init" ] && printf '%s' "$last_seen_init" > "$HOME/.claude/.devforge-plugin-version"
  # Sorgia da file temp (process substitution <(...) non e' affidabile in tutti i contesti)
  local fn="$tmp/fn.sh"
  extract_fn > "$fn"
  # shellcheck disable=SC1090
  source "$fn"
  if declare -f _devforge_detect_plugin_update >/dev/null 2>&1; then
    _devforge_detect_plugin_update || true
  fi
  printf '%s|%s' \
    "$(cat "$HOME/.claude/.devforge-plugin-version" 2>/dev/null || echo MISSING)" \
    "$(cat "$DEVFORGE_SESSION_DIR/.plugin-updated" 2>/dev/null || echo NOFLAG)"
  rm -rf "$tmp"
}

assert_eq() { # desc expected actual
  if [ "$2" = "$3" ]; then PASS=$((PASS+1)); echo "  PASS  $1";
  else FAIL=$((FAIL+1)); echo "  FAIL  $1 (atteso='$2' ottenuto='$3')"; fi
}

# Caso A — first-run (no last-seen): scrive versione, nessun flag
assert_eq "first-run: last_seen scritto, no flag" "1.91.0|NOFLAG" "$(run_case "/x/siae-devforge/1.91.0" "")"

# Caso B — no-change (last-seen == current): nessun flag
assert_eq "no-change: nessun flag" "1.91.0|NOFLAG" "$(run_case "/x/siae-devforge/1.91.0" "1.91.0")"

# Caso C — change (last-seen != current): flag scritto + last-seen aggiornato
assert_eq "change: flag=1.92.0 + last-seen aggiornato" "1.92.0|1.92.0" "$(run_case "/x/siae-devforge/1.92.0" "1.91.0")"

# Caso D — dev-mode non-semver senza plugin.json: skip silenzioso (nessuna scrittura, no flag)
assert_eq "dev-mode: nessuna scrittura, no flag" "MISSING|NOFLAG" "$(run_case "/x/siae-dev-forge" "")"

echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
