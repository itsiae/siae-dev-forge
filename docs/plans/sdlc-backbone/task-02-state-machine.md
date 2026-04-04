# Task 02: State Machine lib/sdlc-state.sh

**Dipendenze:** Task 01 (metadata per BACKBONE_MAP)
**File coinvolti:** nuovo `lib/sdlc-state.sh`, modifica `hooks/session-start`

---

## Step 1 — Crea `lib/sdlc-state.sh`

```bash
#!/usr/bin/env bash
# SDLC State Machine — backbone stage tracking
# Sourced by hooks that need to read/write SDLC stage state.
# Requires: DEVFORGE_STATE_DIR (from lib/logger.sh)

SDLC_STATE_FILE="${DEVFORGE_STATE_DIR}/.devforge-sdlc-stage"

# Ordered backbone stages
SDLC_STAGES=("brainstorming" "plan" "execution" "tdd" "review" "verification" "finish")

# Backbone skill → stage mapping
declare -A SDLC_BACKBONE_MAP=(
    ["siae-brainstorming"]="brainstorming"
    ["siae-writing-plans"]="plan"
    ["siae-executing-plans"]="execution"
    ["siae-tdd"]="tdd"
    ["siae-review-gate"]="review"
    ["siae-verification"]="verification"
    ["siae-finishing-branch"]="finish"
)

sdlc_get_current_stage() {
    if [ -f "$SDLC_STATE_FILE" ]; then
        python3 -c "
import json, sys
with open('$SDLC_STATE_FILE') as f:
    print(json.load(f).get('current_stage', 'idle'))
" 2>/dev/null || echo "idle"
    else
        echo "idle"
    fi
}

sdlc_get_completed_stages() {
    if [ -f "$SDLC_STATE_FILE" ]; then
        python3 -c "
import json
with open('$SDLC_STATE_FILE') as f:
    print(','.join(json.load(f).get('completed_stages', [])))
" 2>/dev/null || echo ""
    else
        echo ""
    fi
}

sdlc_is_stage_completed() {
    local stage="$1"
    local completed
    completed=$(sdlc_get_completed_stages)
    echo ",$completed," | grep -q ",$stage," && echo "yes" || echo "no"
}

sdlc_advance_stage() {
    local stage="$1"
    if [ ! -f "$SDLC_STATE_FILE" ]; then
        echo "{\"current_stage\":\"$stage\",\"completed_stages\":[\"$stage\"],\"active_specialists\":[],\"blocked_on\":null}" > "$SDLC_STATE_FILE"
        return 0
    fi
    python3 -c "
import json
with open('$SDLC_STATE_FILE') as f:
    s = json.load(f)
completed = s.get('completed_stages', [])
if '$stage' not in completed:
    completed.append('$stage')
s['completed_stages'] = completed
s['current_stage'] = '$stage'
with open('$SDLC_STATE_FILE', 'w') as f:
    json.dump(s, f)
" 2>/dev/null
}

sdlc_check_prerequisites() {
    local target_stage="$1"
    local stages_csv
    stages_csv=$(sdlc_get_completed_stages)

    python3 -c "
# Fasi obbligatorie (execution e' bypassabile)
REQUIRED = ['brainstorming', 'plan', 'tdd', 'review', 'verification', 'finish']
ALL = ['brainstorming', 'plan', 'execution', 'tdd', 'review', 'verification', 'finish']
completed = set('$stages_csv'.split(',')) if '$stages_csv' else set()
target = '$target_stage'
if target not in ALL:
    print('ok')
else:
    idx = ALL.index(target)
    missing = [st for st in REQUIRED if ALL.index(st) < idx and st not in completed]
    print('missing:' + ','.join(missing) if missing else 'ok')
" 2>/dev/null || echo "ok"
}

sdlc_get_stage_specialists() {
    local stage="$1"
    local plugin_root="$2"
    # Use skills-core.js to get specialists for a stage
    node -e "
const {findSkillsInDir} = require('$plugin_root/lib/skills-core');
const skills = findSkillsInDir('$plugin_root/skills');
const specialists = skills.filter(s => s.backbone_role === 'specialist' && s.backbone_stage === '$stage');
specialists.forEach(s => console.log(s.name));
" 2>/dev/null || echo ""
}
```

## Step 2 — Reset state in session-start

In `hooks/session-start`, dopo il cleanup dei file di stato (riga ~238), aggiungere:

```bash
# Reset SDLC stage for new session
rm -f "${DEVFORGE_STATE_DIR}/.devforge-sdlc-stage"
```

## Step 3 — Verifica

```bash
# Test state machine
source lib/logger.sh
source lib/sdlc-state.sh

# Stato iniziale
echo "Current: $(sdlc_get_current_stage)"  # idle
echo "Completed: $(sdlc_get_completed_stages)"  # vuoto

# Avanza brainstorming
sdlc_advance_stage "brainstorming"
echo "Current: $(sdlc_get_current_stage)"  # brainstorming
echo "Completed: $(sdlc_get_completed_stages)"  # brainstorming

# Check prerequisites per plan
echo "Prereqs plan: $(sdlc_check_prerequisites plan)"  # ok
echo "Prereqs tdd: $(sdlc_check_prerequisites tdd)"  # missing:plan,execution

# Cleanup
rm -f "${DEVFORGE_STATE_DIR}/.devforge-sdlc-stage"
```

## Step 4 — Commit

```bash
git add lib/sdlc-state.sh hooks/session-start
git commit -m "feat(backbone): add SDLC state machine lib/sdlc-state.sh

- 7-stage backbone: brainstorming → plan → execution → tdd → review → verification → finish
- JSON state file in DEVFORGE_STATE_DIR
- Functions: get/advance/check stage, get specialists
- session-start resets state for new sessions

Co-Authored-By: SIAE DevForge"
```
