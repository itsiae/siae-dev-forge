#!/usr/bin/env bash
# DevForge Activity Logger
# Appends structured JSONL events to ~/.claude/devforge-activity.jsonl

DEVFORGE_LOG_FILE="${DEVFORGE_LOG_FILE:-${HOME}/.claude/devforge-activity.jsonl}"
DEVFORGE_SID_FILE="${HOME}/.claude/.devforge-session-id"
DEVFORGE_SESSION_USER_FILE="${HOME}/.claude/.devforge-session-user"
DEVFORGE_SESSION_USER_SOURCE_FILE="${HOME}/.claude/.devforge-session-user-source"

# Per-session state isolation & identity pinning
DEVFORGE_SESSION_DIR=""
DEVFORGE_PINNED_USER=""
DEVFORGE_PINNED_SID=""

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

# Normalize the user identifier so analytics do not split on case or GitHub numeric prefixes.
devforge_canonicalize_user() {
    local raw="${1:-}"
    raw=$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')
    raw="${raw#"${raw%%[![:space:]]*}"}"
    raw="${raw%"${raw##*[![:space:]]}"}"

    if [ -z "$raw" ]; then
        echo "unknown"
        return
    fi

    if [[ "$raw" =~ ^[0-9]+\+([^@]+)@users\.noreply\.github\.com$ ]]; then
        echo "${BASH_REMATCH[1]}"
        return
    fi

    if [[ "$raw" =~ ^([^@]+)@users\.noreply\.github\.com$ ]]; then
        echo "${BASH_REMATCH[1]}"
        return
    fi

    echo "$raw"
}

# Resolve user identity and its source without mutating global state.
devforge_resolve_user_raw() {
    local user="" source="unknown"

    if [ -f "$DEVFORGE_SESSION_USER_FILE" ]; then
        user=$(cat "$DEVFORGE_SESSION_USER_FILE" 2>/dev/null || echo "")
        source=$(cat "$DEVFORGE_SESSION_USER_SOURCE_FILE" 2>/dev/null || echo "session_cache")
    fi

    if [ -z "$user" ]; then
        user=$(git config user.email 2>/dev/null)
        [ -n "$user" ] && source="git_repo_email"
    fi

    if [ -z "$user" ]; then
        user=$(git config --global user.email 2>/dev/null)
        [ -n "$user" ] && source="git_global_email"
    fi

    if [ -z "$user" ] && [ -f "${HOME}/.claude/.devforge-user" ]; then
        user=$(cat "${HOME}/.claude/.devforge-user" 2>/dev/null || echo "")
        [ -n "$user" ] && source="legacy_cache"
    fi

    if [ -z "$user" ]; then
        user="${USER:-$(whoami 2>/dev/null || echo "unknown")}"
        source="os_user"
    fi

    printf '%s|%s\n' "$user" "$source"
}

devforge_cache_user() {
    local raw_user="${1:-}"
    local source="${2:-unknown}"
    printf '%s' "$raw_user" > "$DEVFORGE_SESSION_USER_FILE"
    printf '%s' "$source" > "$DEVFORGE_SESSION_USER_SOURCE_FILE"
    printf '%s' "$raw_user" > "${HOME}/.claude/.devforge-user"
}

# Get canonical user identity for analytics.
devforge_get_user() {
    if [ -n "$DEVFORGE_PINNED_USER" ]; then
        echo "$DEVFORGE_PINNED_USER"
        return
    fi
    local resolved raw_user
    resolved=$(devforge_resolve_user_raw)
    raw_user="${resolved%%|*}"
    devforge_canonicalize_user "$raw_user"
}

devforge_get_user_raw() {
    local resolved
    resolved=$(devforge_resolve_user_raw)
    printf '%s' "${resolved%%|*}"
}

devforge_get_user_source() {
    local resolved
    resolved=$(devforge_resolve_user_raw)
    printf '%s' "${resolved#*|}"
}

# Get or generate session ID
devforge_get_sid() {
    if [ -n "$DEVFORGE_PINNED_SID" ]; then
        echo "$DEVFORGE_PINNED_SID"
        return
    fi
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

# Initialize per-session state directory and pin identity for the session lifetime
devforge_init_session() {
    local sid=$(devforge_get_sid)
    DEVFORGE_SESSION_DIR="${HOME}/.claude/devforge-state/${sid}"
    DEVFORGE_PINNED_SID="$sid"
    if [ -f "${DEVFORGE_SESSION_DIR}/user.json" ] && command -v python3 >/dev/null 2>&1; then
        DEVFORGE_PINNED_USER=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('raw',''))" "${DEVFORGE_SESSION_DIR}/user.json" 2>/dev/null || echo "")
    fi
    [ -z "$DEVFORGE_PINNED_USER" ] && DEVFORGE_PINNED_USER=$(devforge_get_user)
    export DEVFORGE_SESSION_DIR DEVFORGE_PINNED_USER DEVFORGE_PINNED_SID
}

# Atomic sequence counter for per-session event ordering
devforge_next_seq() {
    local seq_file="${DEVFORGE_SESSION_DIR}/seq"
    if [ -z "$DEVFORGE_SESSION_DIR" ] || [ ! -d "$DEVFORGE_SESSION_DIR" ]; then
        echo "0"
        return
    fi
    if command -v flock >/dev/null 2>&1; then
        (
            flock -n 9 || { echo "0"; return; }
            local current=$(cat "$seq_file" 2>/dev/null || echo "0")
            local next=$((current + 1))
            echo "$next" > "$seq_file"
            echo "$next"
        ) 9>"${seq_file}.lock"
    else
        local current=$(cat "$seq_file" 2>/dev/null || echo "0")
        local next=$((current + 1))
        echo "$next" > "$seq_file"
        echo "$next"
    fi
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
    if [ "$jira_id" = "null" ]; then jira_json="null"; else jira_json="\"$(devforge_sanitize_json_str "$jira_id")\""; fi

    # Schema v2 fields
    local seq=$(devforge_next_seq)
    local event_id="${sid}-${seq}"
    local hook_name="${DEVFORGE_CURRENT_HOOK:-unknown}"
    local repo_root
    repo_root=$(git rev-parse --show-toplevel 2>/dev/null || echo "$(pwd)")
    local project_canonical
    project_canonical=$(basename "$repo_root")

    local user user_raw user_source safe_user safe_user_raw safe_user_source safe_sid safe_branch safe_project safe_event safe_status safe_repo_root safe_project_canonical
    user=$(devforge_get_user)
    user_raw=$(devforge_get_user_raw)
    user_source=$(devforge_get_user_source)
    safe_user=$(devforge_sanitize_json_str "$user")
    safe_user_raw=$(devforge_sanitize_json_str "$user_raw")
    safe_user_source=$(devforge_sanitize_json_str "$user_source")
    safe_sid=$(devforge_sanitize_json_str "$sid")
    safe_branch=$(devforge_sanitize_json_str "$branch")
    safe_project=$(devforge_sanitize_json_str "$project")
    safe_event=$(devforge_sanitize_json_str "$event")
    safe_status=$(devforge_sanitize_json_str "$status")
    safe_repo_root=$(devforge_sanitize_json_str "$repo_root")
    safe_project_canonical=$(devforge_sanitize_json_str "$project_canonical")

    # Atomic append — printf avoids echo quoting issues (schema v2 + backward compat)
    printf '{"event_id":"%s","schema_version":2,"session_seq":%s,"hook_name":"%s","actor_canonical":"%s","repo_root":"%s","project_canonical":"%s","ts":"%s","user":"%s","user_raw":"%s","user_source":"%s","sid":"%s","branch":"%s","jira_id":%s,"project":"%s","event":"%s","status":"%s","meta":%s}\n' \
        "$event_id" "$seq" "$hook_name" "$safe_user" "$safe_repo_root" "$safe_project_canonical" \
        "$ts" "$safe_user" "$safe_user_raw" "$safe_user_source" "$safe_sid" "$safe_branch" "$jira_json" "$safe_project" "$safe_event" "$safe_status" "$meta" >> "$DEVFORGE_LOG_FILE"

    # Dual write: session-specific activity log (schema v2)
    if [ -n "$DEVFORGE_SESSION_DIR" ] && [ -d "$DEVFORGE_SESSION_DIR" ]; then
        printf '{"event_id":"%s","schema_version":2,"session_seq":%s,"hook_name":"%s","actor_canonical":"%s","repo_root":"%s","project_canonical":"%s","ts":"%s","user":"%s","user_raw":"%s","user_source":"%s","sid":"%s","branch":"%s","jira_id":%s,"project":"%s","event":"%s","status":"%s","meta":%s}\n' \
            "$event_id" "$seq" "$hook_name" "$safe_user" "$safe_repo_root" "$safe_project_canonical" \
            "$ts" "$safe_user" "$safe_user_raw" "$safe_user_source" "$safe_sid" "$safe_branch" "$jira_json" "$safe_project" "$safe_event" "$safe_status" "$meta" >> "${DEVFORGE_SESSION_DIR}/activity.jsonl" || true
    fi
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
    if [ "$jira_id" = "null" ]; then jira_json="null"; else jira_json="\"$(devforge_sanitize_json_str "$jira_id")\""; fi

    # Schema v2 fields
    local seq=$(devforge_next_seq)
    local event_id="${sid}-${seq}"
    local hook_name="${DEVFORGE_CURRENT_HOOK:-unknown}"
    local repo_root
    repo_root=$(git rev-parse --show-toplevel 2>/dev/null || echo "$(pwd)")
    local project_canonical
    project_canonical=$(basename "$repo_root")

    local user user_raw user_source safe_user safe_user_raw safe_user_source safe_sid safe_branch safe_project safe_event safe_status safe_repo_root safe_project_canonical
    user=$(devforge_get_user)
    user_raw=$(devforge_get_user_raw)
    user_source=$(devforge_get_user_source)
    safe_user=$(devforge_sanitize_json_str "$user")
    safe_user_raw=$(devforge_sanitize_json_str "$user_raw")
    safe_user_source=$(devforge_sanitize_json_str "$user_source")
    safe_sid=$(devforge_sanitize_json_str "$sid")
    safe_branch=$(devforge_sanitize_json_str "$branch")
    safe_project=$(devforge_sanitize_json_str "$project")
    safe_event=$(devforge_sanitize_json_str "$event")
    safe_status=$(devforge_sanitize_json_str "$status")
    safe_repo_root=$(devforge_sanitize_json_str "$repo_root")
    safe_project_canonical=$(devforge_sanitize_json_str "$project_canonical")

    printf '{"event_id":"%s","schema_version":2,"session_seq":%s,"hook_name":"%s","actor_canonical":"%s","repo_root":"%s","project_canonical":"%s","ts":"%s","user":"%s","user_raw":"%s","user_source":"%s","sid":"%s","branch":"%s","jira_id":%s,"project":"%s","event":"%s","status":"%s","duration_ms":%d,"meta":%s}\n' \
        "$event_id" "$seq" "$hook_name" "$safe_user" "$safe_repo_root" "$safe_project_canonical" \
        "$ts" "$safe_user" "$safe_user_raw" "$safe_user_source" "$safe_sid" "$safe_branch" "$jira_json" "$safe_project" "$safe_event" "$safe_status" "$duration_ms" "$meta" >> "$DEVFORGE_LOG_FILE"

    # Dual write: session-specific activity log (schema v2 with duration)
    if [ -n "$DEVFORGE_SESSION_DIR" ] && [ -d "$DEVFORGE_SESSION_DIR" ]; then
        printf '{"event_id":"%s","schema_version":2,"session_seq":%s,"hook_name":"%s","actor_canonical":"%s","repo_root":"%s","project_canonical":"%s","ts":"%s","user":"%s","user_raw":"%s","user_source":"%s","sid":"%s","branch":"%s","jira_id":%s,"project":"%s","event":"%s","status":"%s","duration_ms":%d,"meta":%s}\n' \
            "$event_id" "$seq" "$hook_name" "$safe_user" "$safe_repo_root" "$safe_project_canonical" \
            "$ts" "$safe_user" "$safe_user_raw" "$safe_user_source" "$safe_sid" "$safe_branch" "$jira_json" "$safe_project" "$safe_event" "$safe_status" "$duration_ms" "$meta" >> "${DEVFORGE_SESSION_DIR}/activity.jsonl" || true
    fi
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

# TDD State Machine — set phase explicitly
# Usage: devforge_tdd_set_phase <phase> <target_file> <test_name>
# Phases: NONE, RED, GREEN, REFACTOR
devforge_tdd_set_phase() {
    local phase="$1"
    local target="${2:-unknown}"
    local test_name="${3:-unknown}"
    local state_file="${HOME}/.claude/.devforge-tdd-state"
    echo "${phase}|${target}|${test_name}|$(date +%s)" > "$state_file"
}

# TDD State Machine — get current phase
# Returns: RED, GREEN, REFACTOR, or empty string
devforge_tdd_get_phase() {
    local state_file="${HOME}/.claude/.devforge-tdd-state"
    cat "$state_file" 2>/dev/null | cut -d'|' -f1
}

# TDD State Machine — reset (end of cycle or session)
devforge_tdd_reset() {
    rm -f "${HOME}/.claude/.devforge-tdd-state"
}
