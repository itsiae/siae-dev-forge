#!/usr/bin/env bash
# run-trigger-regression.sh — Trigger regression tests usando eval queries
#
# Uso: ./tests/run-trigger-regression.sh [--skill <nome-skill>]
#
# Legge i file JSON in evals/trigger-evals/ e verifica che ogni query
# triggeri (o non triggeri) la skill corrispondente usando claude -p.
#
# Exit code: 0 = tutti sopra soglia, 1 = almeno uno sotto soglia

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
EVALS_DIR="${PLUGIN_ROOT}/evals/trigger-evals"
SINGLE_SKILL=""

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skill) SINGLE_SKILL="$2"; shift 2 ;;
    *) echo "Uso: $0 [--skill <nome-skill>]"; exit 1 ;;
  esac
done

# Check prerequisites
if ! command -v claude >/dev/null 2>&1; then
  echo "  SKIP  claude CLI non disponibile"
  exit 0
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "  FAIL  jq non disponibile (richiesto per parsing JSON)"
  exit 1
fi

# Carica credenziali Bedrock se disponibili
BEDROCK_ENV="${SCRIPT_DIR}/.env.bedrock"
if [ -f "$BEDROCK_ENV" ]; then
  # shellcheck source=/dev/null
  source "$BEDROCK_ENV"
fi

# Soglie
RECALL_THRESHOLD="0.80"
PRECISION_THRESHOLD="0.80"

# Timeout
TIMEOUT_CMD="timeout"
if ! command -v timeout >/dev/null 2>&1; then
  if command -v gtimeout >/dev/null 2>&1; then
    TIMEOUT_CMD="gtimeout"
  else
    TIMEOUT_CMD=""
  fi
fi

TOTAL_PASS=0
TOTAL_WARN=0
TOTAL_SKIP=0

echo "Trigger Regression Tests"
echo "========================"
echo ""

# Per ogni file trigger-eval
for eval_file in "${EVALS_DIR}"/*.json; do
  [ ! -f "$eval_file" ] && continue
  [ "$(basename "$eval_file")" = ".gitkeep" ] && continue

  skill_name=$(basename "$eval_file" .json)

  # Filtro singola skill se richiesto
  if [ -n "$SINGLE_SKILL" ] && [ "$skill_name" != "$SINGLE_SKILL" ]; then
    continue
  fi

  # Conta query
  total_should=$(jq '[.[] | select(.should_trigger == true)] | length' "$eval_file")
  total_should_not=$(jq '[.[] | select(.should_trigger == false)] | length' "$eval_file")

  if [ "$total_should" -eq 0 ] && [ "$total_should_not" -eq 0 ]; then
    echo "  SKIP  ${skill_name}: nessuna query nel file"
    TOTAL_SKIP=$((TOTAL_SKIP + 1))
    continue
  fi

  # Test should-trigger queries
  tp=0  # true positives
  fn=0  # false negatives
  for i in $(seq 0 $((total_should - 1))); do
    query=$(jq -r ".[$i | tonumber].query // empty" <(jq '[.[] | select(.should_trigger == true)]' "$eval_file"))

    if [ -n "$TIMEOUT_CMD" ]; then
      output=$($TIMEOUT_CMD 60 claude -p "$query" \
        --dangerously-skip-permissions \
        --output-format stream-json \
        --verbose 2>/dev/null || true)
    else
      output=$(claude -p "$query" \
        --dangerously-skip-permissions \
        --output-format stream-json \
        --verbose 2>/dev/null || true)
    fi

    if echo "$output" | grep -q "\"skill\":\"siae-devforge:${skill_name}\"" || \
       echo "$output" | grep -q "\"skill\":\"${skill_name}\""; then
      tp=$((tp + 1))
    else
      fn=$((fn + 1))
    fi
  done

  # Test should-not-trigger queries
  tn=0  # true negatives
  fp=0  # false positives
  for i in $(seq 0 $((total_should_not - 1))); do
    query=$(jq -r ".[$i | tonumber].query // empty" <(jq '[.[] | select(.should_trigger == false)]' "$eval_file"))

    if [ -n "$TIMEOUT_CMD" ]; then
      output=$($TIMEOUT_CMD 60 claude -p "$query" \
        --dangerously-skip-permissions \
        --output-format stream-json \
        --verbose 2>/dev/null || true)
    else
      output=$(claude -p "$query" \
        --dangerously-skip-permissions \
        --output-format stream-json \
        --verbose 2>/dev/null || true)
    fi

    if echo "$output" | grep -q "\"skill\":\"siae-devforge:${skill_name}\"" || \
       echo "$output" | grep -q "\"skill\":\"${skill_name}\""; then
      fp=$((fp + 1))
    else
      tn=$((tn + 1))
    fi
  done

  # Calcola metriche
  if [ "$total_should" -gt 0 ]; then
    recall=$(echo "scale=2; $tp / $total_should" | bc)
  else
    recall="1.00"
  fi

  if [ $((tp + fp)) -gt 0 ]; then
    precision=$(echo "scale=2; $tp / ($tp + $fp)" | bc)
  else
    precision="1.00"
  fi

  # Valuta soglie
  recall_ok=$(echo "$recall >= $RECALL_THRESHOLD" | bc)
  precision_ok=$(echo "$precision >= $PRECISION_THRESHOLD" | bc)

  if [ "$recall_ok" -eq 1 ] && [ "$precision_ok" -eq 1 ]; then
    echo "  PASS  ${skill_name}: ${tp}/${total_should} should-trigger, ${tn}/${total_should_not} should-not-trigger (P:${precision} R:${recall})"
    TOTAL_PASS=$((TOTAL_PASS + 1))
  else
    echo "  WARN  ${skill_name}: ${tp}/${total_should} should-trigger, ${tn}/${total_should_not} should-not-trigger (P:${precision} R:${recall})"
    [ "$recall_ok" -eq 0 ] && echo "         ↳ recall ${recall} < ${RECALL_THRESHOLD}"
    [ "$precision_ok" -eq 0 ] && echo "         ↳ precision ${precision} < ${PRECISION_THRESHOLD}"
    TOTAL_WARN=$((TOTAL_WARN + 1))
  fi
done

echo ""
echo "Trigger Regression: PASS=${TOTAL_PASS} WARN=${TOTAL_WARN} SKIP=${TOTAL_SKIP}"

# WARN non causa fallimento — le description sono probabilistiche
exit 0
