# Task 06: stage-gate (Sostituisce sub-skill-gate)

**Dipendenze:** Task 02 (sdlc-state.sh)
**File coinvolti:** modifica `hooks/sub-skill-gate`

---

## Step 1 — Riscrivi sub-skill-gate come stage-gate

Sostituire la logica PREREQ_MAP hardcoded con un check basato su `sdlc_check_prerequisites`:

```bash
# Strip plugin prefix
SKILL_NAME="${SKILL_NAME##*:}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${PLUGIN_ROOT}/lib/logger.sh"
source "${PLUGIN_ROOT}/lib/sdlc-state.sh"

# Look up backbone stage for this skill
SKILL_STAGE="${SDLC_BACKBONE_MAP[$SKILL_NAME]:-}"

# If not a backbone skill, check if it's a specialist with a stage
if [ -z "$SKILL_STAGE" ]; then
    # Read backbone_stage from frontmatter via skills-core.js
    SKILL_STAGE=$(node -e "
const {findSkillsInDir} = require('$PLUGIN_ROOT/lib/skills-core');
const skills = findSkillsInDir('$PLUGIN_ROOT/skills');
const s = skills.find(s => s.name === '$SKILL_NAME');
console.log(s?.backbone_stage || '');
" 2>/dev/null || echo "")
fi

# No stage = support skill, no gate
if [ -z "$SKILL_STAGE" ]; then
    echo '{}'
    exit 0
fi

# Check prerequisites for the target stage
PREREQS=$(sdlc_check_prerequisites "$SKILL_STAGE")
if [ "$PREREQS" != "ok" ]; then
    MISSING="${PREREQS#missing:}"
    devforge_log "stage_gate" "blocked" "{\"skill\":\"$SKILL_NAME\",\"stage\":\"$SKILL_STAGE\",\"missing\":\"$MISSING\"}"
    cat <<EOF
{
  "decision": "block",
  "reason": "DevForge Stage Gate — BLOCCATO. La skill ${SKILL_NAME} (fase: ${SKILL_STAGE}) richiede prima: ${MISSING}."
}
EOF
    exit 0
fi

echo '{}'
exit 0
```

## Step 2 — Rimuovi PREREQ_MAP

Eliminare l'array PREREQ_MAP hardcoded (righe 41-48 attuali) e tutta la logica di lookup manuale. La mappatura e' ora nel frontmatter + SDLC_BACKBONE_MAP.

## Step 3 — Verifica

```bash
export DEVFORGE_STATE_DIR=$(mktemp -d)
mkdir -p "$DEVFORGE_STATE_DIR"
source lib/sdlc-state.sh

# siae-tdd senza brainstorming+plan: blocca
result=$(echo '{"skill":"siae-devforge:siae-tdd"}' | bash hooks/sub-skill-gate 2>/dev/null)
echo "$result" | grep -q '"block"' && echo "PASS: blocks tdd without brainstorming+plan" || echo "FAIL"

# Con brainstorming+plan+execution: passa
sdlc_advance_stage "brainstorming"
sdlc_advance_stage "plan"
sdlc_advance_stage "execution"
result=$(echo '{"skill":"siae-devforge:siae-tdd"}' | bash hooks/sub-skill-gate 2>/dev/null)
[ "$result" = "{}" ] && echo "PASS: allows tdd with prereqs" || echo "FAIL"

# Support skill (no stage): sempre passa
result=$(echo '{"skill":"siae-devforge:siae-onboarding"}' | bash hooks/sub-skill-gate 2>/dev/null)
[ "$result" = "{}" ] && echo "PASS: allows support skill always" || echo "FAIL"

rm -rf "$DEVFORGE_STATE_DIR"
```

## Step 4 — Commit

```bash
git add hooks/sub-skill-gate
git commit -m "refactor(backbone): replace PREREQ_MAP with SDLC stage-based checks

- sub-skill-gate now checks sdlc_check_prerequisites instead of hardcoded map
- Backbone skills: checked via SDLC_BACKBONE_MAP
- Specialist skills: stage read from frontmatter backbone_stage
- Support skills: no gate, always allowed

Co-Authored-By: SIAE DevForge"
```
