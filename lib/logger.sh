#!/usr/bin/env bash
# DevForge Activity Logger
# Appends structured JSONL events to ~/.claude/devforge-activity.jsonl

DEVFORGE_LOG_FILE="${DEVFORGE_LOG_FILE:-${HOME}/.claude/devforge-activity.jsonl}"
DEVFORGE_SID_FILE="${HOME}/.claude/.devforge-session-id"
DEVFORGE_SESSION_USER_FILE="${HOME}/.claude/.devforge-session-user"
DEVFORGE_SESSION_USER_SOURCE_FILE="${HOME}/.claude/.devforge-session-user-source"

# Per-session state isolation & identity pinning.
# Preserve env-provided values to support multi-source from hooks and tests.
DEVFORGE_SESSION_DIR="${DEVFORGE_SESSION_DIR:-}"
DEVFORGE_PINNED_USER="${DEVFORGE_PINNED_USER:-}"
DEVFORGE_PINNED_SID="${DEVFORGE_PINNED_SID:-}"

# Cross-platform epoch nanoseconds.
# macOS < 26 (Tahoe) lacks %N support: `date +%s%N` emits "1713000000N"
# (literal "N" suffix) with exit 0 — the `|| echo "0"` fallback never fires.
# This helper validates the output is purely numeric before returning it.
_devforge_epoch_ns() {
    local ts
    ts=$(date +%s%N 2>/dev/null || echo "0")
    # Strip non-numeric output (e.g. macOS BSD date appending literal "N")
    case "$ts" in *[!0-9]*) ts="0" ;; esac
    echo "$ts"
}

# _devforge_shasum — portable SHA-1 wrapper (issue #238).
# macOS ships `shasum` (Perl); GNU coreutils ships `sha1sum`. Git Bash on
# Windows excludes /usr/bin/core_perl from the PATH that Claude Code passes
# to hooks, so `shasum` is unavailable there even though Perl ships it.
# Both backends emit `<40-hex>  -\n` on stdin, so callers using
# `cut -d' ' -f1` / `head -c N` work identically.
# Last-resort: drain stdin (SIGPIPE prevention) then emit zero-hash so
# pipe consumers see a well-formed line. Unreachable on supported platforms.
_devforge_shasum() {
    if command -v shasum >/dev/null 2>&1; then
        shasum
    elif command -v sha1sum >/dev/null 2>&1; then
        sha1sum
    else
        cat >/dev/null
        printf '0000000000000000000000000000000000000000  -\n'
    fi
}

# Ensure log directory exists
mkdir -p "$(dirname "$DEVFORGE_LOG_FILE")"

# Log rotation: max 50MB, 1 backup
# Zero-loss PR-A: resolve lib/ directory of this file for finding atomic_write.py.
# Source-once guard: if already set (e.g. overridden by caller), keep it.
if [ -z "${DEVFORGE_LIB_DIR:-}" ]; then
    DEVFORGE_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

# Zero-loss PR-A: atomic append via Python (lock + fsync cross-OS).
# Replaces raw `printf >> file` to eliminate race conditions on concurrent hook writes
# (root cause of the 6612 parse errors observed in S3 pre-PR187).
#
# Fallback bash-only path: if python3 is NOT available (e.g. Windows Git Bash
# without Python installed), degrade to unlocked `printf >>` and emit a one-shot
# warning. Keeps the plugin functional on python-less environments instead of
# dropping events silently. Zero-loss guarantees are reduced in that mode:
# no fsync, no lock, no in-lock rotation. Users are strongly encouraged to
# install python3 — see docs/plans/ for roadmap of auto-install Python-Standalone.
_devforge_atomic_append() {
    local target_file="$1" line="$2"
    # Post-PR-A review fix: pass rotate_at_bytes so rotation happens INSIDE
    # the same lock as the append (previous bash _devforge_check_rotation was
    # outside the lock — race condition). Default 5MB; override with env.
    local rotate_bytes="${DEVFORGE_ROTATE_BYTES:-5242880}"
    # DEVFORGE_FORCE_BASH_FALLBACK=1 forces the degraded path for testing.
    if [ -z "${DEVFORGE_FORCE_BASH_FALLBACK:-}" ] && command -v python3 >/dev/null 2>&1; then
        python3 "${DEVFORGE_LIB_DIR}/atomic_write.py" append "$target_file" "$line" "$rotate_bytes" 2>/dev/null
        return $?
    fi
    # --- DEGRADED PATH: no python3 available ---
    # Append without lock/fsync. Events still land in activity.jsonl but
    # concurrent writers may produce truncated lines (same risk as pre-PR187).
    printf '%s\n' "$line" >> "$target_file" 2>/dev/null
    # Warn once per session via sentinel file (avoids per-call noise).
    local warned="${HOME}/.claude/.devforge-no-python-warned"
    if [ ! -f "$warned" ]; then
        mkdir -p "$(dirname "$warned")" 2>/dev/null
        touch "$warned"
        printf '[DevForge] WARNING: python3 not found — telemetry degraded to bash-only (no lock/fsync). Install python3 for full zero-loss guarantees.\n' >&2
    fi
}

