# Task 5 — Post-commit-review: upload post-evento

**Stato:** [PENDING]
**File coinvolti:** `hooks/post-commit-review` (MODIFICA)
**AC coperti:** AC-4
**Fase:** PR2
**Dipende da:** Task 1, 3

---

## Step 1 — Init session context

All'inizio del blocco commit detection (dopo `source logger.sh`, linea 38), aggiungi:

```bash
    devforge_init_session
```

## Step 2 — Upload post-commit_created

Dopo la chiamata `devforge_log "commit_created"` (o il nuovo blocco con token delta dalla PR1), aggiungi:

```bash
    # Upload telemetry including the commit_created event just written
    source "${PLUGIN_ROOT}/lib/telemetry-upload.sh" 2>/dev/null || true
    devforge_upload_logs &
```

Nota: upload in background (`&`) per non rallentare il hook.

## Step 3 — Verifica

```bash
bash -n hooks/post-commit-review
```
Output atteso: nessun errore.
