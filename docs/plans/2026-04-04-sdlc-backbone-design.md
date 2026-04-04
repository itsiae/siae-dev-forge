# Design: SDLC Backbone — Catena Minima Obbligatoria

**Data:** 2026-04-04
**Autore:** Lorenzo De Tomasi + DevForge
**Story Points:** 8 SP-Umano / 3 SP-Augmented
**Approccio:** State machine con 3 gate phase-based, 7 fasi backbone, specialist agganciate

---

## Contesto

DevForge ha 37 skill e 7 gate hook. Il sistema attuale ha problemi:
- I gate controllano singole skill, non fasi del processo
- Nessun concetto di ordine tra fasi (puoi fare TDD senza brainstorming)
- 37 skill competono per attivarsi — troppo rumore
- La PREREQ_MAP in sub-skill-gate e' hardcoded e in drift

## Le 3 Regole Madre

1. **Nessuna implementazione senza brainstorming + plan**
2. **Nessun codice produzione senza tdd**
3. **Nessuna chiusura senza review + verification + finish**

Tutto il resto e' specialistico.

## Decisioni architetturali

| # | Decisione | Alternative scartate | Motivazione |
|---|-----------|---------------------|-------------|
| ADR-1 | 7 fasi backbone con state machine JSON | Sequenza flat in PREREQ_MAP | Lo stato e' loggabile, ispezionabile, testabile |
| ADR-2 | 3 gate phase-based sostituiscono i 7 attuali | Gate aggiuntivi | Meno gate = meno rumore, piu' enforcement dove conta |
| ADR-3 | Specialist agganciate a fase, soft guidance | Hard gate per tutte | Bloccare per ogni specializzazione rallenta senza valore |
| ADR-4 | Context injection phase-based | Catalogo completo | Meno token, piu' rilevanza, meno conflitti tra skill |
| ADR-5 | siae-review-gate come nuova skill backbone | Review dispersa tra 3 skill | Una fase ha bisogno di un backbone che la rappresenti |

---

## Backbone: 7 Fasi

| # | Fase | Skill backbone | Hard gate |
|---|------|---------------|-----------|
| 1 | brainstorming | siae-brainstorming | SI |
| 2 | plan | siae-writing-plans | SI |
| 3 | execution | siae-executing-plans | NO (fase implicita) |
| 4 | tdd | siae-tdd | SI |
| 5 | review | siae-review-gate (nuova) | SI |
| 6 | verification | siae-verification | SI |
| 7 | finish | siae-finishing-branch | SI |

## Classificazione Skill

### Backbone (7)
siae-brainstorming, siae-writing-plans, siae-executing-plans, siae-tdd, siae-review-gate (nuova), siae-verification, siae-finishing-branch

### Specialist (22, agganciate a una fase)

| Fase | Specialist |
|------|-----------|
| brainstorming | siae-architecture, siae-codebase-map, siae-microservices-map, siae-service-logic-map |
| plan | — |
| execution | siae-code-standards, siae-security, siae-iac, siae-data-engineering, siae-frontend, siae-flutter, siae-finops, siae-parallel-agents, siae-subagent-development |
| tdd | siae-automation, siae-qa, siae-robot-framework, siae-nr-test-flows |
| review | siae-requesting-review, siae-receiving-review, siae-blind-review |
| verification | siae-debugging |
| finish | siae-documentation, siae-git-workflow |

### Support (8, nessun gate)
siae-onboarding, siae-git-env, siae-git-worktrees, siae-writing-skills, siae-autoresearch, siae-retrospective, siae-branching-strategy-check, using-devforge

---

## State Machine

### File di stato: `${DEVFORGE_STATE_DIR}/.devforge-sdlc-stage`

```json
{
  "current_stage": "execution",
  "completed_stages": ["brainstorming", "plan"],
  "active_specialists": ["siae-security"],
  "blocked_on": null
}
```

### Transizioni

```
IDLE → brainstorming → plan → execution → tdd → review → verification → finish → DONE
```

