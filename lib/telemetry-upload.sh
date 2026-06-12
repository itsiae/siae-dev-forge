#!/usr/bin/env bash
# DevForge Telemetry Upload — Outbox Model
# Uploads pending batches from session outbox directories.
# Replaces the old atomic-move single POST with a durable outbox pattern:
#   activity.jsonl → outbox/batch-<ts>.jsonl → upload → outbox/acked/

# Hardcoded endpoint — no dev configuration needed
# TODO(security): API key hardcoded as fallback — pre-existing tech debt
# documented in spec-reviewer iter-5 finding CRITICAL #1.
# Action: move to AWS Secrets Manager or per-install env var.
# Tracker: docs/plans/2026-04-13-telemetry-zero-loss-design.md Sez 8 (Secrets Manager
# already in cost estimate $0.40/mese). Implementation rinviata a iniziativa
# successiva (richiede plugin install hook che setta env per OGNI dev macchina).
# Mitigation attuale: env var DEVFORGE_TELEMETRY_KEY ha precedenza sul default.
DEVFORGE_TELEMETRY_ENDPOINT="${DEVFORGE_TELEMETRY_ENDPOINT:-https://5o6tu3hcei.execute-api.eu-west-1.amazonaws.com/v1/logs}"
DEVFORGE_TELEMETRY_KEY="${DEVFORGE_TELEMETRY_KEY:-WhQioTyfb41PcvRrjD7ji6o8xF59quSd3OYvM1sz}"

# Backward compat: honour legacy DEVFORGE_TELEMETRY_URL if set
DEVFORGE_TELEMETRY_ENDPOINT="${DEVFORGE_TELEMETRY_URL:-$DEVFORGE_TELEMETRY_ENDPOINT}"

# --- Outbox functions --------------------------------------------------------

# devforge_create_batch — copies new lines into batch files.
# Zero-loss PR-A: processes BOTH activity.jsonl AND activity-<ts>.archived.jsonl
# (created by _devforge_check_rotation). Uses per-file byte-offset cursor in
# outbox/.cursor-<basename>. Fully-consumed archived files are removed.
devforge_create_batch() {
    local session_dir="${DEVFORGE_SESSION_DIR:-}"
    [ -z "$session_dir" ] || [ ! -d "$session_dir" ] && return 0

    mkdir -p "${session_dir}/outbox" 2>/dev/null || return 0

    local lock_file="${session_dir}/outbox/.batch.lock"

    (
        # Try lock, skip if can't acquire (another process is batching)
        if command -v flock >/dev/null 2>&1; then
            flock -n 9 || return 0
        fi

        # Process archived files first (oldest → newest by ts in filename), then current.
        # shellcheck disable=SC2012
        local files
        files=$(ls -1 "${session_dir}"/activity-*.archived.jsonl 2>/dev/null | sort) || files=""
        [ -f "${session_dir}/activity.jsonl" ] && files="${files}
${session_dir}/activity.jsonl"

        local f basename cursor_file cursor file_size batch_file
        for f in $files; do
            [ -f "$f" ] && [ -s "$f" ] || { _devforge_maybe_remove_archived "$f" "${session_dir}/outbox"; continue; }
            basename=$(basename "$f")
            cursor_file="${session_dir}/outbox/.cursor-${basename}"
            cursor=$(cat "$cursor_file" 2>/dev/null || echo "0")
            file_size=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null || echo "0")

            if [ "$file_size" -gt "$cursor" ] 2>/dev/null; then
                local epoch_ns
                epoch_ns=$(command -v _devforge_epoch_ns >/dev/null 2>&1 && _devforge_epoch_ns || date +%s)
                batch_file="${session_dir}/outbox/batch-${epoch_ns}-$$-${basename%.jsonl}.jsonl"
                tail -c +"$((cursor + 1))" "$f" > "$batch_file" 2>/dev/null || { rm -f "$batch_file"; continue; }
                if [ -s "$batch_file" ]; then
                    echo "$file_size" > "$cursor_file"
                else
                    rm -f "$batch_file"
                fi
            fi

            # Cleanup: remove archived file if fully consumed and cursor matches size
            _devforge_maybe_remove_archived "$f" "${session_dir}/outbox"
        done
    ) 9>"$lock_file" 2>/dev/null
}

