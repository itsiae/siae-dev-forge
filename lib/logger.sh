#!/usr/bin/env bash
# DevForge Activity Logger
# Appends structured JSONL events to ~/.claude/devforge-activity.jsonl

DEVFORGE_LOG_FILE="${DEVFORGE_LOG_FILE:-${HOME}/.claude/devforge-activity.jsonl}"
DEVFORGE_SID_FILE="${HOME}/.claude/.devforge-session-id"

# Ensure log directory exists
mkdir -p "$(dirname "$DEVFORGE_LOG_FILE")"

# Log rotation: max 50MB, 1 backup
_devforge_check_rotation() {
    local max_bytes=52428800
    if [ -f "$DEVFORGE_LOG_FILE" ]; then
        local file_size
        file_size=$(stat -f%z "$DEVFORGE_LOG_FILE" 2>/dev/null || stat -c%s "$DEVFORGE_LOG_FILE" 2>/dev/null || echo 0)
        if [ "$file_size" -gt "$max_bytes" ] 2>/dev/null; then
            mv "$DEVFORGE_LOG_FILE" "${DEVFORGE_LOG_FILE}.1"
        fi
    fi
}

# Extract git context for cross-session correlation
# Returns: branch|jira_id|project
devforge_get_git_context() {
    local branch jira_id project
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "no-branch")
    project=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")
    # Anchored to branch naming convention (feature|bugfix|hotfix)
    jira_id=$(git branch --show-current 2>/dev/null | grep -oE '(feature|bugfix|hotfix)/[A-Z]+-[0-9]+' | grep -oE '[A-Z]+-[0-9]+' || echo "")
    [ -z "$jira_id" ] && jira_id="null"
    echo "${branch}|${jira_id}|${project}"
}

# Map skill name to SDLC phase for drift detection
devforge_get_sdlc_phase() {
    local skill="$1"
    case "$skill" in
        *onboarding*)          echo "1. Init" ;;
        *brainstorming*)       echo "2. Design" ;;
        *architecture*)        echo "2. Design" ;;
        *git-workflow*)        echo "3. Branching" ;;
        *code-standards*)      echo "4. Implementation" ;;
        *security*)            echo "4. Implementation" ;;
        *iac*)                 echo "4. Implementation" ;;
        *data-engineering*)    echo "4. Implementation" ;;
        *frontend*)            echo "4. Implementation" ;;
        *subagent*)            echo "4. Implementation" ;;
        *tdd*)                 echo "5. Testing" ;;
        *qa*)                  echo "5. Testing / QA" ;;
        *automation*)          echo "5. Testing / Automation" ;;
        *debugging*)           echo "6. QA Gate" ;;
        *documentation*)       echo "7. Release" ;;
        *verification*)        echo "Cross-cutting" ;;
        *writing-skills*)      echo "Meta" ;;
        *)                     echo "unknown" ;;
    esac
}

# Get user identity: repo email → global email → cache → $USER → whoami → unknown
devforge_get_user() {
    local user
    # 1. Repo-local git config
    user=$(git config user.email 2>/dev/null)
    # 2. Global git config
    [ -z "$user" ] && user=$(git config --global user.email 2>/dev/null)
    # 3. Session cache (set by session-start)
    [ -z "$user" ] && [ -f "${HOME}/.claude/.devforge-user" ] && user=$(cat "${HOME}/.claude/.devforge-user" 2>/dev/null)
    # 4. OS user
    [ -z "$user" ] && user="${USER:-$(whoami 2>/dev/null || echo "unknown")}"
    echo "$user"
}

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

# Sanitize a string for safe JSON embedding (escapes \, ", newlines, tabs)
# Usage: devforge_sanitize_json_str "unsafe string"
devforge_sanitize_json_str() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

# Log an event to the JSONL file
# Usage: devforge_log <event_type> <status> [meta_json]
# Example: devforge_log "session_start" "success" '{"project_dir":"/path","plugin_version":"1.0.1"}'
devforge_log() {
    _devforge_check_rotation
    local event="$1"
    local status="${2:-success}"
    local meta="${3-}"
    [ -z "$meta" ] && meta='{}'
    local ts sid git_ctx branch jira_id project jira_json

    ts=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
    sid=$(devforge_get_sid)
    git_ctx=$(devforge_get_git_context)
    branch=$(echo "$git_ctx" | cut -d'|' -f1)
    jira_id=$(echo "$git_ctx" | cut -d'|' -f2)
    project=$(echo "$git_ctx" | cut -d'|' -f3)
    if [ "$jira_id" = "null" ]; then jira_json="null"; else jira_json="\"${jira_id}\""; fi

    local user
    user=$(devforge_get_user)

    # Atomic append — printf avoids echo quoting issues
    printf '{"ts":"%s","user":"%s","sid":"%s","branch":"%s","jira_id":%s,"project":"%s","event":"%s","status":"%s","meta":%s}\n' \
        "$ts" "$user" "$sid" "$branch" "$jira_json" "$project" "$event" "$status" "$meta" >> "$DEVFORGE_LOG_FILE"
}

# Log with duration measurement
# Usage: devforge_log_timed <event_type> <status> <start_time_epoch_ns> [meta_json]
devforge_log_timed() {
    _devforge_check_rotation
    local event="$1"
    local status="${2:-success}"
    local start_ns="$3"
    local meta="${4-}"
    [ -z "$meta" ] && meta='{}'
    local end_ns duration_ms ts sid git_ctx branch jira_id project jira_json

    end_ns=$(date +%s%N 2>/dev/null || echo "0")
    if [ "$start_ns" != "0" ] && [ "$end_ns" != "0" ]; then
        duration_ms=$(( (end_ns - start_ns) / 1000000 ))
    else
        duration_ms=0
    fi

    ts=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
    sid=$(devforge_get_sid)
    git_ctx=$(devforge_get_git_context)
    branch=$(echo "$git_ctx" | cut -d'|' -f1)
    jira_id=$(echo "$git_ctx" | cut -d'|' -f2)
    project=$(echo "$git_ctx" | cut -d'|' -f3)
    if [ "$jira_id" = "null" ]; then jira_json="null"; else jira_json="\"${jira_id}\""; fi

    local user
    user=$(devforge_get_user)

    printf '{"ts":"%s","user":"%s","sid":"%s","branch":"%s","jira_id":%s,"project":"%s","event":"%s","status":"%s","duration_ms":%d,"meta":%s}\n' \
        "$ts" "$user" "$sid" "$branch" "$jira_json" "$project" "$event" "$status" "$duration_ms" "$meta" >> "$DEVFORGE_LOG_FILE"
}

# Set an active mode sentinel in the current working directory
# Usage: devforge_set_mode <mode_name> <context_string>
# Example: devforge_set_mode "tdd" "RED|src/MyService.java|testShouldReturnEmpty"
devforge_set_mode() {
    local mode="$1"
    local context="$2"
    echo "$context" > "$(pwd)/.devforge-active-${mode}"
}

# Clear an active mode sentinel from the current working directory
# Usage: devforge_clear_mode <mode_name>
# Example: devforge_clear_mode "tdd"
devforge_clear_mode() {
    local mode="$1"
    rm -f "$(pwd)/.devforge-active-${mode}"
}
