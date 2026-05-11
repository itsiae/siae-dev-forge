# Task 11 — State File Writers (PostToolUse Hooks)

**Goal:** Hook che aggiornano `.skill-state` quando brainstorm/debug/tdd/verification completano. State legge in `skill-advisory` (Task 10).

**File coinvolti:**
- `hooks/state-writer` (nuovo)
- `hooks/hooks.json` (modifica — registra hook PostToolUse)

## Step 1 — Definisci schema state file

`.claude/projects/<project>/.skill-state` JSON:

```json
{
  "last_brainstorm_completed": "2026-05-03T10:15:00Z",
  "last_brainstorm_step": 7,
  "last_fix_or_implementation_done": "2026-05-03T10:30:00Z",
  "last_verification_passed": "2026-05-03T10:35:00Z",
  "last_tdd_cycle": "2026-05-03T10:25:00Z",
  "last_debug_phase": 4,
  "version": 1
}
```

Tutti i campi opzionali. File vuoto/missing = stato vuoto = nessun gate (massima permissività).

## Step 2 — State writer hook

In `hooks/state-writer`:

```bash
#!/usr/bin/env bash
# State Writer Hook — PostToolUse event per skill backbone.
# Aggiorna .skill-state con timestamp completion. Non-blocking.

set -euo pipefail

STATE_DIR="${CLAUDE_PROJECT_DIR:-.}/.claude/projects/$(basename "$(pwd)")"
STATE_FILE="$STATE_DIR/.skill-state"
mkdir -p "$STATE_DIR"

INPUT="$(cat)"

# Estrai skill name + result status
DATA=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    skill = d.get('tool_input', {}).get('skill', '') or d.get('tool_input', {}).get('skill_name', '')
    if ':' in skill:
        skill = skill.split(':', 1)[1]
    success = d.get('tool_response', {}).get('is_error', True) is False
    print(f'{skill}\t{success}')
except Exception:
    print('\\tFalse')
")

SKILL=$(echo "$DATA" | cut -f1)
SUCCESS=$(echo "$DATA" | cut -f2)

[ -z "$SKILL" ] && exit 0
[ "$SUCCESS" != "True" ] && exit 0

NOW=$(date -u +%FT%TZ)

# Skill-specific state update
python3 <<PYEOF
import json, os
sf = "$STATE_FILE"
state = {}
if os.path.exists(sf):
    try:
        state = json.load(open(sf))
    except Exception:
        state = {}

skill = "$SKILL"
now = "$NOW"
state['version'] = state.get('version', 1)

if skill == "siae-brainstorming":
    state['last_brainstorm_completed'] = now
    state['last_brainstorm_step'] = 7
elif skill == "siae-debugging":
    state['last_debug_phase'] = 4
elif skill == "siae-tdd":
    state['last_tdd_cycle'] = now
    state['last_fix_or_implementation_done'] = now
elif skill == "siae-verification":
    state['last_verification_passed'] = now
elif skill == "siae-writing-plans":
    state['last_plan_written'] = now

with open(sf, 'w') as f:
    json.dump(state, f, indent=2)
PYEOF

exit 0
```

## Step 3 — Make eseguibile + test syntax

```bash
chmod +x hooks/state-writer
bash -n hooks/state-writer
```

## Step 4 — Test isolato

```bash
# Setup
TEST_PROJ=/tmp/test-state-writer
mkdir -p "$TEST_PROJ/.claude/projects/test-state-writer"
cd "$TEST_PROJ"

# Simula brainstorming completato
CLAUDE_PROJECT_DIR=$TEST_PROJ \
  echo '{"tool_input": {"skill": "siae-brainstorming"}, "tool_response": {"is_error": false}}' \
  | bash /Users/detomasi/Library/Mobile\ Documents/com~apple~CloudDocs/siae-dev-forge/hooks/state-writer

cat $TEST_PROJ/.claude/projects/test-state-writer/.skill-state
# Atteso: JSON con last_brainstorm_completed e last_brainstorm_step: 7

# Cleanup
rm -rf "$TEST_PROJ"
```

## Step 5 — Test integrazione con skill-advisory

```bash
# Stato pieno = no suggestion
echo '{"last_fix_or_implementation_done": "2026-05-03T10:00:00Z"}' > /tmp/state-test.json
STATE_FILE_OVERRIDE=/tmp/state-test.json \
  echo '{"tool_input": {"skill": "siae-verification"}}' \
  | hooks/skill-advisory
# Atteso: empty (nessuna suggestion perché last_fix è settato)
```

## Step 6 — Commit

```bash
git add hooks/state-writer
git commit -m "feat(hooks): state-writer PostToolUse aggiorna .skill-state per backbone

Hook che traccia completion di siae-brainstorming/debugging/tdd/verification/
writing-plans nel file .skill-state per progetto. Letto da skill-advisory.
Non-blocking, idempotente. Test isolato + integrazione PASS."
```

## Criteri accettazione

- `hooks/state-writer` eseguibile
- Sintassi bash OK
- Test isolato genera state file corretto
- Test integrazione con skill-advisory OK

## NO-REGRESSION

Pure observer + writer. Zero impact su skill esistenti.
