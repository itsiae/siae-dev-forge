#!/usr/bin/env bash
# cache-helper.sh — utility per persistence layer .code-coverage/
# Usage: source skills/code-coverage/lib/cache-helper.sh

set -euo pipefail

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
  mkdir -p "$repo/.code-coverage"
  ensure_gitignore "$repo"
  local log="$repo/.code-coverage/decisions.log"
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
