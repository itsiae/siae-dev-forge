# Task 03 — Counter SID-anchored + 3 livelli (soft/warn/block)

**Stato:** [PENDING]
**Stima:** 15 min
**Dipendenze:** Task 02

## Goal

Implementare counter SID-anchored + 3 livelli: N=1 soft log, N=2-3 warn block, N≥4 hard block. Richiede `DEVFORGE_ENFORCEMENT_STRICT=1` per attivare enforcement (W1 opt-in).

Copre scenari 1, 2, 3, 5 (counter flow), 10 (W1 opt-in), e counter reset su brainstorming invocato in session-skills (fallback, il reset vero è in Task 05).

## File coinvolti

- `tests/hooks/brainstorming-gate.test.sh` (MODIFY)
- `hooks/brainstorming-gate` (MODIFY — sostituisci la riga `# Task 03 aggiunge la logica`)

## Step 1 — Test RED: 5 scenari

Aggiungi **prima** del scenario 6 (deve essere il primo blocco, perché usa hello.ts che è in scope):

```bash
# ─── Scenario 1: N=1 → nudge soft (log + pass) ───
DEVFORGE_ENFORCEMENT_STRICT=1 invoke_gate "${TEST_REPO}/hello.ts"
if [ "$(count_events brainstorming_nudge_soft)" != "1" ]; then
    echo "FAIL scenario 1: nudge_soft count = $(count_events brainstorming_nudge_soft), atteso 1"
    cat "$DEVFORGE_LOG_FILE"
    exit 1
fi
COUNTER=$(read_counter)
if [ "$COUNTER" != "test-sid-12345|1" ]; then
    echo "FAIL scenario 1: counter = '$COUNTER', atteso 'test-sid-12345|1'"
    exit 1
fi
echo "PASS scenario 1: N=1 nudge_soft + counter SID|1"

# ─── Scenario 2: N=2 → warn block (decision:block nel JSON output) ───
OUT=$(DEVFORGE_ENFORCEMENT_STRICT=1 invoke_gate "${TEST_REPO}/hello.ts")
if [ "$(count_events brainstorming_gate_warn)" != "1" ]; then
    echo "FAIL scenario 2: gate_warn count != 1"
    exit 1
fi
if ! echo "$OUT" | grep -q '"decision":"block"'; then
    echo "FAIL scenario 2: no decision:block nel output (N=2 deve bloccare)"
    echo "OUT: $OUT"
    exit 1
fi
COUNTER=$(read_counter)
if [ "$COUNTER" != "test-sid-12345|2" ]; then
    echo "FAIL scenario 2: counter = '$COUNTER', atteso 'test-sid-12345|2'"
    exit 1
fi
echo "PASS scenario 2: N=2 warn + decision:block + counter=2"

# ─── Scenario 3: N=4 → hard block ───
DEVFORGE_ENFORCEMENT_STRICT=1 invoke_gate "${TEST_REPO}/hello.ts" >/dev/null  # N=3
OUT=$(DEVFORGE_ENFORCEMENT_STRICT=1 invoke_gate "${TEST_REPO}/hello.ts")       # N=4
if [ "$(count_events brainstorming_gate_blocked)" != "1" ]; then
    echo "FAIL scenario 3: gate_blocked count != 1"
    exit 1
fi
if ! echo "$OUT" | grep -q '"decision":"block"'; then
    echo "FAIL scenario 3: N=4 deve hard block"
    exit 1
fi
if ! echo "$OUT" | grep -qi "BLOCCATO"; then
    echo "FAIL scenario 3: messaggio non contiene 'BLOCCATO'"
    exit 1
fi
echo "PASS scenario 3: N=4 hard block + BLOCCATO message"

# ─── Scenario 5: siae-brainstorming in session-skills → reset counter ───
set_session_skill "siae-brainstorming"
# forzare reset (simula quello che farebbe post-skill)
echo "test-sid-12345|0" > "${HOME}/.claude/.devforge-brainstorm-counter"
DEVFORGE_ENFORCEMENT_STRICT=1 invoke_gate "${TEST_REPO}/hello.ts"
COUNTER=$(read_counter)
# Con brainstorming invocato, il gate deve saltare completamente (no increment, no log)
# Fix: il gate deve rispettare session-skills come short-circuit
if echo "$COUNTER" | grep -qE "\|[2-9]|\|[1-9][0-9]"; then
    echo "FAIL scenario 5: counter incrementato nonostante siae-brainstorming presente ($COUNTER)"
    exit 1
fi
echo "PASS scenario 5: siae-brainstorming presente → no enforcement"
rm -f "${HOME}/.claude/.devforge-session-skills"

# ─── Scenario 10: W1 mode senza DEVFORGE_ENFORCEMENT_STRICT → solo log soft, no block ───
rm -f "${HOME}/.claude/.devforge-brainstorm-counter"
# Reset log: count_events conta da inizio, verifichiamo solo che NON ci sia nuovo "blocked"
BLOCKED_BEFORE=$(count_events brainstorming_gate_blocked)
invoke_gate "${TEST_REPO}/hello.ts"  # senza STRICT=1
BLOCKED_AFTER=$(count_events brainstorming_gate_blocked)
if [ "$BLOCKED_BEFORE" != "$BLOCKED_AFTER" ]; then
    echo "FAIL scenario 10: blocked aumentato senza STRICT"
    exit 1
fi
echo "PASS scenario 10: senza STRICT → no enforcement (W1 opt-in rispettato)"
```

## Step 2 — Run test, verifica RED

```bash
bash tests/hooks/brainstorming-gate.test.sh 2>&1 | grep -E "PASS|FAIL"
```

