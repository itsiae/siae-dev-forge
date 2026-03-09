#!/usr/bin/env bash
# run-test.sh — Esegue un singolo test di skill triggering
#
# Uso: ./run-test.sh <prompt-file> [expected-skill-name]
#
# Invoca Claude Code con il prompt e verifica che la skill target venga invocata.
# Se expected-skill-name non e' fornito, verifica solo che QUALCHE skill venga invocata.
#
# Exit code: 0 = PASS, 1 = FAIL, 2 = SKIP (claude non disponibile)

set -uo pipefail

PROMPT_FILE="$1"
EXPECTED_SKILL="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PROMPT_NAME=$(basename "$PROMPT_FILE" .txt)

# Carica credenziali Bedrock se disponibili
BEDROCK_ENV="${SCRIPT_DIR}/../.env.bedrock"
if [ -f "$BEDROCK_ENV" ]; then
  # shellcheck source=/dev/null
  source "$BEDROCK_ENV"
fi

# Check if claude CLI is available
if ! command -v claude >/dev/null 2>&1; then
  echo "  SKIP  ${PROMPT_NAME}: claude CLI non disponibile"
  exit 2
fi

# Read prompt content
if [ ! -f "$PROMPT_FILE" ]; then
  echo "  FAIL  ${PROMPT_NAME}: file prompt non trovato: ${PROMPT_FILE}"
  exit 1
fi

PROMPT_CONTENT=$(cat "$PROMPT_FILE")

# Invoke Claude with the prompt and capture output
# Use timeout to prevent hanging (60 seconds max)
# --dangerously-skip-permissions: necessario in modalita' non-interattiva
# (la skill invocation richiede permessi che bloccherebbero il test)
# macOS usa gtimeout (coreutils), Linux usa timeout
TIMEOUT_CMD="timeout"
if ! command -v timeout >/dev/null 2>&1; then
  if command -v gtimeout >/dev/null 2>&1; then
    TIMEOUT_CMD="gtimeout"
  else
    TIMEOUT_CMD=""
  fi
fi

if [ -n "$TIMEOUT_CMD" ]; then
  OUTPUT=$($TIMEOUT_CMD 60 claude -p "$PROMPT_CONTENT" \
    --dangerously-skip-permissions \
    --output-format stream-json \
    --verbose 2>/dev/null || true)
else
  OUTPUT=$(claude -p "$PROMPT_CONTENT" \
    --dangerously-skip-permissions \
    --output-format stream-json \
    --verbose 2>/dev/null || true)
fi

if [ -z "$OUTPUT" ]; then
  echo "  SKIP  ${PROMPT_NAME}: nessun output da claude (timeout o errore)"
  exit 2
fi

# Check if any skill was invoked
if echo "$OUTPUT" | grep -q '"name":"Skill"'; then
  if [ -n "$EXPECTED_SKILL" ]; then
    # Check for specific skill
    if echo "$OUTPUT" | grep -q "\"skill\":\"${EXPECTED_SKILL}\""; then
      echo "  PASS  ${PROMPT_NAME} → ${EXPECTED_SKILL}"
      exit 0
    else
      # Try with plugin prefix
      if echo "$OUTPUT" | grep -q "\"skill\":\"siae-devforge:${EXPECTED_SKILL}\""; then
        echo "  PASS  ${PROMPT_NAME} → siae-devforge:${EXPECTED_SKILL}"
        exit 0
      fi
      echo "  FAIL  ${PROMPT_NAME}: skill invocata ma non ${EXPECTED_SKILL}"
      exit 1
    fi
  else
    echo "  PASS  ${PROMPT_NAME}: skill invocata"
    exit 0
  fi
else
  echo "  FAIL  ${PROMPT_NAME}: nessuna skill invocata"
  exit 1
fi
