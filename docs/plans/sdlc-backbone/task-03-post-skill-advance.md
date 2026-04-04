# Task 03: post-skill Avanza Stage

**Dipendenze:** Task 02 (sdlc-state.sh)
**File coinvolti:** `hooks/post-skill`

---

## Step 1 — Source sdlc-state.sh in post-skill

In `hooks/post-skill`, dopo `source "${PLUGIN_ROOT}/lib/logger.sh"`, aggiungere:

```bash
source "${PLUGIN_ROOT}/lib/sdlc-state.sh"
```

## Step 2 — Avanza stage dopo registrazione skill

Dopo il blocco che scrive in `SESSION_SKILLS_FILE` (la sezione "Step 1 CRITICAL"), aggiungere:

```bash
# Advance SDLC stage if this is a backbone skill
BACKBONE_STAGE="${SDLC_BACKBONE_MAP[$SKILL_NAME]:-}"
if [ -n "$BACKBONE_STAGE" ]; then
    sdlc_advance_stage "$BACKBONE_STAGE"
fi
```

## Step 3 — Verifica

```bash
export DEVFORGE_STATE_DIR=$(mktemp -d)
mkdir -p "$DEVFORGE_STATE_DIR"

# Simula invocazione siae-brainstorming
echo '{"skill":"siae-devforge:siae-brainstorming"}' | bash hooks/post-skill 2>/dev/null

# Verifica che lo stage sia avanzato
source lib/sdlc-state.sh
echo "Stage: $(sdlc_get_current_stage)"  # brainstorming
echo "Completed: $(sdlc_get_completed_stages)"  # brainstorming

# Simula siae-writing-plans
echo '{"skill":"siae-devforge:siae-writing-plans"}' | bash hooks/post-skill 2>/dev/null
echo "Completed: $(sdlc_get_completed_stages)"  # brainstorming,plan

rm -rf "$DEVFORGE_STATE_DIR"
```

## Step 4 — Commit

```bash
git add hooks/post-skill
git commit -m "feat(backbone): post-skill advances SDLC stage for backbone skills

- Sources lib/sdlc-state.sh
- Looks up skill in SDLC_BACKBONE_MAP
- Calls sdlc_advance_stage if backbone skill

Co-Authored-By: SIAE DevForge"
```