Regole di transizione:
- Una fase e' `completed` quando la sua skill backbone viene invocata E completa il suo flusso
- `post-skill` hook aggiorna lo stato quando una skill backbone viene invocata
- Le fasi possono essere ri-entrate (es. tornare a brainstorming dopo review)
- Le specialist non avanzano lo stato — operano dentro la fase corrente

### Libreria: `lib/sdlc-state.sh`

```bash
# Costanti backbone
SDLC_STAGES=("brainstorming" "plan" "execution" "tdd" "review" "verification" "finish")
SDLC_STATE_FILE="${DEVFORGE_STATE_DIR}/.devforge-sdlc-stage"

# Mappa backbone skill → stage
SDLC_BACKBONE_MAP=(
    "siae-brainstorming=brainstorming"
    "siae-writing-plans=plan"
    "siae-executing-plans=execution"
    "siae-tdd=tdd"
    "siae-review-gate=review"
    "siae-verification=verification"
    "siae-finishing-branch=finish"
)

sdlc_get_state() {
    if [ -f "$SDLC_STATE_FILE" ]; then
        cat "$SDLC_STATE_FILE"
    else
        echo '{"current_stage":"idle","completed_stages":[],"active_specialists":[],"blocked_on":null}'
    fi
}

sdlc_is_stage_completed() {
    local stage="$1"
    local state
    state=$(sdlc_get_state)
    echo "$state" | python3 -c "
import sys, json
s = json.load(sys.stdin)
print('yes' if '$stage' in s.get('completed_stages', []) else 'no')
" 2>/dev/null || echo "no"
}

sdlc_advance_stage() {
    local stage="$1"
    local state
    state=$(sdlc_get_state)
    echo "$state" | python3 -c "
import sys, json
s = json.load(sys.stdin)
completed = s.get('completed_stages', [])
if '$stage' not in completed:
    completed.append('$stage')
s['completed_stages'] = completed
s['current_stage'] = '$stage'
json.dump(s, sys.stdout)
" 2>/dev/null > "${SDLC_STATE_FILE}.tmp" && mv "${SDLC_STATE_FILE}.tmp" "$SDLC_STATE_FILE"
}

sdlc_check_prerequisites() {
    local target_stage="$1"
    # Trova l'indice della fase target
    # Verifica che tutte le fasi precedenti siano completate
    local state
    state=$(sdlc_get_state)
    echo "$state" | python3 -c "
import sys, json
STAGES = ['brainstorming', 'plan', 'execution', 'tdd', 'review', 'verification', 'finish']
s = json.load(sys.stdin)
completed = set(s.get('completed_stages', []))
target = '$target_stage'
if target not in STAGES:
    print('ok')
    sys.exit(0)
idx = STAGES.index(target)
missing = [st for st in STAGES[:idx] if st not in completed]
if missing:
    print('missing:' + ','.join(missing))
else:
    print('ok')
" 2>/dev/null || echo "ok"
}
```

---

## Gate Consolidamento

### I 3 nuovi gate

**1. `impl-gate`** (PreToolUse: Edit, Write su codice prod)
Sostituisce: `tdd-gate` + `plan-gate` (parzialmente)

```bash
# Regola 1: brainstorming + plan completate
# Regola 2: tdd completata
PREREQS=$(sdlc_check_prerequisites "tdd")
if [ "$PREREQS" != "ok" ]; then
    MISSING="${PREREQS#missing:}"
    # Block con messaggio che indica le fasi mancanti
fi
```

**2. `close-gate`** (PreToolUse: Bash git push/merge, Stop con claim)
Sostituisce: `stop-gate` (parzialmente) + `pre-commit` (parzialmente)

```bash
# Regola 3: review + verification completate
for stage in review verification; do
    if [ "$(sdlc_is_stage_completed "$stage")" != "yes" ]; then
        # Block
    fi
done
```

**3. `stage-gate`** (PreToolUse: Skill backbone)
Sostituisce: `sub-skill-gate`

```bash
# Verifica che la fase precedente sia completata
SKILL_STAGE=$(lookup backbone_stage for $SKILL_NAME)
PREREQS=$(sdlc_check_prerequisites "$SKILL_STAGE")
if [ "$PREREQS" != "ok" ]; then
    # Block: non puoi invocare questa fase senza completare le precedenti
fi
```