# _devforge_maybe_remove_archived — remove an archived file if cursor == file_size
# (means all lines have been batched). Also removes the cursor file.
_devforge_maybe_remove_archived() {
    local f="$1" outbox="$2"
    local basename
    basename=$(basename "$f")
    case "$basename" in
        activity-*.archived.jsonl) ;;
        *) return 0 ;;  # only clean up archived files, never activity.jsonl
    esac
    local cursor_file="${outbox}/.cursor-${basename}"
    local cursor file_size
    cursor=$(cat "$cursor_file" 2>/dev/null || echo "0")
    file_size=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null || echo "0")
    if [ "$cursor" -ge "$file_size" ] 2>/dev/null && [ "$file_size" -gt 0 ] 2>/dev/null; then
        rm -f "$f" "$cursor_file"
    fi
}

# devforge_batch_global — batch events from the global activity file.
# The global file (~/.claude/devforge-activity.jsonl) receives ALL events via
# dual-write in devforge_log(), but is never read by devforge_create_batch
# (which processes only session-specific files). If session-start crashes
# before creating the session dir, events land ONLY in the global file and
# are permanently stranded. This function provides a fallback drain with a
# dedicated cursor so events are batched exactly once.
devforge_batch_global() {
    local global_file="${DEVFORGE_LOG_FILE:-${HOME}/.claude/devforge-activity.jsonl}"
    [ -f "$global_file" ] && [ -s "$global_file" ] || return 0

    local state_root="${HOME}/.claude/devforge-state"
    mkdir -p "${state_root}/.global-outbox/acked" 2>/dev/null || return 0

    local cursor_file="${state_root}/.global-outbox/.cursor-global"
    local cursor file_size batch_file epoch_ns
    cursor=$(cat "$cursor_file" 2>/dev/null || echo "0")
    file_size=$(stat -f%z "$global_file" 2>/dev/null || stat -c%s "$global_file" 2>/dev/null || echo "0")

    if [ "$file_size" -gt "$cursor" ] 2>/dev/null; then
        epoch_ns=$(command -v _devforge_epoch_ns >/dev/null 2>&1 && _devforge_epoch_ns || date +%s)
        batch_file="${state_root}/.global-outbox/batch-${epoch_ns}-$$.jsonl"
        tail -c +"$((cursor + 1))" "$global_file" > "$batch_file" 2>/dev/null || { rm -f "$batch_file"; return 0; }
        if [ -s "$batch_file" ]; then
            echo "$file_size" > "$cursor_file"
        else
            rm -f "$batch_file"
        fi
    fi
}

# _devforge_post_batch <batch_file> — POST one batch, echo HTTP code.
# Extracted for testability: tests override this to inject codes without network.
# Returns "000" on curl transport failure (timeout/DNS/connection).
_devforge_post_batch() {
    local batch="$1"
    curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$DEVFORGE_TELEMETRY_ENDPOINT" \
        -H "x-api-key: $DEVFORGE_TELEMETRY_KEY" \
        -H "Content-Type: application/jsonl" \
        --data-binary "@${batch}" \
        --max-time 10 2>/dev/null || echo "000"
}

# devforge_upload_logs — creates a batch from current session + uploads all pending
devforge_upload_logs() {
    devforge_create_batch 2>/dev/null || true
    devforge_batch_global 2>/dev/null || true
    devforge_upload_backlog 2>/dev/null || true
}

# devforge_upload_backlog — iterates ALL session dirs and uploads pending batches
devforge_upload_backlog() {
    [ -z "$DEVFORGE_TELEMETRY_ENDPOINT" ] && return 0

    # Never send API key over plain HTTP
    [[ ! "$DEVFORGE_TELEMETRY_ENDPOINT" =~ ^https:// ]] && return 0

    local state_root="${HOME}/.claude/devforge-state"
    [ -d "$state_root" ] || return 0

    # Include both session-specific outboxes AND the global fallback outbox
    for outbox_dir in "$state_root"/*/outbox "$state_root/.global-outbox"; do
        [ -d "$outbox_dir" ] || continue
        for batch in "$outbox_dir"/batch-*.jsonl; do
            [ -f "$batch" ] || continue
            local response
            response=$(_devforge_post_batch "$batch")

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
    for batch in "$state_root"/*/outbox/batch-*.jsonl "$state_root/.global-outbox"/batch-*.jsonl; do
        [ -f "$batch" ] && count=$((count + 1))
    done
    echo "$count"
}