# Zero-loss PR-A: NTP clock skew detection (edge cases #7 + #18).
# Args: ntp_epoch — unix ts from NTP source (empty if unreachable).
# Side effects: if |local - ntp| > 3600s, writes clock-skew.json in
# DEVFORGE_SESSION_DIR with force_received_at:true flag. Lambda side uses
# this flag to prefer received_at over client ts for S3 partitioning.
_devforge_check_clock_skew() {
    local ntp_epoch="$1"
    # NTP unreachable or empty arg: no-op
    [ -z "$ntp_epoch" ] && return 0
    # Non-numeric input: no-op
    case "$ntp_epoch" in
        ''|*[!0-9]*) return 0 ;;
    esac
    local session_dir="${DEVFORGE_SESSION_DIR:-}"
    [ -z "$session_dir" ] || [ ! -d "$session_dir" ] && return 0

    local local_epoch skew skew_abs
    local_epoch=$(date -u +%s)
    skew=$((local_epoch - ntp_epoch))
    skew_abs=${skew#-}

    if [ "$skew_abs" -gt 3600 ] 2>/dev/null; then
        # Write flag file (JSON) — Lambda reads force_received_at from session user.json
        # or from this sentinel via upload metadata
        printf '{"force_received_at":true,"clock_skew_sec":%s,"ntp_source":"external","detected_at":"%s"}\n' \
            "$skew" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "${session_dir}/clock-skew.json"
    fi
    return 0
}

# Zero-loss PR-A: disk space gate.
# Overridable in tests. Returns free KB on the DEVFORGE_SESSION_DIR filesystem.
_devforge_free_kb() {
    local dir="${DEVFORGE_SESSION_DIR:-$HOME/.claude}"
    df -k "$dir" 2>/dev/null | tail -1 | awk '{print $4}'
}

# Returns 0 if disk has >=100MB free, 1 otherwise.
# On low disk, queues a timestamp line to .devforge-disk-full-events.tmp
# so the next successful flush can emit a `local_disk_full` event.
_devforge_disk_gate() {
    local free_kb min_kb=102400  # 100MB
    free_kb=$(_devforge_free_kb)
    [ -z "$free_kb" ] && free_kb="999999999"  # no df output → assume ok
    if [ "$free_kb" -lt "$min_kb" ] 2>/dev/null; then
        local recovery_file="${HOME}/.claude/.devforge-disk-full-events.tmp"
        mkdir -p "$(dirname "$recovery_file")" 2>/dev/null
        printf '%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)|free_kb=${free_kb}" >> "$recovery_file"
        return 1
    fi
    return 0
}

_devforge_check_rotation() {
    # Post-PR-A review fix: rotation is now ATOMIC inside atomic_write.py
    # (under the same flock as the append). This bash function kept ONLY to
    # enforce the 50MB TOTAL CAP on activity + archived, and it does so SAFELY:
    # drops ONLY fully-consumed archived (cursor_file == file_size). Archived
    # not-yet-uploaded (cursor < size OR cursor file missing) are PRESERVED
    # even if total > cap — better disk pressure than data loss.
    local cap_bytes=52428800  # 50MB total cap
    [ -z "${DEVFORGE_LOG_FILE:-}" ] && return 0
    local base dir
    base=$(basename "$DEVFORGE_LOG_FILE" .jsonl)
    dir=$(dirname "$DEVFORGE_LOG_FILE")

    local total=0 sz
    for f in "${dir}/${base}.jsonl" "${dir}/${base}"-*.archived.jsonl; do
        [ -f "$f" ] || continue
        sz=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null || echo 0)
        total=$((total + sz))
    done

    # Safe drop: only archived fully consumed by the batcher.
    # Cursor file is in ${session_dir}/outbox/.cursor-<basename>.
    local session_dir outbox cursor_file cursor archived_basename archived dropped
    session_dir="${DEVFORGE_SESSION_DIR:-$dir}"
    outbox="${session_dir}/outbox"
    while [ "$total" -gt "$cap_bytes" ] 2>/dev/null; do
        dropped=0
        # shellcheck disable=SC2012
        for archived in $(ls -1 "${dir}/${base}"-*.archived.jsonl 2>/dev/null | sort); do
            [ -f "$archived" ] || continue
            archived_basename=$(basename "$archived")
            cursor_file="${outbox}/.cursor-${archived_basename}"
            cursor=$(cat "$cursor_file" 2>/dev/null || echo "0")
            sz=$(stat -f%z "$archived" 2>/dev/null || stat -c%s "$archived" 2>/dev/null || echo 0)
            # Only drop if fully consumed: cursor >= file_size
            if [ "$cursor" -ge "$sz" ] 2>/dev/null && [ "$sz" -gt 0 ] 2>/dev/null; then
                rm -f "$archived" "$cursor_file"
                total=$((total - sz))
                dropped=1
                break  # re-check cap with fewer files
            fi
        done
        # No safely-droppable archived found → stop (prefer disk pressure)
        [ "$dropped" -eq 0 ] && break
    done
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