### Gate rimossi

| Gate attuale | Destino |
|-------------|---------|
| `tdd-gate` | Assorbito da `impl-gate` |
| `plan-gate` | Assorbito da `impl-gate` (brainstorming check) |
| `pre-commit` | Assorbito da `close-gate` (per commit) + resta per quality gate |
| `stop-gate` | Assorbito da `close-gate` (per claim) + resta per telemetria |
| `sub-skill-gate` | Assorbito da `stage-gate` |
| `pr-gate` | Assorbito da `close-gate` |
| `batch-checkpoint` | Resta invariato (non e' SDLC) |

Nota: `pre-commit` e `stop-gate` non vengono eliminati — la parte quality gate e telemetria resta. Solo la logica "hai invocato skill X?" viene sostituita dalla logica "fase Y completata?".

### post-skill aggiornato

Quando una skill backbone viene invocata, `post-skill` chiama `sdlc_advance_stage`:

```bash
# In post-skill, dopo aver registrato la skill
for entry in "${SDLC_BACKBONE_MAP[@]}"; do
    MAP_SKILL="${entry%%=*}"
    MAP_STAGE="${entry#*=}"
    if [ "$SKILL_NAME" = "$MAP_SKILL" ]; then
        sdlc_advance_stage "$MAP_STAGE"
        break
    fi
done
```

---

## Context Injection Phase-Based

`devforge-reinject` cambia da catalogo completo a:

```
Fase SDLC attuale: execution
Fasi completate: brainstorming, plan
Gate aperti: tdd richiesto prima di modificare codice produzione
Skill specialistiche consigliate in questa fase:
- siae-security
- siae-code-standards
- siae-frontend
```

`session-start` continua a iniettare il catalogo backbone completo (7 skill) + la lista specialist raggruppata per fase.

---

## Nuova Skill: siae-review-gate

Skill backbone per la fase review. Minimale:

1. Verifica che ci siano file modificati (`git diff --stat`)
2. Propone il tipo di review:
   - Blind review → invoca `siae-blind-review`
   - Request review → invoca `siae-requesting-review`
   - Receive review → invoca `siae-receiving-review`
3. Avanza la fase a `review` completata

Frontmatter:
```yaml
---
name: siae-review-gate
description: >
  Orchestra la fase di review: sceglie il tipo di review appropriato
  e avanza la fase SDLC.
triggers:
  - review
  - pronto per review
  - code review
  - chiedi review
type: Rigid
sdlc_phase: "5. Review"
backbone_role: backbone
backbone_stage: review
hard_gate: true
---
```

---

## Frontmatter Schema (tutte le 37+1 skill)

Nuovi campi obbligatori:

```yaml
backbone_role: backbone | specialist | support
backbone_stage: brainstorming | plan | execution | tdd | review | verification | finish | null
hard_gate: true | false
```

`skills-core.js` li legge e li usa per:
- Costruire il catalogo raggruppato per fase
- Determinare quali specialist suggerire in context injection
- Validare coerenza backbone_role / hard_gate

---

## Criteri di accettazione

1. File `.devforge-sdlc-stage` creato da `post-skill` quando prima skill backbone invocata
2. `impl-gate` blocca Edit/Write su codice prod se brainstorming+plan+tdd non completate
3. `close-gate` blocca finish/stop se review+verification non completate
4. `stage-gate` blocca skill backbone se fase precedente non completata
5. Context injection mostra fase corrente + specialist consigliate (non catalogo completo)
6. Tutte le 38 SKILL.md hanno `backbone_role`, `backbone_stage`, `hard_gate` nel frontmatter
7. `siae-review-gate` esiste e orchestra la fase review
8. I gate attuali (tdd-gate, plan-gate, sub-skill-gate) sono sostituiti dai 3 nuovi
9. Zero regressioni sulla test suite
10. `sdlc_check_prerequisites "tdd"` ritorna `missing:brainstorming,plan` se le fasi non sono completate
