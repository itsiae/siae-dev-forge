#!/usr/bin/env bash
# DevForge Telemetry Upload — Outbox Model
# Uploads pending batches from session outbox directories.
# Replaces the old atomic-move single POST with a durable outbox pattern:
#   activity.jsonl → outbox/batch-<ts>.jsonl → upload → outbox/acked/

# Hardcoded endpoint — no dev configuration needed
DEVFORGE_TELEMETRY_ENDPOINT="${DEVFORGE_TELEMETRY_ENDPOINT:-https://5o6tu3hcei.execute-api.eu-west-1.amazonaws.com/v1/logs}"
DEVFORGE_TELEMETRY_KEY="${DEVFORGE_TELEMETRY_KEY:-WhQioTyfb41PcvRrjD7ji6o8xF59quSd3OYvM1sz}"

# Backward compat: honour legacy DEVFORGE_TELEMETRY_URL if set
DEVFORGE_TELEMETRY_ENDPOINT="${DEVFORGE_TELEMETRY_URL:-$DEVFORGE_TELEMETRY_ENDPOINT}"

# --- Outbox functions --------------------------------------------------------

# devforge_create_batch — copies new lines from activity.jsonl into a batch file
# Uses a byte-offset cursor so we never re-send lines already batched.
devforge_create_batch() {
    local session_dir="${DEVFORGE_SESSION_DIR:-}"
    [ -z "$session_dir" ] || [ ! -d "$session_dir" ] && return 0

    local activity="${session_dir}/activity.jsonl"
    [ ! -f "$activity" ] || [ ! -s "$activity" ] && return 0

    # Ensure outbox dir exists
    mkdir -p "${session_dir}/outbox" 2>/dev/null || return 0

    local cursor_file="${session_dir}/outbox/.cursor"
    local cursor
    cursor=$(cat "$cursor_file" 2>/dev/null || echo "0")
    local file_size
    file_size=$(stat -f%z "$activity" 2>/dev/null || stat -c%s "$activity" 2>/dev/null || echo "0")

    # Nothing new to batch
    [ "$file_size" -le "$cursor" ] && return 0

    local batch_file="${session_dir}/outbox/batch-$(date +%s).jsonl"
    tail -c +"$((cursor + 1))" "$activity" > "$batch_file" 2>/dev/null || return 0

    # Only update cursor if batch file was actually written
    if [ -s "$batch_file" ]; then
        echo "$file_size" > "$cursor_file"
    else
        rm -f "$batch_file" 2>/dev/null
    fi
}

# devforge_upload_logs — creates a batch from current session + uploads all pending
devforge_upload_logs() {
    devforge_create_batch 2>/dev/null || true
    devforge_upload_backlog 2>/dev/null || true
}

# devforge_upload_backlog — iterates ALL session dirs and uploads pending batches
devforge_upload_backlog() {
    [ -z "$DEVFORGE_TELEMETRY_ENDPOINT" ] && return 0

    # Never send API key over plain HTTP
    [[ ! "$DEVFORGE_TELEMETRY_ENDPOINT" =~ ^https:// ]] && return 0

    local state_root="${HOME}/.claude/devforge-state"
    [ -d "$state_root" ] || return 0

    for outbox_dir in "$state_root"/*/outbox; do
        [ -d "$outbox_dir" ] || continue
        for batch in "$outbox_dir"/batch-*.jsonl; do
            [ -f "$batch" ] || continue
            local response
            response=$(curl -s -o /dev/null -w "%{http_code}" \
                -X POST "$DEVFORGE_TELEMETRY_ENDPOINT" \
                -H "x-api-key: $DEVFORGE_TELEMETRY_KEY" \
                -H "Content-Type: application/jsonl" \
                --data-binary "@${batch}" \
                --max-time 10 2>/dev/null) || continue

            if [ "$response" = "200" ] || [ "$response" = "201" ]; then
                mkdir -p "${outbox_dir}/acked" 2>/dev/null
                mv "$batch" "${outbox_dir}/acked/" 2>/dev/null || true
            fi
        done
    done
}

# devforge_pending_count — counts un-acked batch files across all sessions
devforge_pending_count() {
    local state_root="${HOME}/.claude/devforge-state"
    [ -d "$state_root" ] || { echo "0"; return; }
    local count=0
    for batch in "$state_root"/*/outbox/batch-*.jsonl; do
        [ -f "$batch" ] && count=$((count + 1))
    done
    echo "$count"
}
