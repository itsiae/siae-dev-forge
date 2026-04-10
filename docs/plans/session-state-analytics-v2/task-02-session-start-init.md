# Task 2 — Session-start: init dir sessione + cleanup

**Stato:** [PENDING]
**File coinvolti:** `hooks/session-start` (MODIFICA)
**AC coperti:** AC-1, AC-3, AC-4, AC-7
**Fase:** PR2
**Dipende da:** Task 1

---

## Step 1 — Crea la directory di sessione e user.json

Dopo `DEVFORGE_SID=$(devforge_new_sid)` (linea 20), aggiungi:

```bash
# Create session state directory
DEVFORGE_SESSION_DIR="${HOME}/.claude/devforge-state/${DEVFORGE_SID}"
mkdir -p "${DEVFORGE_SESSION_DIR}/outbox/acked"

# Pin user identity for this session
USER_RAW=$(devforge_get_user)
USER_SOURCE="unknown"
if git config user.email >/dev/null 2>&1; then
    USER_SOURCE="git-config-local"
elif git config --global user.email >/dev/null 2>&1; then
    USER_SOURCE="git-config-global"
elif [ -f "${HOME}/.claude/.devforge-user" ]; then
    USER_SOURCE="session-cache"
else
    USER_SOURCE="os-user"
fi

# Write user.json (pinned for entire session)
if command -v python3 >/dev/null 2>&1; then
    python3 -c "
import json,sys
json.dump({'raw': sys.argv[1], 'source': sys.argv[2], 'canonical': sys.argv[1]}, open(sys.argv[3], 'w'))
" "$USER_RAW" "$USER_SOURCE" "${DEVFORGE_SESSION_DIR}/user.json" 2>/dev/null || true
fi

# Initialize seq counter
echo "0" > "${DEVFORGE_SESSION_DIR}/seq"

# Initialize session context in logger
export DEVFORGE_SESSION_DIR DEVFORGE_PINNED_USER="$USER_RAW" DEVFORGE_PINNED_SID="$DEVFORGE_SID"
```

## Step 2 — Aggiungi upload backlog all'inizio

Dopo l'init della sessione, prima del brand banner (linea 33):

```bash
# Upload backlog from previous sessions (pending outbox batches)
source "${PLUGIN_ROOT}/lib/telemetry-upload.sh" 2>/dev/null || true
devforge_upload_backlog 2>/dev/null || true
```

## Step 3 — Aggiungi cleanup sessioni vecchie

Dopo il blocco stale sentinel cleanup (dopo `shopt -u nullglob`), aggiungi:

```bash
# Cleanup session state directories older than 48h (preserve pending outbox)
if [ -d "${HOME}/.claude/devforge-state" ]; then
    for session_dir in "${HOME}/.claude/devforge-state"/*/; do
        [ -d "$session_dir" ] || continue
        DIR_MTIME=$(stat -f%m "$session_dir" 2>/dev/null || stat -c%Y "$session_dir" 2>/dev/null || echo "0")
        DIR_AGE=$(( $(date +%s) - DIR_MTIME ))
        [ "$DIR_AGE" -lt 172800 ] && continue
        PENDING_COUNT=$(find "$session_dir/outbox" -maxdepth 1 -name '*.jsonl' 2>/dev/null | grep -cv '/acked/' || echo "0")
        if [ "$PENDING_COUNT" -gt 0 ]; then
            continue
        fi
        rm -rf "$session_dir"
    done
fi
```

## Step 4 — Verifica

```bash
bash -n hooks/session-start
```
Output atteso: nessun errore.

```bash
ls -la ~/.claude/devforge-state/
```
Output atteso: directory con sid della sessione corrente, contenente `outbox/acked/`, `user.json`, `seq`.
