#!/usr/bin/env bash
# SDLC State Machine — backbone stage tracking
# Sourced by hooks that need to read/write SDLC stage state.
# Requires: DEVFORGE_STATE_DIR (from lib/logger.sh)

SDLC_STATE_FILE="${DEVFORGE_STATE_DIR}/.devforge-sdlc-stage"

# Ordered backbone stages
SDLC_STAGES=("brainstorming" "plan" "execution" "tdd" "review" "verification" "finish")

# Backbone skill → stage mapping (bash 3 compatible, no declare -A)
SDLC_BACKBONE_ENTRIES=(
    "siae-brainstorming=brainstorming"
    "siae-writing-plans=plan"
    "siae-executing-plans=execution"
    "siae-tdd=tdd"
    "siae-review-gate=review"
    "siae-verification=verification"
    "siae-finishing-branch=finish"
)

# Lookup: returns stage for a backbone skill name, or empty
sdlc_lookup_stage() {
    local skill="$1"
    for entry in "${SDLC_BACKBONE_ENTRIES[@]}"; do
        if [ "${entry%%=*}" = "$skill" ]; then
            echo "${entry#*=}"
            return 0
        fi
    done
    echo ""
}

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
    node -e "
const {findSkillsInDir} = require('$plugin_root/lib/skills-core');
const skills = findSkillsInDir('$plugin_root/skills');
const specialists = skills.filter(s => s.backbone_role === 'specialist' && s.backbone_stage === '$stage');
specialists.forEach(s => console.log(s.name));
" 2>/dev/null || echo ""
}
