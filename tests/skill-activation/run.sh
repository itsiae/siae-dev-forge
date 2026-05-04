#!/usr/bin/env bash
# Skill Activation Test Runner — invoca Bedrock per ogni case in cases.yml
# Usage: TEST_MODEL=sonnet|haiku ./run.sh [--smoke]

set -euo pipefail
cd "$(dirname "$0")"

: "${AWS_REGION:=eu-west-1}"
: "${AWS_BEARER_TOKEN_BEDROCK:?AWS_BEARER_TOKEN_BEDROCK not set}"

case "${TEST_MODEL:-sonnet}" in
  sonnet) MODEL="eu.anthropic.claude-sonnet-4-6-20250929-v1:0" ;;
  haiku)  MODEL="eu.anthropic.claude-haiku-4-5-20251001-v1:0" ;;
  *) echo "TEST_MODEL must be sonnet|haiku"; exit 2 ;;
esac

SMOKE=0
[ "${1:-}" = "--smoke" ] && SMOKE=1

CASES_FILE="${CASES_FILE:-cases.yml}"
[ -f "$CASES_FILE" ] || { echo "Cases file missing: $CASES_FILE"; exit 1; }

OUT_DIR=".cache"
mkdir -p "$OUT_DIR"
LOG="$OUT_DIR/run-$(date +%Y%m%d-%H%M%S).jsonl"
echo "Model: $MODEL"
echo "Output log: $LOG"

# Skill descriptions context (frontmatter only) — instruct LLM to choose best skill
SKILL_CTX="$OUT_DIR/skill-context.txt"
{
  echo "Sei un router di skill. Dato un prompt utente, identifica QUALE skill DevForge invochi PRIMA."
  echo "Lista skill disponibili (name + description):"
  echo
  for f in ../../skills/*/SKILL.md; do
    name=$(grep -m1 '^name:' "$f" | awk '{print $2}')
    desc=$(awk '/^description:/{flag=1; sub(/^description: */,""); next} flag && /^[a-z_]+:/{flag=0} flag' "$f" | tr '\n' ' ' | sed 's/  */ /g' | head -c 400)
    echo "- name: $name"
    echo "  description: $desc"
  done
  echo
  echo "Rispondi SOLO in JSON: {\"primary\": \"<skill-name>\", \"chain\": [\"...\"]}"
} > "$SKILL_CTX"

# Iterate cases.yml
LIMIT=30
[ "$SMOKE" = "1" ] && LIMIT=3

python3 -c "
import yaml, json, sys
cases = yaml.safe_load(open('$CASES_FILE'))[:$LIMIT]
for c in cases:
    print(json.dumps(c))
" | while IFS= read -r case_json; do
  id=$(echo "$case_json" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
  prompt=$(echo "$case_json" | python3 -c 'import sys,json; print(json.load(sys.stdin)["prompt"])')

  echo "=== $id ==="

  # Build Bedrock payload — M2 fix: pass SKILL_CTX path as argv[2]
  # to prevent shell expansion fragility when path contains apostrophes/spaces.
  payload=$(python3 -c "
import json, sys
ctx = open(sys.argv[2], encoding='utf-8').read()
prompt = sys.argv[1]
body = {
    'anthropic_version': 'bedrock-2023-05-31',
    'max_tokens': 200,
    'temperature': 0.0,
    'system': ctx,
    'messages': [{'role': 'user', 'content': prompt}]
}
print(json.dumps(body, ensure_ascii=False))
" "$prompt" "$SKILL_CTX")

  # Invoke Bedrock (via aws cli)
  resp=$(aws bedrock-runtime invoke-model \
    --region "$AWS_REGION" \
    --model-id "$MODEL" \
    --body "$payload" \
    --cli-binary-format raw-in-base64-out \
    /dev/stdout 2>&1) || {
      echo "{\"id\": \"$id\", \"error\": \"bedrock_call_failed\", \"detail\": $(echo "$resp" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')}" >> "$LOG"
      continue
    }

  # Extract text from Bedrock response (Anthropic format)
  text=$(echo "$resp" | python3 -c "
import json, sys
data = json.load(sys.stdin)
content = data.get('content', [])
text = ''.join([c.get('text','') for c in content if c.get('type')=='text'])
print(text)
")

  echo "{\"id\": \"$id\", \"prompt\": $(echo "$prompt" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))'), \"response\": $(echo "$text" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')}" >> "$LOG"
done

echo "Done. Log: $LOG"
echo "Run evaluator: python3 evaluator.py $LOG"
