# Task 6 — Context + statusline: read da session dir

**Stato:** [PENDING]
**File coinvolti:** `hooks/devforge-context-always` (MODIFICA), `statusline/devforge-statusline.sh` (MODIFICA)
**AC coperti:** AC-1
**Fase:** PR2
**Dipende da:** Task 1, 2

---

## Step 1 — devforge-context-always: init session + read counters

All'inizio dello script (dopo PLUGIN_ROOT, linea 16), aggiungi:

```bash
source "${PLUGIN_ROOT}/lib/logger.sh" 2>/dev/null || true
devforge_init_session 2>/dev/null || true
```

Nella sezione Session Stats (linea 74+), leggi counters dalla dir sessione dove disponibili:

```bash
# Prefer session dir counters, fallback to global files
if [ -n "$DEVFORGE_SESSION_DIR" ] && [ -d "$DEVFORGE_SESSION_DIR" ]; then
    COMMITS=$(cat "${DEVFORGE_SESSION_DIR}/commits" 2>/dev/null || cat "${STATE_DIR}/.devforge-session-commits" 2>/dev/null || echo "0")
else
    COMMITS=$(cat "${STATE_DIR}/.devforge-session-commits" 2>/dev/null || echo "0")
fi
```

## Step 2 — Statusline: telemetry status indicator

In `statusline/devforge-statusline.sh`, nella sezione 3 (lettura state), aggiungi:

```bash
# Telemetry status
TELEMETRY_STATUS=""
if command -v bash >/dev/null 2>&1; then
    PLUGIN_ROOT_SL=$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd)
    if [ -f "${PLUGIN_ROOT_SL}/lib/telemetry-upload.sh" ]; then
        source "${PLUGIN_ROOT_SL}/lib/telemetry-upload.sh" 2>/dev/null || true
        PENDING=$(devforge_pending_count 2>/dev/null || echo "0")
        if [ "$PENDING" -gt 0 ] 2>/dev/null; then
            TELEMETRY_STATUS="pending:${PENDING}"
        else
            TELEMETRY_STATUS="ok"
        fi
    fi
fi
```

In LINE2, dopo il context bar, aggiungi:

```bash
if [ -n "$TELEMETRY_STATUS" ] && [ "$TELEMETRY_STATUS" != "ok" ]; then
    LINE2="${LINE2} | ${YELLOW}telem=${TELEMETRY_STATUS}${RESET}"
fi
```

## Step 3 — Verifica

```bash
bash -n hooks/devforge-context-always
bash -n statusline/devforge-statusline.sh
```
Output atteso: nessun errore.
