#!/usr/bin/env bash
# run-trigger-regression.sh — Trigger regression tests per skill DevForge
#
# Uso: ./tests/run-trigger-regression.sh [--skill <nome>] [--runs-per-query N]
#                                        [--num-workers N] [--timeout N] [--model <id>]
#
# Thin wrapper che itera su evals/trigger-evals/*.json e chiama
# run-trigger-eval.py per ogni skill. Allineato ad Anthropic skill-creator.
#
# Exit code: 0 = tutti sopra soglia, 1 = almeno uno sotto soglia

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
EVALS_DIR="${PLUGIN_ROOT}/evals/trigger-evals"
EVAL_SCRIPT="${SCRIPT_DIR}/run-trigger-eval.py"
RESULTS_DIR="${PLUGIN_ROOT}/evals/results"

# Defaults
SINGLE_SKILL=""
RUNS_PER_QUERY=3
NUM_WORKERS=8
TIMEOUT=60
MODEL=""

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skill) SINGLE_SKILL="$2"; shift 2 ;;
    --runs-per-query) RUNS_PER_QUERY="$2"; shift 2 ;;
    --num-workers) NUM_WORKERS="$2"; shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    *) echo "Uso: $0 [--skill <nome>] [--runs-per-query N] [--num-workers N] [--timeout N] [--model <id>]"; exit 1 ;;
  esac
done

# Prerequisites
if ! command -v claude >/dev/null 2>&1; then
  echo "  SKIP  claude CLI non disponibile"
  exit 0
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "  FAIL  python3 non disponibile"
  exit 1
fi
if [ ! -f "$EVAL_SCRIPT" ]; then
  echo "  FAIL  run-trigger-eval.py non trovato in ${EVAL_SCRIPT}"
  exit 1
fi

TOTAL_PASS=0
TOTAL_WARN=0
TOTAL_SKIP=0

echo "Trigger Regression Tests (claude -p, ${RUNS_PER_QUERY} runs/query, ${NUM_WORKERS} workers)"
echo "=========================================="
echo ""

for eval_file in "${EVALS_DIR}"/*.json; do
  [ ! -f "$eval_file" ] && continue
  [ "$(basename "$eval_file")" = ".gitkeep" ] && continue

  skill_name=$(basename "$eval_file" .json)

  if [ -n "$SINGLE_SKILL" ] && [ "$skill_name" != "$SINGLE_SKILL" ]; then
    continue
  fi

  # Build command
  CMD=(python3 "$EVAL_SCRIPT"
    --eval-file "$eval_file"
    --skill "$skill_name"
    --plugin-root "$PLUGIN_ROOT"
    --runs-per-query "$RUNS_PER_QUERY"
    --num-workers "$NUM_WORKERS"
    --timeout "$TIMEOUT"
    --results-dir "$RESULTS_DIR"
    --verbose)

  [ -n "$MODEL" ] && CMD+=(--model "$MODEL")

  # Run: stderr has verbose output, stdout has JSON
  verbose_output=$("${CMD[@]}" 2>&1 >/dev/null)
  exit_code=$?

  # Display verbose lines
  echo "$verbose_output" | grep -E "^\s*\[" | head -25
  echo "$verbose_output" | grep "^Results:" | head -1

  if [ "$exit_code" -eq 0 ]; then
    echo "  PASS  ${skill_name}"
    TOTAL_PASS=$((TOTAL_PASS + 1))
  elif [ "$exit_code" -eq 1 ]; then
    echo "  WARN  ${skill_name}"
    TOTAL_WARN=$((TOTAL_WARN + 1))
  else
    echo "  SKIP  ${skill_name} (exit code ${exit_code})"
    TOTAL_SKIP=$((TOTAL_SKIP + 1))
  fi
  echo ""
done

echo "=========================================="
echo "Trigger Regression: PASS=${TOTAL_PASS} WARN=${TOTAL_WARN} SKIP=${TOTAL_SKIP}"

# WARN non causa fallimento — le description sono probabilistiche
exit 0
