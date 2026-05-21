#!/usr/bin/env bash
# template-cache.sh — hard-cache su filesystem per template di test
# Usage:
#   source skills/code-coverage/lib/template-cache.sh
#   get_template <framework> <repo_path>   # stampa path al template cached
#   clean_template_placeholders <rendered_file>   # post-render cleanup (C1)
#
# Cache layout: <repo>/.code-coverage/_templates/<framework>.cached
# NOTA: questo file è destinato a essere sourced; non imposta `set -euo pipefail`
# per non alterare l'error-handling dello shell chiamante.

get_template() {
  local framework="${1:-}"
  local repo="${2:-}"
  if [ -z "$framework" ] || [ -z "$repo" ]; then
    echo "ERROR: get_template requires <framework> <repo_path>" >&2
    return 1
  fi

  local cache_dir="$repo/.code-coverage/_templates"
  local cache_file="$cache_dir/${framework}.cached"

  mkdir -p "$cache_dir" || return 1

  if [ -f "$cache_file" ]; then
    echo "$cache_file"
    return 0
  fi

  local skill_root
  skill_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || return 1
  local templates_dir="$skill_root/templates"

  local src=""
  case "$framework" in
    vitest)         src="$templates_dir/vitest.template.ts" ;;
    vitest-lambda)  src="$templates_dir/vitest-lambda-handler.template.ts" ;;
    jest)           src="$templates_dir/jest.template.ts" ;;
    pytest)         src="$templates_dir/pytest.template.py" ;;
    pyspark)        src="$templates_dir/pyspark.template.py" ;;
    junit5)         src="$templates_dir/junit5.template.java" ;;
    mockk)          src="$templates_dir/mockk.template.kt" ;;
    go-test)        src="$templates_dir/go-testing.template.go" ;;
    cargo-test)     src="$templates_dir/cargo-test.template.rs" ;;
    xunit)          src="$templates_dir/xunit.template.cs" ;;
    flutter_test)   src="$templates_dir/flutter_test.template.dart" ;;
    *)
      echo "ERROR: unknown framework '$framework' for template cache" >&2
      return 1
      ;;
  esac

  if [ ! -f "$src" ]; then
    echo "ERROR: template source not found: $src" >&2
    return 1
  fi

  cp "$src" "$cache_file" || return 1
  echo "$cache_file"
}

# C1 fix — Post-render placeholder cleanup
# ====================================================================
# Applica sostituzioni regex per pulire artefatti di sostituzione naïve
# {{Placeholder}} → "" (placeholder vuoti) che lascerebbero sintassi
# invalida tipo `import { foo,  }` o `, {`.
#
# Coverage:
#   - Vitest/Jest/TS: `import { A, } from '...'` → `import { A } from '...'`
#   - Vitest/Jest/TS: `import { , B } from '...'` → `import { B } from '...'`
#   - Vitest/Jest/TS: `import {  } from '...'` → riga rimossa
#   - Java: `import .*;` invariato (placeholder Java sono FQN, no list)
#   - Python: `from x import a, ` → `from x import a`; `from x import ` → riga rimossa
#
# Idempotente: applicarlo 2 volte produce lo stesso output.
# Exit code: 0 sempre. Modifica IN PLACE.
clean_template_placeholders() {
  local file="${1:-}"
  if [ -z "$file" ] || [ ! -f "$file" ]; then
    echo "ERROR: clean_template_placeholders requires existing <file>" >&2
    return 1
  fi

  python3 - "$file" <<'PYEOF'
import re, sys
from pathlib import Path

p = Path(sys.argv[1])
text = p.read_text(encoding="utf-8")

# Step 1: rimuove residual {{...}} placeholder (sostituzione naïve fallita)
# Verranno trattati come simboli "vuoti" dalle regole successive.
text = re.sub(r"\{\{[^}]*\}\}", "", text)

lines_out = []
for line in text.splitlines():
    # Vitest/Jest/TS/JS import { a, b } from 'x'
    m = re.match(r"^(\s*import\s*\{)([^}]*)(\}\s*from\s*['\"][^'\"]+['\"];?\s*)$", line)
    if m:
        prefix, body, suffix = m.groups()
        # split su virgola, strip whitespace, scarta vuoti
        symbols = [s.strip() for s in body.split(",") if s.strip()]
        if not symbols:
            # import {} from '...': riga inutile, rimuovi
            continue
        line = f"{prefix} {', '.join(symbols)} {suffix.lstrip()}"
        lines_out.append(line)
        continue

    # Python: from x import a, b, c
    m = re.match(r"^(\s*from\s+[\w.]+\s+import\s+)(.+)$", line)
    if m:
        prefix, body = m.groups()
        symbols = [s.strip() for s in body.split(",") if s.strip()]
        if not symbols:
            # nessun simbolo importato: scarta riga
            continue
        line = f"{prefix}{', '.join(symbols)}"
        lines_out.append(line)
        continue

    # Java/Kotlin/etc: `import com.foo.Bar;` — se FQN è vuoto, scarta.
    if re.match(r"^\s*import\s*;\s*$", line):
        continue
    # Java: `import   ;` con spazi
    if re.match(r"^\s*import\s+;\s*$", line):
        continue

    lines_out.append(line)

p.write_text("\n".join(lines_out) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
PYEOF
  return 0
}
