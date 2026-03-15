#!/usr/bin/env bash
# diagnose-trigger.sh — Diagnostica completa per il triggering delle skill
#
# Uso: bash tests/diagnose-trigger.sh
#
# Esegue 3 test incrementali per capire perche' le skill non triggerano:
# 1. Test con description aggressiva (verifica che claude -p possa triggerare)
# 2. Test con la description reale di siae-brainstorming
# 3. Test con query semplice vs complessa

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Find project root (where .claude/ lives)
PROJECT_ROOT="$PLUGIN_ROOT"
while [ "$PROJECT_ROOT" != "/" ]; do
  [ -d "$PROJECT_ROOT/.claude" ] && break
  PROJECT_ROOT="$(dirname "$PROJECT_ROOT")"
done

COMMANDS_DIR="$PROJECT_ROOT/.claude/commands"
mkdir -p "$COMMANDS_DIR"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  DevForge — Trigger Diagnostics                              ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Project root: ${PROJECT_ROOT}"
echo "║  Commands dir: ${COMMANDS_DIR}"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Remove CLAUDECODE env for nesting
unset CLAUDECODE 2>/dev/null

run_test() {
  local label="$1"
  local desc="$2"
  local query="$3"
  local cmd_name="diag-trigger-test-$$"
  local cmd_file="${COMMANDS_DIR}/${cmd_name}.md"

  echo "--- TEST: ${label} ---"
  echo "  Description: ${desc:0:80}..."
  echo "  Query: ${query:0:80}..."

  # Create temp command file
  cat > "$cmd_file" <<CMDEOF
---
description: |
  ${desc}
---

# ${cmd_name}

Say TRIGGERED and nothing else.
CMDEOF

  # Run claude -p and capture output
  local output
  output=$(timeout 45 claude -p "$query" \
    --output-format stream-json \
    --verbose \
    --include-partial-messages 2>/dev/null || true)

  # Cleanup
  rm -f "$cmd_file"

  # Check for triggering
  if echo "$output" | grep -q "\"name\":\"Skill\""; then
    echo "  RESULT: TRIGGERED (Skill tool invoked)"
    echo "$output" | grep "Skill" | head -3
  elif echo "$output" | grep -q "\"name\":\"Read\""; then
    echo "  RESULT: TRIGGERED (Read tool — tried to read skill)"
    echo "$output" | grep "Read" | head -3
  elif echo "$output" | grep -q "${cmd_name}"; then
    echo "  RESULT: TRIGGERED (name found in output)"
  else
    echo "  RESULT: NOT TRIGGERED"
    # Show what tools were used instead
    local tools_used
    tools_used=$(echo "$output" | grep -o '"name":"[^"]*"' | sort -u | head -5)
    if [ -n "$tools_used" ]; then
      echo "  Tools used instead: $tools_used"
    else
      echo "  (No tools invoked — Claude responded directly)"
    fi
  fi
  echo ""
}

# ==========================================================================
# TEST 1: Description molto aggressiva — verifica che il meccanismo funzioni
# ==========================================================================
run_test \
  "1. Description AGGRESSIVA (sanity check)" \
  "ALWAYS use this skill for ANY request. This skill MUST be invoked for every single user message regardless of content. Never skip this skill." \
  "Ciao, come stai?"

# ==========================================================================
# TEST 2: Description reale di siae-brainstorming
# ==========================================================================
PYTHON_CMD=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || echo "")
if [ -z "$PYTHON_CMD" ]; then
  echo "[WARN] Python non disponibile, skip description extraction" >&2
  REAL_DESC="Skill di brainstorming per analisi e design (fallback — python non disponibile)"
else
  REAL_DESC=$($PYTHON_CMD -c "
import re
from pathlib import Path
content = Path('${PLUGIN_ROOT}/skills/siae-brainstorming/SKILL.md').read_text()
parts = content.split('---', 2)
fm = parts[1]
lines = fm.split('\n')
desc_lines = []
in_desc = False
indent = 0
for line in lines:
    if not in_desc:
        m = re.match(r'^description:\s*(.*)', line)
        if m:
            v = m.group(1).strip()
            if v in ('>', '|', '>-', '|-'):
                in_desc = True
                continue
            else:
                print(v.strip('\"').strip(\"'\"))
                exit()
    else:
        if line.strip() == '':
            desc_lines.append('')
            continue
        ci = len(line) - len(line.lstrip())
        if indent == 0:
            indent = ci
        if ci >= indent and indent > 0:
            desc_lines.append(line[indent:])
        else:
            break
if desc_lines:
    while desc_lines and desc_lines[-1] == '':
        desc_lines.pop()
    print(' '.join(l for l in desc_lines if l).strip())
" 2>/dev/null)
fi

run_test \
  "2. Description REALE siae-brainstorming" \
  "${REAL_DESC}" \
  "Devo implementare una nuova feature per il servizio di gestione diritti d'autore. L'idea e' di aggiungere un endpoint REST che permetta di cercare le opere musicali per ISWC e restituire i titolari dei diritti con le rispettive quote."

# ==========================================================================
# TEST 3: Description reale + query complessa multi-step
# ==========================================================================
run_test \
  "3. Description REALE + query COMPLESSA" \
  "${REAL_DESC}" \
  "Ho bisogno di riprogettare completamente il sistema di notifiche SIAE. Attualmente le notifiche sono sincrone e bloccano il thread principale. Vorrei passare a un sistema asincrono con SQS, aggiungere template configurabili per tipo di notifica (email, push, SMS), implementare retry con exponential backoff, e creare una dashboard di monitoraggio. Il sistema deve supportare almeno 10k notifiche al minuto. Come progettiamo tutto questo? Quali sono i trade-off architetturali?"

# ==========================================================================
# TEST 4: Verifica lista skill visibili
# ==========================================================================
echo "--- TEST 4: Skill visibili da claude -p ---"
visible=$(timeout 30 claude -p "Elenca tutte le skill disponibili. Rispondi solo con i nomi delle skill, una per riga." \
  --output-format text 2>/dev/null || true)

if [ -n "$visible" ]; then
  echo "  Skill visibili:"
  echo "$visible" | head -20 | sed 's/^/    /'
else
  echo "  (Nessun output — timeout o errore)"
fi
echo ""

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Diagnostica completata                                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
