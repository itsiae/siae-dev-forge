# Task 7 — Patch stop-gate hook per retrospective

**Stato:** [PENDING]
**Dipendenze:** Task 6 (siae-retrospective deve esistere)
**File coinvolti:**
- `hooks/stop-gate`

---

## Step 1 — Aggiungi check retrospective

Apri `hooks/stop-gate`.
Trova il blocco dopo il check verification (riga ~129):

```bash
if echo "$SESSION_SKILLS_CHECK" | grep -qF "siae-verification"; then
    # Verification was invoked — allow stop
    exit 0
fi
```

Modifica questo blocco per richiedere ANCHE siae-retrospective per sessioni produttive
(almeno 1 commit). Il nuovo blocco diventa:

```bash
if echo "$SESSION_SKILLS_CHECK" | grep -qF "siae-verification"; then
    # Verification was invoked — check retrospective for productive sessions
    if [ "$COMMITS_COUNT" -gt 0 ] && ! echo "$SESSION_SKILLS_CHECK" | grep -qF "siae-retrospective"; then
        # Productive session without retrospective — soft reminder (non-blocking)
        devforge_log "stop_gate" "reminder" "{\"reason\":\"retrospective_skipped\",\"commits\":${COMMITS_COUNT}}"
        cat <<RETRO_EOF
{
  "decision": "block",
  "reason": "DevForge Retrospective Reminder — Hai ${COMMITS_COUNT} commit in questa sessione ma non hai eseguito siae-retrospective. Le lezioni non salvate sono lezioni perse. Invoca siae-retrospective per estrarre e persistere le lezioni apprese, poi potrai fermarti. (Tentativo 1/1 — al prossimo tentativo lo stop verra' permesso)"
}
RETRO_EOF
        # Mark as reminded so next attempt passes
        RETRO_REMINDED_FILE="${HOME}/.claude/.devforge-retro-reminded"
        if [ -f "$RETRO_REMINDED_FILE" ]; then
            rm -f "$RETRO_REMINDED_FILE"
            exit 0
        fi
        touch "$RETRO_REMINDED_FILE"
        exit 0
    fi
    # All checks passed
    rm -f "${HOME}/.claude/.devforge-retro-reminded" 2>/dev/null
    exit 0
fi
```

## Step 2 — Cleanup nel session-start

Apri `hooks/session-start`. Aggiungi cleanup del file di reminder all'inizio
della sessione, nella sezione dove vengono puliti gli altri file di stato:

```bash
rm -f "${HOME}/.claude/.devforge-retro-reminded" 2>/dev/null
```

## Step 3 — Verifica

```bash
grep -c "siae-retrospective" hooks/stop-gate
grep "retro-reminded" hooks/stop-gate
```
Output atteso: almeno 2 occorrenze di `siae-retrospective`, e la riga `retro-reminded`.

## Step 4 — Commit

```bash
git add hooks/stop-gate hooks/session-start
git commit -m "feat(hooks): add retrospective reminder to stop-gate (#864)"
```