# Emit a RAW multi-signal identity bundle as a single-line JSON object.
# All signals best-effort (empty string if unavailable); never aborts under
# `set -euo pipefail`. NO resolution/normalization here — the downstream
# consumer (developer-telemetry) resolves with the full signal set, which makes
# shared-machine / wrong-git-config cases disambiguable. repo_root is NOT
# included: it is already a top-level event field (see devforge_log_timed).
devforge_identity_bundle() {
    local gle gln gge ggn osu host
    gle=$(git config user.email 2>/dev/null || true)
    gln=$(git config user.name 2>/dev/null || true)
    gge=$(git config --global user.email 2>/dev/null || true)
    ggn=$(git config --global user.name 2>/dev/null || true)
    osu="${USER:-}"
    [ -z "$osu" ] && osu=$(whoami 2>/dev/null || echo "")
    host=$(hostname -s 2>/dev/null || hostname 2>/dev/null || echo "")
    printf '{"git_local_email":"%s","git_local_name":"%s","git_global_email":"%s","git_global_name":"%s","os_user":"%s","host":"%s"}' \
        "$(devforge_sanitize_json_str "$gle")" "$(devforge_sanitize_json_str "$gln")" \
        "$(devforge_sanitize_json_str "$gge")" "$(devforge_sanitize_json_str "$ggn")" \
        "$(devforge_sanitize_json_str "$osu")" "$(devforge_sanitize_json_str "$host")"
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
    # Prefer pinned session user.json
    if [ -n "$DEVFORGE_SESSION_DIR" ] && [ -f "${DEVFORGE_SESSION_DIR}/user.json" ] && command -v python3 >/dev/null 2>&1; then
        local raw
        raw=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('raw',''))" "${DEVFORGE_SESSION_DIR}/user.json" 2>/dev/null || echo "")
        if [ -n "$raw" ]; then
            printf '%s' "$raw"
            return
        fi
    fi
    local resolved
    resolved=$(devforge_resolve_user_raw)
    printf '%s' "${resolved%%|*}"
}

devforge_get_user_source() {
    # Prefer pinned session user.json
    if [ -n "$DEVFORGE_SESSION_DIR" ] && [ -f "${DEVFORGE_SESSION_DIR}/user.json" ] && command -v python3 >/dev/null 2>&1; then
        local src
        src=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('source',''))" "${DEVFORGE_SESSION_DIR}/user.json" 2>/dev/null || echo "")
        if [ -n "$src" ]; then
            printf '%s' "$src"
            return
        fi
    fi
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
        # Bug fix v1.63.3: era "no-session" stringa letterale -> 11715 eventi orfani
        # collassati su un singolo bucket. Ora genera nuovo sid e persiste.
        devforge_new_sid
    fi
}

# Generate a new session ID and persist it
devforge_new_sid() {
    local sid
    sid=$(_devforge_epoch_ns | _devforge_shasum | head -c 8)
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
        [ -n "$DEVFORGE_PINNED_USER" ] && DEVFORGE_PINNED_USER=$(devforge_canonicalize_user "$DEVFORGE_PINNED_USER")
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
        local locked_result
        locked_result=$(
            flock -n 9 || exit 1
            current=$(cat "$seq_file" 2>/dev/null || echo "0")
            next=$((current + 1))
            echo "$next" > "$seq_file"
            echo "$next"
        ) 9>"${seq_file}.lock"
        if [ -n "$locked_result" ]; then
            echo "$locked_result"
            return
        fi
        # flock contention or flock unavailable — fallback to unlocked increment
        # (no atomicity guarantee; duplicate seq numbers possible under concurrency)
    fi
    local current=$(cat "$seq_file" 2>/dev/null || echo "0")
    local next=$((current + 1))
    echo "$next" > "$seq_file"
    echo "$next"
}

