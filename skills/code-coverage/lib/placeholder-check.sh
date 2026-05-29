#!/usr/bin/env bash
# placeholder-check.sh — hard gate per file di test generati
# Usage: bash placeholder-check.sh <file-path>
# Exit 0 se nessun placeholder trovato, exit 1 altrimenti

set -euo pipefail

FILE="${1:?file path required}"

if [ ! -f "$FILE" ]; then
  echo "ERROR: $FILE does not exist" >&2
  exit 1
fi

# Template files (living under a templates/ directory) are source templates — their
# {{PLACEHOLDER}} tokens are intentional and must NOT be treated as leaks.
if echo "$FILE" | grep -qE '(^|/)templates/'; then
  echo "OK: template file — placeholders are intentional in $FILE"
  exit 0
fi

MATCHES=$(grep -nE '\{\{[[:space:]]*[[:alnum:]_.\-]+[[:space:]]*\}\}' "$FILE" || true)

if [ -n "$MATCHES" ]; then
  echo "PLACEHOLDER LEAK in $FILE:" >&2
  echo "$MATCHES" >&2
  echo "Refusing to write file with unresolved placeholders." >&2
  exit 1
fi

echo "OK: no placeholder in $FILE"
exit 0
