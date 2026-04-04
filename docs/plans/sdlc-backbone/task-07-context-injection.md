# Task 07: Context Injection Phase-Based

**Dipendenze:** Task 02 (sdlc-state.sh)
**File coinvolti:** `hooks/devforge-reinject`, `hooks/session-start`

---

## Step 1 — Aggiorna devforge-reinject

Sostituire la re-injection del catalogo completo con un contesto phase-based:

```bash
# Source SDLC state
source "${PLUGIN_ROOT}/lib/sdlc-state.sh"

CURRENT=$(sdlc_get_current_stage)
COMPLETED=$(sdlc_get_completed_stages)

# Get specialists for current stage
SPECIALISTS=""
if [ "$CURRENT" != "idle" ]; then
    SPECIALISTS=$(sdlc_get_stage_specialists "$CURRENT" "$PLUGIN_ROOT" 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
fi

# Build compact context
SDLC_CONTEXT="Fase SDLC attuale: ${CURRENT}"
[ -n "$COMPLETED" ] && SDLC_CONTEXT="${SDLC_CONTEXT}\nFasi completate: ${COMPLETED}"

# Determine open gates
GATES=""
if [ "$(sdlc_is_stage_completed "brainstorming")" != "yes" ]; then
    GATES="brainstorming richiesto prima di qualsiasi implementazione"
elif [ "$(sdlc_is_stage_completed "tdd")" != "yes" ]; then
    GATES="tdd richiesto prima di modificare codice produzione"
elif [ "$(sdlc_is_stage_completed "review")" != "yes" ]; then
    GATES="review richiesto prima di chiudere"
fi
[ -n "$GATES" ] && SDLC_CONTEXT="${SDLC_CONTEXT}\nGate aperti: ${GATES}"

[ -n "$SPECIALISTS" ] && SDLC_CONTEXT="${SDLC_CONTEXT}\nSkill specialistiche consigliate: ${SPECIALISTS}"
```

Iniettare `$SDLC_CONTEXT` in `additional_context` al posto del catalogo skill.

## Step 2 — Aggiorna session-start

`session-start` continua a iniettare il catalogo backbone (7 skill) + lista specialist raggruppata per fase. Ma cambia il formato: raggruppamento per fase, non lista piatta.

## Step 3 — Verifica

```bash
export DEVFORGE_STATE_DIR=$(mktemp -d)
mkdir -p "$DEVFORGE_STATE_DIR"
source lib/sdlc-state.sh
sdlc_advance_stage "brainstorming"
sdlc_advance_stage "plan"

# Simula reinject
echo '{"message":"implementa il servizio"}' | bash hooks/devforge-reinject 2>/dev/null
# Deve contenere "Fase SDLC attuale: plan" e specialist per execution

rm -rf "$DEVFORGE_STATE_DIR"
```

## Step 4 — Commit

```bash
git add hooks/devforge-reinject hooks/session-start
git commit -m "feat(backbone): phase-based context injection in reinject

- devforge-reinject shows current SDLC stage + specialists instead of full catalog
- session-start injects backbone catalog grouped by phase
- Much less noise, more relevant suggestions

Co-Authored-By: SIAE DevForge"
```