# Sanitize a string for safe JSON embedding.
# Escapes: \, ", \n, \r, \t, and control chars 0x00-0x1F (stripped).
# Source of truth for JSON escaping across hooks — do not duplicate inline.
# Usage: devforge_sanitize_json_str "unsafe string"
devforge_sanitize_json_str() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    # Strip remaining control chars (0x00-0x08, 0x0b, 0x0c, 0x0e-0x1f).
    # \n \r \t already handled above; JSON spec requires these or \uXXXX form.
    # We strip (not escape to \uXXXX) for simplicity — these bytes should not
    # appear in file paths, skill names, or commit messages in practice.
    s=$(printf '%s' "$s" | LC_ALL=C tr -d '\000-\010\013\014\016-\037')
    printf '%s' "$s"
}

# Log an event to the JSONL file
# Usage: devforge_log <event_type> <status> [meta_json]
# Example: devforge_log "session_start" "success" '{"project_dir":"/path","plugin_version":"1.0.1"}'
devforge_log() {
    # Zero-loss: skip write if disk space is critically low. Recovery event
    # is queued for emission at the next successful write.
    _devforge_disk_gate || return 0
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

    # Zero-loss PR-A: build the JSON line once, then atomic append via Python
    # (lock + fsync, cross-OS). Replaces raw `>> file` to eliminate race.
    local json_line
    json_line=$(printf '{"event_id":"%s","schema_version":2,"session_seq":%s,"hook_name":"%s","actor_canonical":"%s","repo_root":"%s","project_canonical":"%s","ts":"%s","user":"%s","user_raw":"%s","user_source":"%s","sid":"%s","branch":"%s","jira_id":%s,"project":"%s","event":"%s","status":"%s","meta":%s}' \
        "$event_id" "$seq" "$hook_name" "$safe_user" "$safe_repo_root" "$safe_project_canonical" \
        "$ts" "$safe_user" "$safe_user_raw" "$safe_user_source" "$safe_sid" "$safe_branch" "$jira_json" "$safe_project" "$safe_event" "$safe_status" "$meta")

    _devforge_atomic_append "$DEVFORGE_LOG_FILE" "$json_line"

    # Dual write: session-specific activity log (schema v2).
    # Skip if the session activity file is the same path as DEVFORGE_LOG_FILE
    # (resolved with realpath if available) to avoid duplicate lines.
    if [ -n "$DEVFORGE_SESSION_DIR" ] && [ -d "$DEVFORGE_SESSION_DIR" ]; then
        local session_activity="${DEVFORGE_SESSION_DIR}/activity.jsonl"
        if [ "$session_activity" != "$DEVFORGE_LOG_FILE" ]; then
            _devforge_atomic_append "$session_activity" "$json_line"
        fi
    fi
}

# Log with duration measurement
# Usage: devforge_log_timed <event_type> <status> <start_time_epoch_ns> [meta_json]
devforge_log_timed() {
    _devforge_disk_gate || return 0
    _devforge_check_rotation
    local event="$1"
    local status="${2:-success}"
    local start_ns="$3"
    local meta="${4-}"
    [ -z "$meta" ] && meta='{}'
    local end_ns duration_ms ts sid git_ctx branch jira_id project jira_json

    end_ns=$(_devforge_epoch_ns)
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

    # Zero-loss PR-A: atomic append via Python (lock + fsync)
    local json_line
    json_line=$(printf '{"event_id":"%s","schema_version":2,"session_seq":%s,"hook_name":"%s","actor_canonical":"%s","repo_root":"%s","project_canonical":"%s","ts":"%s","user":"%s","user_raw":"%s","user_source":"%s","sid":"%s","branch":"%s","jira_id":%s,"project":"%s","event":"%s","status":"%s","duration_ms":%d,"meta":%s}' \
        "$event_id" "$seq" "$hook_name" "$safe_user" "$safe_repo_root" "$safe_project_canonical" \
        "$ts" "$safe_user" "$safe_user_raw" "$safe_user_source" "$safe_sid" "$safe_branch" "$jira_json" "$safe_project" "$safe_event" "$safe_status" "$duration_ms" "$meta")

    _devforge_atomic_append "$DEVFORGE_LOG_FILE" "$json_line"

    # Dual write: session-specific activity log (schema v2 with duration).
    # Skip if same path as DEVFORGE_LOG_FILE to avoid duplicates (FIX CRITICAL
    # iter-5 review: parità con devforge_log che già aveva questa guard).
    if [ -n "$DEVFORGE_SESSION_DIR" ] && [ -d "$DEVFORGE_SESSION_DIR" ]; then
        local session_activity_t="${DEVFORGE_SESSION_DIR}/activity.jsonl"
        if [ "$session_activity_t" != "$DEVFORGE_LOG_FILE" ]; then
            _devforge_atomic_append "$session_activity_t" "$json_line"
        fi
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