Atteso: scenari 1, 2, 3 FAIL perché logica non implementata.

## Step 3 — Implementazione hook

Sostituisci la riga `# Scope filter passato — da qui in avanti Task 03 aggiunge la logica` in `hooks/brainstorming-gate` e il `echo '{}'; exit 0` subito dopo con:

```bash
# Source logger (fornisce devforge_get_sid, devforge_log, devforge_sanitize_json_str)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${PLUGIN_ROOT}/lib/logger.sh" 2>/dev/null || true
devforge_init_session 2>/dev/null || true

# Short-circuit: siae-brainstorming già invocato in session-skills
SESSION_SKILLS_FILE="${HOME}/.claude/.devforge-session-skills"
if [ -f "$SESSION_SKILLS_FILE" ] && grep -qF "siae-brainstorming" "$SESSION_SKILLS_FILE" 2>/dev/null; then
    echo '{}'
    exit 0
fi

# Rollout mode check:
#   W1 (opt-in): richiede DEVFORGE_ENFORCEMENT_STRICT=1
#   W2+ (default on): enforcement attivo sempre (tranne ENFORCEMENT_OFF già gestito)
# Deploy W2 = setta DEVFORGE_W2_DEFAULT=1 nel hook direttamente (post-retrospective W1)
W2_DEFAULT="${DEVFORGE_W2_DEFAULT:-0}"
if [ "$W2_DEFAULT" != "1" ] && [ "${DEVFORGE_ENFORCEMENT_STRICT:-0}" != "1" ]; then
    echo '{}'
    exit 0
fi

# Counter SID-anchored
CURRENT_SID=$(devforge_get_sid 2>/dev/null || echo "unknown")
COUNTER_FILE="${HOME}/.claude/.devforge-brainstorm-counter"
CURRENT_DATA=$(cat "$COUNTER_FILE" 2>/dev/null || echo "")
STORED_SID="${CURRENT_DATA%%|*}"
STORED_N="${CURRENT_DATA##*|}"
# Se SID diverso o file assente → reset a 0
if [ "$STORED_SID" != "$CURRENT_SID" ] || [ -z "$STORED_N" ]; then
    STORED_N=0
fi

NEW_N=$((STORED_N + 1))

# Atomic write counter
echo "${CURRENT_SID}|${NEW_N}" > "${COUNTER_FILE}.tmp" && mv "${COUNTER_FILE}.tmp" "$COUNTER_FILE"

# Sanitize file_path per JSON
SAFE_FILE_PATH=$(devforge_sanitize_json_str "$FILE_PATH")
BASENAME=$(basename "$FILE_PATH")

# 3 livelli escalation
if [ "$NEW_N" -eq 1 ]; then
    devforge_log "brainstorming_nudge_soft" "success" "{\"file_path\":\"${SAFE_FILE_PATH}\",\"counter\":1}"
    echo '{}'
    exit 0
elif [ "$NEW_N" -le 3 ]; then
    devforge_log "brainstorming_gate_warn" "success" "{\"file_path\":\"${SAFE_FILE_PATH}\",\"counter\":${NEW_N}}"
    cat <<EOF_WARN
{
  "decision": "block",
  "reason": "DevForge Brainstorming Nudge — ${NEW_N}° edit senza design. Hai modificato ${BASENAME} senza invocare siae-brainstorming. I dati mostrano che skippare il design costa 3-5x rework. Opzioni: (1) Invoca Skill siae-devforge:siae-brainstorming ora (raccomandato), (2) Continua senza — prossimo warn al 3°, hard block al 4°, (3) Fix triviale? Usa: DEVFORGE_SKIP_BRAINSTORMING=1 <comando>."
}
EOF_WARN
    exit 0
else
    # N >= 4 hard block
    devforge_log "brainstorming_gate_blocked" "blocked" "{\"file_path\":\"${SAFE_FILE_PATH}\",\"counter\":${NEW_N},\"violation\":\"no_brainstorm\"}"
    cat <<EOF_BLOCK
{
  "decision": "block",
  "reason": "DevForge Brainstorming Gate — BLOCCATO. ${NEW_N} edit su codice produzione senza siae-brainstorming in questa sessione. Legge di Ferro SIAE: nessuna implementazione senza design approvato. Sblocca: Skill tool -> siae-devforge:siae-brainstorming (raccomandato). Bypass emergenza (tracciato): DEVFORGE_SKIP_BRAINSTORMING=1 <comando successivo>. Se questo gate è inappropriato per il tuo task, segnalalo a #devforge-support."
}
EOF_BLOCK
    exit 0
fi
```

## Step 4 — Run test, verifica GREEN

```bash
bash tests/hooks/brainstorming-gate.test.sh 2>&1 | grep -E "PASS|FAIL"
```

Atteso: scenari 1, 2, 3, 5, 10 + già verdi 6-9 → 9 PASS.

## Step 5 — Commit

```bash
git add hooks/brainstorming-gate tests/hooks/brainstorming-gate.test.sh
git commit -m "feat(hook): counter SID-anchored + 3 livelli enforcement [T03]"
```

## Definition of Done

- [ ] Scenari 1, 2, 3, 5, 10 passano
- [ ] Counter file schema `SID|N` rispettato
- [ ] W1 opt-in: enforcement attivo SOLO con `DEVFORGE_ENFORCEMENT_STRICT=1`
- [ ] Short-circuit su siae-brainstorming in session-skills
- [ ] 3 eventi emessi (`brainstorming_nudge_soft`, `_warn`, `_blocked`)
- [ ] Commit creato
