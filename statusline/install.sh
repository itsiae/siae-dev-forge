#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# install.sh — Idempotent installer for DevForge status line
# Injects statusLine configuration into ~/.claude/settings.json
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Path STABILE invariante agli auto-update (root-cause fix, design 2026-06-19).
# Il clone marketplace è git-pullato IN-PLACE → path NON versionato, sopravvive a ogni
# update. PLUGIN_ROOT invece può essere la cache versionata (cache/.../X.Y.Z) che
# l'auto-update cancella → settings.json punterebbe a uno script inesistente → statusline
# vuota in silenzio. Preferiamo il clone se il file esiste; fallback a PLUGIN_ROOT solo su
# fresh-install (clone non ancora presente) — si auto-corregge al primo session-start utile.
STABLE_STATUSLINE="${HOME}/.claude/plugins/marketplaces/siae-devforge/statusline/devforge-statusline.sh"
if [ -f "$STABLE_STATUSLINE" ]; then
  STATUSLINE_SCRIPT="$STABLE_STATUSLINE"
else
  STATUSLINE_SCRIPT="${PLUGIN_ROOT}/statusline/devforge-statusline.sh"
fi
SETTINGS_FILE="${HOME}/.claude/settings.json"

# 1. Verify devforge-statusline.sh exists
if [ ! -f "$STATUSLINE_SCRIPT" ]; then
  echo "[DevForge] ERROR: devforge-statusline.sh non trovato in ${STATUSLINE_SCRIPT}" >&2
  exit 1
fi

DESIRED_COMMAND="bash '${STATUSLINE_SCRIPT}'"

# 2. Create settings.json with {} if it does not exist
if [ ! -f "$SETTINGS_FILE" ]; then
  mkdir -p "$(dirname "$SETTINGS_FILE")"
  echo '{}' > "$SETTINGS_FILE"
fi

# 3. Check current statusLine configuration
if command -v jq >/dev/null 2>&1; then
  # --- jq path ---
  CURRENT_COMMAND=$(jq -r '.statusLine.command // empty' "$SETTINGS_FILE" 2>/dev/null || true)

  if [ -n "$CURRENT_COMMAND" ]; then
    # 4. Already devforge-statusline → update path if changed
    if printf '%s' "$CURRENT_COMMAND" | grep -qF "devforge-statusline"; then
      if [ "$CURRENT_COMMAND" = "$DESIRED_COMMAND" ]; then
        # Already configured with correct path — nothing to do
        exit 0
      fi
      # Path changed (e.g. plugin moved) — update it
      TMP_FILE=$(mktemp "${SETTINGS_FILE}.XXXXXX")
      jq --arg cmd "$DESIRED_COMMAND" '.statusLine.command = $cmd | .statusLine.type = "command"' "$SETTINGS_FILE" > "$TMP_FILE"
      mv "$TMP_FILE" "$SETTINGS_FILE"
      echo "✅ DevForge status line: path aggiornato" >&2
      exit 0
    fi

    # 5. Different statusLine configured — do NOT overwrite
    echo "[DevForge] NOTA: statusLine già configurata con un comando custom. Non sovrascrivo." >&2
    echo "[DevForge] Comando attuale: ${CURRENT_COMMAND}" >&2
    echo "[DevForge] Per usare DevForge statusline, aggiungi manualmente a ${SETTINGS_FILE}:" >&2
    echo "  \"statusLine\": { \"command\": \"${DESIRED_COMMAND}\" }" >&2
    exit 0
  fi

  # 6. statusLine not configured → inject
  TMP_FILE=$(mktemp "${SETTINGS_FILE}.XXXXXX")
  jq --arg cmd "$DESIRED_COMMAND" '.statusLine = { "type": "command", "command": $cmd }' "$SETTINGS_FILE" > "$TMP_FILE"
  mv "$TMP_FILE" "$SETTINGS_FILE"
  echo "✅ DevForge status line installata" >&2
  exit 0

else
  # --- Fallback senza jq ---

  # Check if statusLine is already present
  if grep -qF "devforge-statusline" "$SETTINGS_FILE" 2>/dev/null; then
    # Already configured — skip
    exit 0
  fi

  if grep -qF '"statusLine"' "$SETTINGS_FILE" 2>/dev/null; then
    # Different statusLine present — do NOT overwrite
    echo "[DevForge] NOTA: statusLine già configurata. jq non disponibile per merge sicuro." >&2
    echo "[DevForge] Aggiungi manualmente a ${SETTINGS_FILE}:" >&2
    echo "  \"statusLine\": { \"command\": \"${DESIRED_COMMAND}\" }" >&2
    exit 0
  fi

  # No jq, no existing statusLine — print manual instructions
  echo "[DevForge] jq non disponibile. Per installare la status line, aggiungi a ${SETTINGS_FILE}:" >&2
  echo "  \"statusLine\": { \"command\": \"${DESIRED_COMMAND}\" }" >&2
  echo "[DevForge] Oppure installa jq (brew install jq) e riesegui." >&2
  exit 0
fi
