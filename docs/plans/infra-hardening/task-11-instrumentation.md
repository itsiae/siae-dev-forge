# Task 11: Strumentazione Mismatch Attivazione (D11)

**Deliverable:** D11
**Dipendenze:** Task 01 (DEVFORGE_STATE_DIR)
**File coinvolti:** `hooks/post-skill`, `hooks/stop-gate`

---

## Step 1 — Aggiungi `message_number` al log di post-skill

In `hooks/post-skill`, nella sezione di logging (dopo Step 2 del file, dove logga `skill_invoked`):

```bash
# Read current message count for late-invocation tracking (D11)
MSG_COUNT=$(cat "${DEVFORGE_STATE_DIR}/.devforge-message-counter" 2>/dev/null || echo "0")
MSG_COUNT=$((MSG_COUNT + 0))  # sanitize to number
```

Aggiorna la chiamata `devforge_log` per includere `message_number`:

```bash
# PRIMA:
devforge_log "$SAFE_SKILL_NAME" "skill_invoked" \
  "{\"skill\":\"$SAFE_SKILL_NAME\"}" 2>/dev/null || true

# DOPO:
devforge_log "$SAFE_SKILL_NAME" "skill_invoked" \
  "{\"skill\":\"$SAFE_SKILL_NAME\",\"message_number\":$MSG_COUNT}" 2>/dev/null || true
```

## Step 2 — Aggiungi late-invocation detection in post-skill

Subito dopo il log `skill_invoked`, aggiungere:

```bash
# D11: Log late invocation (skill invoked after message 5)
LATE_THRESHOLD=5
if [ "$MSG_COUNT" -gt "$LATE_THRESHOLD" ] 2>/dev/null; then
    devforge_log "$SAFE_SKILL_NAME" "skill_late_invocation" \
      "{\"skill\":\"$SAFE_SKILL_NAME\",\"message_number\":$MSG_COUNT,\"threshold\":$LATE_THRESHOLD}" 2>/dev/null || true
fi
```

## Step 3 — Aggiungi summary in stop-gate

In `hooks/stop-gate`, nella sezione di session summary (prima del log `session_ended`):

Leggi il file session-skills e il message counter per calcolare metriche:

```bash
# D11: Session skill invocation summary
SESSION_SKILLS_FILE="${DEVFORGE_STATE_DIR}/.devforge-session-skills"
FINAL_MSG_COUNT=$(cat "${DEVFORGE_STATE_DIR}/.devforge-message-counter" 2>/dev/null || echo "0")

if [ -f "$SESSION_SKILLS_FILE" ]; then
    SKILL_COUNT=$(wc -l < "$SESSION_SKILLS_FILE" | tr -d ' ')
    SKILL_LIST=$(tr '\n' ',' < "$SESSION_SKILLS_FILE" | sed 's/,$//')
    SAFE_SKILL_LIST=$(devforge_sanitize_json_str "$SKILL_LIST")
    devforge_log "session" "skill_summary" \
      "{\"skills_invoked\":$SKILL_COUNT,\"skills\":\"$SAFE_SKILL_LIST\",\"total_messages\":$FINAL_MSG_COUNT}" 2>/dev/null || true
fi
```

## Step 4 — Verifica

```bash
# Simula una sessione con skill invocata tardi
export DEVFORGE_STATE_DIR=$(mktemp -d)
mkdir -p "$DEVFORGE_STATE_DIR"
echo "10" > "$DEVFORGE_STATE_DIR/.devforge-message-counter"
export DEVFORGE_LOG_FILE="/tmp/devforge-test-d11.jsonl"
rm -f "$DEVFORGE_LOG_FILE"

# Invoca post-skill
echo '{"skill":"siae-devforge:siae-brainstorming"}' | \
  bash hooks/post-skill 2>/dev/null

# Verifica che il log contiene skill_late_invocation
grep 'skill_late_invocation' "$DEVFORGE_LOG_FILE"
```
Output atteso: riga JSON con `skill_late_invocation` e `message_number: 10`.

```bash
# Cleanup
rm -rf "$DEVFORGE_STATE_DIR" "$DEVFORGE_LOG_FILE"
```

## Step 5 — Run test suite

```bash
tests/run-all.sh
```
Output atteso: tutti i test passano (le nuove righe di log non impattano i test esistenti).

## Step 6 — Commit

```bash
git add hooks/post-skill hooks/stop-gate
git commit -m "feat(telemetry): add skill invocation timing and late-invocation detection

- post-skill logs message_number with every skill_invoked event
- post-skill emits skill_late_invocation when skill invoked after message 5
- stop-gate emits skill_summary with all skills invoked and total messages

Co-Authored-By: SIAE DevForge"
```
