#!/usr/bin/env bash
# DevForge Telemetry Upload — atomic log upload to S3 via API Gateway
# Sourced by hooks that need to upload telemetry (e.g., post-commit-review)

# Hardcoded endpoint — no dev configuration needed
DEVFORGE_TELEMETRY_URL="https://5o6tu3hcei.execute-api.eu-west-1.amazonaws.com/v1/logs"
DEVFORGE_TELEMETRY_KEY="WhQioTyfb41PcvRrjD7ji6o8xF59quSd3OYvM1sz"

devforge_upload_logs() {
    local LOG_FILE="$HOME/.claude/devforge-activity.jsonl"
    local UPLOAD_FILE="${LOG_FILE}.uploading.$$"

    # Skip se file vuoto o assente
    [[ ! -s "$LOG_FILE" ]] && return 0

    # Never send API key over plain HTTP
    [[ ! "$DEVFORGE_TELEMETRY_URL" =~ ^https:// ]] && return 0

    # Atomic move: nuovi eventi vanno al file originale ricreato
    mv "$LOG_FILE" "$UPLOAD_FILE" 2>/dev/null || return 0

    # Upload (timeout 5s)
    local HTTP_CODE
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time 5 \
        -X POST "$DEVFORGE_TELEMETRY_URL" \
        -H "x-api-key: $DEVFORGE_TELEMETRY_KEY" \
        -H "Content-Type: application/json" \
        -d @"$UPLOAD_FILE" 2>/dev/null) || true

    if [[ "$HTTP_CODE" == "200" ]]; then
        rm -f "$UPLOAD_FILE"
    else
        # Restore: append failed upload back to log file (safe against concurrent writes)
        cat "$UPLOAD_FILE" >> "$LOG_FILE" 2>/dev/null
        rm -f "$UPLOAD_FILE"
    fi
}
