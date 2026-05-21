#!/usr/bin/env bash
# cache-helper.sh — utility per persistence layer .code-coverage/
# Usage: source skills/code-coverage/lib/cache-helper.sh
#
# NB: NON impostiamo `set -euo pipefail` perché il file è destinato al `source`.
# Le opzioni propagherebbero al parent shell alterando il suo error-handling.
# Gestione errori esplicita: ogni funzione usa `return 1` su failure path.

is_cache_valid() {
  local cache="$1"
  local pinnacle="$2"
  if [ ! -f "$cache" ]; then return 1; fi
  if [ ! -f "$pinnacle" ]; then return 0; fi
  local cache_mtime pinnacle_mtime
  cache_mtime=$(stat -f %m "$cache" 2>/dev/null || stat -c %Y "$cache")
  pinnacle_mtime=$(stat -f %m "$pinnacle" 2>/dev/null || stat -c %Y "$pinnacle")
  [ "$cache_mtime" -gt "$pinnacle_mtime" ]
}

ensure_gitignore() {
  local repo="$1"
  local gitignore="$repo/.gitignore"
  if [ ! -f "$gitignore" ]; then
    echo ".code-coverage/" > "$gitignore"
    echo "Created $gitignore with .code-coverage/ entry"
    return 0
  fi
  if grep -qE '^\.code-coverage/?$' "$gitignore"; then
    return 0
  fi
  printf '\n# Added by /code-coverage skill\n.code-coverage/\n' >> "$gitignore"
  echo "Appended .code-coverage/ to $gitignore"
}

init_workdir() {
  local repo="$1"
  mkdir -p "$repo/.code-coverage" || return 1
  ensure_gitignore "$repo"
  local log="$repo/.code-coverage/decisions.log"
  local sentinel="$repo/.code-coverage/last_run_state"

  # C4a fix: archivia decisions.log se il run precedente è "completed".
  # Reset esplicito del sentinel post-archive: Phase 6 deve riscriverlo per
  # certificare un nuovo run completed (evita archive spurio su sentinel stale).
  # Timestamp con PID per evitare collision su run concorrenti nello stesso sec.
  if [ -f "$log" ] && [ -f "$sentinel" ] && grep -q "^completed$" "$sentinel" 2>/dev/null; then
    local archive_ts
    archive_ts=$(date -u +%Y%m%dT%H%M%SZ)_$$
    mv "$log" "${log}.archive.${archive_ts}" 2>/dev/null || true
    rm -f "$sentinel"
  fi

  if [ ! -f "$log" ]; then
    echo "# /code-coverage decisions log — $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$log"
  fi
}

log_decision() {
  local repo="$1"
  local phase="$2"
  local decision="$3"
  local rationale="$4"
  local ts
  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  printf '%s [%s] %s — %s\n' "$ts" "$phase" "$decision" "$rationale" >> "$repo/.code-coverage/decisions.log"
}
