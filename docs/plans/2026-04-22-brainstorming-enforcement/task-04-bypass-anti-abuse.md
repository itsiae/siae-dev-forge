# Task 04 — Bypass env var + daily anti-abuse counter

**Stato:** [PENDING]
**Stima:** 10 min
**Dipendenze:** Task 03

## Goal

Implementare bypass `DEVFORGE_SKIP_BRAINSTORMING=1` + counter giornaliero con evento `brainstorming_bypass_abuse_suspected` se count > 5/giorno.

Copre scenari 4 (bypass singolo) + 11 (abuse detection > 5/giorno) + 12 (race condition counter atomic).

## File coinvolti

- `tests/hooks/brainstorming-gate.test.sh` (MODIFY)
- `hooks/brainstorming-gate` (MODIFY — aggiungi check bypass prima del counter N)

## Step 1 — Test RED: 3 scenari

Aggiungi **dopo** scenario 10, **prima** di scenario 6:

```bash
# ─── Scenario 4: DEVFORGE_SKIP_BRAINSTORMING=1 → bypass + log ───
rm -f "${HOME}/.claude/.devforge-brainstorm-counter" "${HOME}/.claude/.devforge-bypass-count"
BYPASS_BEFORE=$(count_events brainstorming_gate_bypassed)
DEVFORGE_ENFORCEMENT_STRICT=1 DEVFORGE_SKIP_BRAINSTORMING=1 invoke_gate "${TEST_REPO}/hello.ts"
BYPASS_AFTER=$(count_events brainstorming_gate_bypassed)
if [ $((BYPASS_AFTER - BYPASS_BEFORE)) != "1" ]; then
    echo "FAIL scenario 4: bypass event non emesso"
    exit 1
fi
# Counter principale deve NON incrementare su bypass
COUNTER=$(read_counter)
if echo "$COUNTER" | grep -qE "\|[1-9]"; then
    echo "FAIL scenario 4: counter incrementato su bypass ($COUNTER)"
    exit 1
fi
echo "PASS scenario 4: bypass emette gate_bypassed + no counter increment"

# ─── Scenario 11: anti-abuse — 6+ bypass nello stesso giorno → abuse_suspected ───
# Lo scenario 4 ha già emesso 1 bypass. Facciamone altri 5 per arrivare a 6.
for i in 2 3 4 5 6; do
    DEVFORGE_ENFORCEMENT_STRICT=1 DEVFORGE_SKIP_BRAINSTORMING=1 invoke_gate "${TEST_REPO}/hello.ts"
done
ABUSE_COUNT=$(count_events brainstorming_bypass_abuse_suspected)
if [ "$ABUSE_COUNT" = "0" ]; then
    echo "FAIL scenario 11: nessun abuse_suspected emesso (atteso >=1 con 6 bypass)"
    cat "${HOME}/.claude/.devforge-bypass-count"
    exit 1
fi
echo "PASS scenario 11: abuse_suspected emesso dopo 6 bypass nello stesso giorno"

# ─── Scenario 12: bypass file format YYYY-MM-DD|count corretto ───
BYPASS_FILE="${HOME}/.claude/.devforge-bypass-count"
if [ ! -f "$BYPASS_FILE" ]; then
    echo "FAIL scenario 12: bypass file non creato"
    exit 1
fi
CONTENT=$(cat "$BYPASS_FILE")
TODAY=$(date -u +%Y-%m-%d)
if ! echo "$CONTENT" | grep -qE "^${TODAY}\|[0-9]+$"; then
    echo "FAIL scenario 12: bypass file format errato: '$CONTENT' (atteso '${TODAY}|N')"
    exit 1
fi
echo "PASS scenario 12: bypass file format YYYY-MM-DD|count"
```

## Step 2 — Run test, verifica RED

```bash
bash tests/hooks/brainstorming-gate.test.sh 2>&1 | grep -E "PASS|FAIL"
```

Atteso: scenari 4, 11, 12 FAIL.

## Step 3 — Implementazione

In `hooks/brainstorming-gate`, **dopo** il blocco del W1/W2 mode check e **prima** del counter SID, aggiungi:

```bash
# Bypass esplicito via env var (pattern git --no-verify)
if [ "${DEVFORGE_SKIP_BRAINSTORMING:-0}" = "1" ]; then
    SAFE_FILE_PATH=$(devforge_sanitize_json_str "$FILE_PATH")

    # Daily bypass counter anti-abuse: schema YYYY-MM-DD|count
    BYPASS_FILE="${HOME}/.claude/.devforge-bypass-count"
    TODAY=$(date -u +%Y-%m-%d)
    BYPASS_DATA=$(cat "$BYPASS_FILE" 2>/dev/null || echo "")
    BYPASS_DATE="${BYPASS_DATA%%|*}"
    BYPASS_COUNT="${BYPASS_DATA##*|}"

    if [ "$BYPASS_DATE" != "$TODAY" ] || [ -z "$BYPASS_COUNT" ]; then
        BYPASS_COUNT=0
    fi
    NEW_BYPASS_COUNT=$((BYPASS_COUNT + 1))
    echo "${TODAY}|${NEW_BYPASS_COUNT}" > "${BYPASS_FILE}.tmp" && mv "${BYPASS_FILE}.tmp" "$BYPASS_FILE"

    devforge_log "brainstorming_gate_bypassed" "success" "{\"file_path\":\"${SAFE_FILE_PATH}\",\"reason\":\"env_var\",\"bypass_count_today\":${NEW_BYPASS_COUNT}}"

    # Soglia anti-abuse: > 5/giorno emit abuse_suspected
    if [ "$NEW_BYPASS_COUNT" -gt 5 ]; then
        PATTERN="frequent_bypass"
        if [ "$NEW_BYPASS_COUNT" -ge 10 ]; then
            PATTERN="always_on"
        fi
        devforge_log "brainstorming_bypass_abuse_suspected" "warning" "{\"count_today\":${NEW_BYPASS_COUNT},\"estimated_pattern\":\"${PATTERN}\"}"
    fi

    echo '{}'
    exit 0
fi
```

## Step 4 — Run test, verifica GREEN

```bash
bash tests/hooks/brainstorming-gate.test.sh 2>&1 | grep -E "PASS|FAIL"
```

Atteso: scenari 4, 11, 12 PASS. Scenari precedenti restano verdi (12/12 totali).

## Step 5 — Commit

```bash
git add hooks/brainstorming-gate tests/hooks/brainstorming-gate.test.sh
git commit -m "feat(hook): bypass env var + daily anti-abuse counter [T04]"
```

## Definition of Done

- [ ] Scenari 4, 11, 12 passano
- [ ] `DEVFORGE_SKIP_BRAINSTORMING=1` emette `brainstorming_gate_bypassed`
- [ ] Counter bypass giornaliero formato `YYYY-MM-DD|N`
- [ ] Soglia > 5/giorno → `brainstorming_bypass_abuse_suspected` con pattern
- [ ] Contatore principale NON incrementato su bypass
- [ ] Commit creato
