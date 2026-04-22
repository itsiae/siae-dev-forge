# Task 05 — Reset counter in post-skill su siae-brainstorming

**Stato:** [PENDING]
**Stima:** 6 min
**Dipendenze:** Task 03

## Goal

Modificare `hooks/post-skill` per azzerare il counter brainstorming quando l'utente invoca `siae-brainstorming`. Emette anche `brainstorming_invoked_post_gate` con il trigger (nudge/warn/block) per tracciare la conversion rate.

## File coinvolti

- `hooks/post-skill` (MODIFY — aggiungi blocco reset dopo il blocco session-skills)
- `tests/hooks/brainstorming-gate.test.sh` (MODIFY — aggiungi verifica)

## Step 1 — Test RED: verifica integration post-skill

Aggiungi **dopo** scenario 10, **prima** di scenario 4:

```bash
# ─── Scenario 5b: invocazione post-skill di siae-brainstorming resetta counter ───
# Setup: stato con counter=3 (warn level)
rm -f "${HOME}/.claude/.devforge-session-skills"
echo "test-sid-12345|3" > "${HOME}/.claude/.devforge-brainstorm-counter"

# Simula invocazione Skill siae-brainstorming via post-skill hook
SKILL_INPUT='{"tool_name":"Skill","skill":"siae-devforge:siae-brainstorming","name":"siae-devforge:siae-brainstorming"}'
echo "$SKILL_INPUT" | bash "${PLUGIN_ROOT}/hooks/post-skill" >/dev/null 2>&1 || true

# Verifica counter resettato a 0
COUNTER=$(read_counter)
if [ "$COUNTER" != "test-sid-12345|0" ]; then
    echo "FAIL scenario 5b: counter dopo reset = '$COUNTER', atteso 'test-sid-12345|0'"
    exit 1
fi

# Verifica evento brainstorming_invoked_post_gate emesso (conversion tracking)
if [ "$(count_events brainstorming_invoked_post_gate)" = "0" ]; then
    echo "FAIL scenario 5b: brainstorming_invoked_post_gate non emesso"
    exit 1
fi

# Il trigger deve riflettere il livello a cui si trovava (N=3 = warn)
if ! grep -q '"trigger":"warn"' "$DEVFORGE_LOG_FILE"; then
    echo "FAIL scenario 5b: trigger non è 'warn' (counter era 3)"
    grep brainstorming_invoked_post_gate "$DEVFORGE_LOG_FILE"
    exit 1
fi
echo "PASS scenario 5b: post-skill reset counter + emit invoked_post_gate con trigger warn"
```

## Step 2 — Run test, verifica RED

```bash
bash tests/hooks/brainstorming-gate.test.sh 2>&1 | grep -E "PASS|FAIL"
```

Atteso: scenario 5b FAIL.

## Step 3 — Implementazione in `hooks/post-skill`

Leggi `hooks/post-skill` per identificare il blocco esistente delle plan lifecycle events (dove c'è `CLEAN_SKILL_TOKEN`). Aggiungi **dopo** il blocco `if [ "$CLEAN_SKILL_TOKEN" = "siae-writing-plans" ]` chiuso (cerca la chiusura con `fi` seguito da riga vuota prima del blocco TDD state machine):

```bash
    # Reset counter brainstorming-gate su invocazione siae-brainstorming (T05)
    if [ "$CLEAN_SKILL_TOKEN" = "siae-brainstorming" ]; then
        CURRENT_SID=$(devforge_get_sid 2>/dev/null || echo "unknown")
        COUNTER_FILE="${HOME}/.claude/.devforge-brainstorm-counter"
        # Leggi counter corrente per determinare trigger (nudge/warn/block)
        CURRENT_DATA=$(cat "$COUNTER_FILE" 2>/dev/null || echo "")
        CURRENT_N="${CURRENT_DATA##*|}"
        TRIGGER="none"
        case "${CURRENT_N:-0}" in
            1) TRIGGER="nudge" ;;
            2|3) TRIGGER="warn" ;;
            [4-9]|[0-9][0-9]*) TRIGGER="block" ;;
        esac

        # Reset counter atomico
        echo "${CURRENT_SID}|0" > "${COUNTER_FILE}.tmp" && mv "${COUNTER_FILE}.tmp" "$COUNTER_FILE"

        # Emetti conversion event (solo se ci fu un nudge precedente)
        if [ "$TRIGGER" != "none" ]; then
            devforge_log "brainstorming_invoked_post_gate" "success" "{\"trigger\":\"${TRIGGER}\",\"counter_before_reset\":${CURRENT_N:-0}}" || true
        fi
    fi
```

**Posizione esatta (ancora per edit atomico):**

Trova in `hooks/post-skill` questa sequenza esatta (chiusura blocco `siae-writing-plans` + blank line + commento TDD):

```bash
        fi
    fi
fi

# --- TDD State Machine: initialize state when siae-tdd is invoked ---
```

Il nuovo blocco va inserito **tra il primo `fi` (chiusura `if CLEAN_SKILL_TOKEN = siae-writing-plans`) e il commento `# --- TDD State Machine`**. Puoi individuare la riga esatta con:

```bash
grep -n "TDD State Machine: initialize" hooks/post-skill
# dovrebbe trovare 1 sola occorrenza — inserisci il blocco 2 righe PRIMA (dopo il `fi` finale di siae-writing-plans)
```

Verifica post-edit: il blocco di reset è dentro `if [ -n "$SKILL_NAME" ]` MA fuori da `if CLEAN_SKILL_TOKEN = siae-writing-plans`. Se serve indentazione corretta, allineare con `if [ "$CLEAN_SKILL_TOKEN" = "siae-brainstorming" ]` (4 spazi, stesso livello del blocco brainstorming/writing-plans precedente).

## Step 4 — Run test, verifica GREEN

```bash
bash tests/hooks/brainstorming-gate.test.sh 2>&1 | grep -E "PASS|FAIL"
bash tests/hooks/post-skill-plan-events.test.sh 2>&1 | tail -3
```

Atteso: scenario 5b PASS, test plan-events esistente resta verde (7/7).

## Step 5 — Commit

```bash
git add hooks/post-skill tests/hooks/brainstorming-gate.test.sh
git commit -m "feat(hook): reset counter + emit invoked_post_gate su brainstorming [T05]"
```

## Definition of Done

- [ ] Scenario 5b passa (reset counter a SID|0 + emit invoked_post_gate)
- [ ] Trigger derivato da counter N (nudge/warn/block/none)
- [ ] Test post-skill-plan-events esistente resta verde
- [ ] Commit creato
