# Task 4 — Stop-gate: flush + upload finale

**Stato:** [PENDING]
**File coinvolti:** `hooks/stop-gate` (MODIFICA)
**AC coperti:** AC-4, AC-5
**Fase:** PR2
**Dipende da:** Task 1, 2, 3

---

## Step 1 — Init session context in stop-gate

All'inizio dello script (dopo `source logger.sh`, linea 17), aggiungi:

```bash
devforge_init_session
```

## Step 2 — Aggiungi flush + upload dopo session_end

Dopo la chiamata `devforge_log_timed "session_end"` (linea 57), aggiungi:

```bash
    # Flush telemetry: create batch and upload
    source "${PLUGIN_ROOT}/lib/telemetry-upload.sh" 2>/dev/null || true
    devforge_upload_logs 2>/dev/null || true
```

## Step 3 — Verifica

```bash
bash -n hooks/stop-gate
```
Output atteso: nessun errore.
