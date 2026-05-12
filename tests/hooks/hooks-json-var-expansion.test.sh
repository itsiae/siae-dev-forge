#!/usr/bin/env bash
# tests/hooks/hooks-json-var-expansion.test.sh
#
# Verifica che hooks/hooks.json usi double-quote (JSON-escaped \") per
# ${CLAUDE_PLUGIN_ROOT}, consentendo a bash di espandere la variabile
# iniettata da Claude Code nell'env del processo hook.
#
# Bug originale: single-quotes attorno a ${CLAUDE_PLUGIN_ROOT} impediscono
# espansione → SessionStart:startup fail con "bash: ${CLAUDE_PLUGIN_ROOT}/
# hooks/run-hook.cmd: No such file or directory".
#
# Design: docs/plans/2026-05-12-hooks-json-var-expansion-fix-design.md
set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOKS_JSON="${PLUGIN_ROOT}/hooks/hooks.json"

command -v jq >/dev/null || { echo "FAIL: jq non disponibile"; exit 1; }
[ -f "$HOOKS_JSON" ] || { echo "FAIL: $HOOKS_JSON non trovato"; exit 1; }

# Assert 1: zero occorrenze del pattern single-quoted '${CLAUDE_PLUGIN_ROOT}
single_count=$(grep -cF "'\${CLAUDE_PLUGIN_ROOT}" "$HOOKS_JSON" || true)
if [ "$single_count" -ne 0 ]; then
  echo "FAIL[1]: hooks.json contiene $single_count single-quoted \${CLAUDE_PLUGIN_ROOT} (atteso 0)"
  grep -nF "'\${CLAUDE_PLUGIN_ROOT}" "$HOOKS_JSON" || true
  exit 1
fi

# Assert 2: 24 occorrenze del byte-pattern escaped-dquote \"${CLAUDE_PLUGIN_ROOT}
# (22 pre-existing + 2 review-evidence: PreToolUse + PostToolUse, Task 03)
escaped_count=$(grep -cF '\"${CLAUDE_PLUGIN_ROOT}' "$HOOKS_JSON" || true)
if [ "$escaped_count" -ne 24 ]; then
  echo "FAIL[2]: attese 24 occorrenze escaped-dquote \\\"\${CLAUDE_PLUGIN_ROOT}, trovate $escaped_count"
  exit 1
fi

# Assert 3: JSON valido
if ! jq . "$HOOKS_JSON" >/dev/null 2>&1; then
  echo "FAIL[3]: hooks.json non e' JSON valido"
  jq . "$HOOKS_JSON" 2>&1 | head -5 || true
  exit 1
fi

# Assert 4 (runtime): OGNI hook command si espande correttamente con
# CLAUDE_PLUGIN_ROOT controllata; verifichiamo che la sostringa attesa
# /tmp/probe-root/hooks/ appaia in tutti i 22 commands espansi.
total=0; failed=0
while IFS= read -r cmd; do
  [ -z "$cmd" ] && continue
  total=$((total+1))
  expanded=$(CLAUDE_PLUGIN_ROOT=/tmp/probe-root bash -c "echo $cmd" 2>/dev/null || echo "")
  case "$expanded" in
    *"/tmp/probe-root/hooks/"*) ;;
    *)
      echo "FAIL[4.${total}]: command non si espande → cmd=$cmd | expanded=$expanded"
      failed=$((failed+1))
      ;;
  esac
done < <(jq -r '.hooks | to_entries[] | .value[] | .hooks[]? | .command' "$HOOKS_JSON")

if [ "$failed" -ne 0 ]; then
  echo "FAIL[4]: $failed/$total hooks non si espandono correttamente"
  exit 1
fi
if [ "$total" -ne 24 ]; then
  echo "FAIL[4]: attesi 24 commands totali, trovati $total"
  exit 1
fi

echo "PASS: hooks.json var expansion conforme (24 hooks, JSON valid, runtime expansion OK)"
