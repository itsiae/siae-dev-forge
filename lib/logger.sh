#!/usr/bin/env bash
# DevForge Activity Logger
# Appends structured JSONL events to ~/.claude/devforge-activity.jsonl

DEVFORGE_LOG_FILE="${HOME}/.claude/devforge-activity.jsonl"
DEVFORGE_SID_FILE="${HOME}/.claude/.devforge-session-id"

# Ensure log directory exists
mkdir -p "$(dirname "$DEVFORGE_LOG_FILE")"

# Get or generate session ID
devforge_get_sid() {
    if [ -f "$DEVFORGE_SID_FILE" ]; then
        cat "$DEVFORGE_SID_FILE"
    else
        echo "no-session"
    fi
}

# Generate a new session ID and persist it
devforge_new_sid() {
    local sid
    sid=$(date +%s%N | md5sum 2>/dev/null | head -c 8 || date +%s | shasum | head -c 8)
    echo "$sid" > "$DEVFORGE_SID_FILE"
    echo "$sid"
}

# Log an event to the JSONL file
# Usage: devforge_log <event_type> <status> [meta_json]
# Example: devforge_log "session_start" "success" '{"project_dir":"/path","plugin_version":"1.0.1"}'
devforge_log() {
    local event="$1"
    local status="${2:-success}"
    local meta="${3-}"
    [ -z "$meta" ] && meta='{}'
    local ts sid

    ts=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
    sid=$(devforge_get_sid)

    # Atomic append — printf avoids echo quoting issues
    printf '{"ts":"%s","sid":"%s","event":"%s","status":"%s","meta":%s}\n' \
        "$ts" "$sid" "$event" "$status" "$meta" >> "$DEVFORGE_LOG_FILE"
}

# Log with duration measurement
# Usage: devforge_log_timed <event_type> <status> <start_time_epoch_ns> [meta_json]
devforge_log_timed() {
    local event="$1"
    local status="${2:-success}"
    local start_ns="$3"
    local meta="${4-}"
    [ -z "$meta" ] && meta='{}'
    local end_ns duration_ms ts sid

    end_ns=$(date +%s%N 2>/dev/null || echo "0")
    if [ "$start_ns" != "0" ] && [ "$end_ns" != "0" ]; then
        duration_ms=$(( (end_ns - start_ns) / 1000000 ))
    else
        duration_ms=0
    fi

    ts=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
    sid=$(devforge_get_sid)

    printf '{"ts":"%s","sid":"%s","event":"%s","status":"%s","duration_ms":%d,"meta":%s}\n' \
        "$ts" "$sid" "$event" "$status" "$duration_ms" "$meta" >> "$DEVFORGE_LOG_FILE"
}
