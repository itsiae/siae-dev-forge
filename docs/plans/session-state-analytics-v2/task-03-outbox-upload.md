# Task 3 — Telemetry upload: outbox model

**Stato:** [PENDING]
**File coinvolti:** `lib/telemetry-upload.sh` (MODIFICA)
**AC coperti:** AC-4, AC-5, AC-6
**Fase:** PR2
**Dipende da:** Task 1

---

## Step 1 — Riscrittura outbox-based upload

Riscrivere `lib/telemetry-upload.sh` con il modello outbox:

```bash
#!/usr/bin/env bash
# DevForge Telemetry Upload — Outbox Model
# Uploads pending batches from session outbox directories.

DEVFORGE_TELEMETRY_ENDPOINT="${DEVFORGE_TELEMETRY_ENDPOINT:-https://REDACTED}"
DEVFORGE_TELEMETRY_KEY="${DEVFORGE_TELEMETRY_KEY:-REDACTED}"

# Create a batch from the current session's activity.jsonl
# Copies new lines (since last batch) into outbox/batch-<ts>.jsonl
devforge_create_batch() {
    local session_dir="${DEVFORGE_SESSION_DIR:-}"
    [ -z "$session_dir" ] || [ ! -d "$session_dir" ] && return 0
    
    local activity="${session_dir}/activity.jsonl"
    [ ! -f "$activity" ] || [ ! -s "$activity" ] && return 0
    
    local cursor_file="${session_dir}/outbox/.cursor"
    local cursor=$(cat "$cursor_file" 2>/dev/null || echo "0")
    local file_size=$(stat -f%z "$activity" 2>/dev/null || stat -c%s "$activity" 2>/dev/null || echo "0")
    
    [ "$file_size" -le "$cursor" ] && return 0
    
    local batch_file="${session_dir}/outbox/batch-$(date +%s).jsonl"
    tail -c +"$((cursor + 1))" "$activity" > "$batch_file" 2>/dev/null || return 0
    echo "$file_size" > "$cursor_file"
}

# Upload all pending batches (current session + backlog from old sessions)
devforge_upload_logs() {
    devforge_create_batch 2>/dev/null || true
    devforge_upload_backlog 2>/dev/null || true
}

# Upload pending batches from ALL session outbox directories
devforge_upload_backlog() {
    local state_root="${HOME}/.claude/devforge-state"
    [ -d "$state_root" ] || return 0
    
    for outbox_dir in "$state_root"/*/outbox; do
        [ -d "$outbox_dir" ] || continue
        for batch in "$outbox_dir"/batch-*.jsonl; do
            [ -f "$batch" ] || continue
            # Try upload
            local response
            response=$(curl -s -o /dev/null -w "%{http_code}" \
                -X POST "$DEVFORGE_TELEMETRY_ENDPOINT" \
                -H "x-api-key: $DEVFORGE_TELEMETRY_KEY" \
                -H "Content-Type: application/jsonl" \
                --data-binary "@${batch}" \
                --max-time 10 2>/dev/null) || continue
            
            if [ "$response" = "200" ] || [ "$response" = "201" ]; then
                # Acked — move to acked/
                mkdir -p "${outbox_dir}/acked" 2>/dev/null
                mv "$batch" "${outbox_dir}/acked/" 2>/dev/null || true
            fi
            # If not 200, batch stays in outbox/ for retry
        done
    done
}

# Count pending (non-acked) batches across all sessions
devforge_pending_count() {
    local state_root="${HOME}/.claude/devforge-state"
    [ -d "$state_root" ] || { echo "0"; return; }
    find "$state_root" -path '*/outbox/batch-*.jsonl' 2>/dev/null | grep -cv '/acked/' || echo "0"
}
```

## Step 2 — Verifica

```bash
bash -n lib/telemetry-upload.sh
source lib/telemetry-upload.sh
type devforge_create_batch
type devforge_upload_logs
type devforge_upload_backlog
type devforge_pending_count
```
Output atteso: tutte le funzioni definite, nessun errore di sintassi.
