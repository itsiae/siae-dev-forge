#!/usr/bin/env bash
# run-all.sh — Esegue tutti i test di skill triggering
#
# Uso: ./tests/skill-triggering/run-all.sh
#
# Per ogni file in prompts/, invoca run-test.sh con la skill attesa
# (il nome del file .txt corrisponde alla skill target).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="${SCRIPT_DIR}/prompts"

# Check if claude is available before running
if ! command -v claude >/dev/null 2>&1; then
  echo "  SKIP  claude CLI non disponibile — skill triggering tests saltati"
  echo "  INFO  Per eseguire questi test, installa Claude Code: https://docs.anthropic.com/en/docs/build-with-claude/claude-code"
  exit 0
fi

PASS=0
FAIL=0
SKIP=0

# Map prompt file name to expected skill name
# Compatible with bash 3.x (no associative arrays)
get_expected_skill() {
  case "$1" in
    brainstorming)  echo "siae-brainstorming" ;;
    tdd)            echo "siae-tdd" ;;
    debugging)      echo "siae-debugging" ;;
    code-review)    echo "siae-code-standards" ;;
    verification)   echo "siae-verification" ;;
    git-workflow)   echo "siae-git-workflow" ;;
    documentation)  echo "siae-documentation" ;;
    *)              echo "" ;;
  esac
}

echo "Skill Triggering Tests"
echo "======================"
echo ""

for prompt_file in "${PROMPTS_DIR}"/*.txt; do
  prompt_name=$(basename "$prompt_file" .txt)
  expected=$(get_expected_skill "$prompt_name")

  if "${SCRIPT_DIR}/run-test.sh" "$prompt_file" "$expected"; then
    PASS=$((PASS + 1))
  else
    exit_code=$?
    if [ "$exit_code" -eq 2 ]; then
      SKIP=$((SKIP + 1))
    else
      FAIL=$((FAIL + 1))
    fi
  fi
done

echo ""
echo "Risultato: PASS=${PASS} FAIL=${FAIL} SKIP=${SKIP}"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi

exit 0
