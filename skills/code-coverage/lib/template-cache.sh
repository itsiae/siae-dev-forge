#!/usr/bin/env bash
# template-cache.sh — hard-cache su filesystem per template di test
# Usage:
#   source skills/code-coverage/lib/template-cache.sh
#   get_template <framework> <repo_path>   # stampa path al template cached
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
