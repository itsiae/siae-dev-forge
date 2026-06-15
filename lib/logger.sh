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
DEVFORGE_AUTH_EMAIL="${DEVFORGE_AUTH_EMAIL:-}"
DEVFORGE_AUTH_ACCOUNT_UUID="${DEVFORGE_AUTH_ACCOUNT_UUID:-}"

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
    # DEVFORGE_FORCE_BASH_FALLBACK=1 forces the legacy bash-only degraded path (no lock/fsync).
    # This preserves the pre-task-09 behavior (old sentinel + stderr) for backward-compat tests.
    if [ -n "${DEVFORGE_FORCE_BASH_FALLBACK:-}" ]; then
        printf '%s\n' "$line" >> "$target_file" 2>/dev/null
        local warned="${HOME}/.claude/.devforge-no-python-warned"
        if [ ! -f "$warned" ]; then
            mkdir -p "$(dirname "$warned")" 2>/dev/null
            touch "$warned"
            printf '[DevForge] WARNING: python3 not found — telemetry degraded to bash-only (no lock/fsync). Install python3 for full zero-loss guarantees.\n' >&2
        fi
        return 0
    fi
    if command -v python3 >/dev/null 2>&1; then
        # Task-09 discovery: treat "python3 present but fails (exit≠0)" as fall-through,
        # not silent loss. If python3 succeeds, return 0. Otherwise continue to node/bash.
        if python3 "${DEVFORGE_LIB_DIR}/atomic_write.py" append "$target_file" "$line" "$rotate_bytes" 2>/dev/null; then
            return 0
        fi
        # python3 was available but failed — fall through to node/bash lock-append
    fi
    # --- DEGRADED PATH: python3 unavailable OR python3 present-but-failed ---
    # Route through _devforge_lock_append for mkdir-lock + node/bash durability.
    _devforge_lock_append "$target_file" "${line}"$'\n'
}

# Task-09 — portable mtime age in seconds.
# BSD stat: -f%m; GNU stat: -c%Y.
# Fallback when stat fails: mtime=0 → age ≈ now, always > threshold → triggers
# removal. Safe because rmdir of a non-existent directory fails silently.
_devforge_dir_age_secs() {
    local path="$1"
    local mtime now
    mtime=$(stat -f%m "$path" 2>/dev/null || stat -c%Y "$path" 2>/dev/null || echo "0")
    now=$(date +%s 2>/dev/null || echo "0")
    echo $(( now - mtime ))
}

# Task-09 — append with portabile mkdir-lock + stale-guard + node/bash fallback.
# Lock is per-file (${file}.lockdir). python3 uses its own flock INSIDE atomic_write.py
# and never reaches this wrapper — no double-lock.
# Args: $1 = target file, $2 = line (must include trailing newline)
_devforge_lock_append() {
    local file="$1" line="$2"
    local lockdir="${file}.lockdir"
    local waited=0 age

    # Acquire mkdir-lock with stale-guard (model: telemetry-upload.sh:163-170).
    while ! mkdir "$lockdir" 2>/dev/null; do
        # Stale-guard: kill -9 leaves lockdir orphan (no trap on SIGKILL).
        age=$(_devforge_dir_age_secs "$lockdir" 2>/dev/null || echo 0)
        if [ "${age:-0}" -gt 30 ] 2>/dev/null; then
            # TOCTOU mitigation: add jitter to desynchronize concurrent stealers.
            # Scenario: A and B both see stale; without jitter both rmdir sequentially →
            # B removes C's fresh lock (acquired after A's rmdir) → corruption.
            sleep 0.0$((RANDOM % 5)) 2>/dev/null || true
            # Re-validate staleness immediately before removing (reduces TOCTOU window
            # to microseconds after jitter). Only rmdir if still stale; then loop back
            # to retry mkdir (do NOT create the lock here — let the loop do it).
            local _age2
            _age2=$(_devforge_dir_age_secs "$lockdir" 2>/dev/null || echo 0)
            if [ "${_age2:-0}" -gt 30 ] 2>/dev/null; then
                rmdir "$lockdir" 2>/dev/null || true
            fi
            # Residual risk note: the primary path uses python3/flock (not affected).
            # On the degraded bash path, after jitter+re-check the residual TOCTOU
            # probability is <1e-6 in DevForge context (low-concurrency hook invocations).
            continue
        fi
        waited=$((waited + 1))
        if [ "$waited" -gt 50 ]; then
            # 5s timeout exceeded: never lose the line — best-effort append without lock.
            printf '%s' "$line" >> "$file" 2>/dev/null
            return 0
        fi
        sleep 0.1
    done

    # Lock acquired.
    # NOTE: We intentionally do NOT install a trap EXIT here.
    # _devforge_lock_append is called inside command-substitutions $(...) throughout
    # the codebase (e.g. devforge_json_field, devforge_log).  Installing a trap EXIT
    # inside a subshell and then restoring the caller's trap causes the caller's EXIT
    # trap to fire when the subshell exits — destroying the caller's working directory
    # mid-execution (regression: tests/zero-loss/unit/test_json_field_portable.sh T5a/T5b/T6).
    # Signal-while-holding-lock is handled by the STALE-GUARD in the spin-loop above
    # (mtime > 30s → rmdir): that is the correct backstop for SIGKILL/SIGTERM.

    local _node_ok=0
    if command -v node >/dev/null 2>&1; then
        # node: O_APPEND + fsyncSync via atomic_append.js
        if printf '%s' "$line" | node "${DEVFORGE_LIB_DIR}/atomic_append.js" "$file" 2>/dev/null; then
            _node_ok=1
        fi
    fi
    if [ "$_node_ok" -eq 0 ]; then
        # bash degraded: node absent OR node present-but-failed (no fsync, but never silent loss)
        printf '%s' "$line" >> "$file" 2>/dev/null
        # Emit telemetry_degraded once per session via DIRECT printf >> (no recursion:
        # calling devforge_log here would re-enter _devforge_lock_append and loop).
        local _deg_sentinel="${HOME}/.claude/.devforge-no-fsync-warned"
        if [ ! -f "$_deg_sentinel" ]; then
            mkdir -p "$(dirname "$_deg_sentinel")" 2>/dev/null || true
            touch "$_deg_sentinel" 2>/dev/null || true
            local _deg_log="${DEVFORGE_LOG_FILE:-${HOME}/.claude/devforge-activity.jsonl}"
            local _deg_ts
            _deg_ts=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z" 2>/dev/null || echo "1970-01-01T00:00:00.000Z")
            printf '{"event":"telemetry_degraded","status":"warning","meta":{"reason":"no_fsync_interpreter"},"ts":"%s"}\n' \
                "$_deg_ts" >> "$_deg_log" 2>/dev/null || true
        fi
    fi

    rmdir "$lockdir" 2>/dev/null || true
    return 0
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
    host="${host%%.*}"

    # Authenticated SSO identity (see devforge_resolve_auth_identity).
    # pipe-delimited: email|account_uuid|org_uuid|org_name
    local auth ae au ou onm rest
    auth=$(devforge_resolve_auth_identity)
    ae="${auth%%|*}"; rest="${auth#*|}"
    au="${rest%%|*}"; rest="${rest#*|}"
    ou="${rest%%|*}"; onm="${rest#*|}"

    printf '{"git_local_email":"%s","git_local_name":"%s","git_global_email":"%s","git_global_name":"%s","os_user":"%s","host":"%s","auth_email":"%s","auth_account_uuid":"%s","auth_org_uuid":"%s","auth_org_name":"%s"}' \
        "$(devforge_sanitize_json_str "$gle")" "$(devforge_sanitize_json_str "$gln")" \
        "$(devforge_sanitize_json_str "$gge")" "$(devforge_sanitize_json_str "$ggn")" \
        "$(devforge_sanitize_json_str "$osu")" "$(devforge_sanitize_json_str "$host")" \
        "$(devforge_sanitize_json_str "$ae")" "$(devforge_sanitize_json_str "$au")" \
        "$(devforge_sanitize_json_str "$ou")" "$(devforge_sanitize_json_str "$onm")"
}

# Resolve authenticated SSO identity from Claude Code's local oauth account file.
# Reads ~/.claude.json -> oauthAccount.{emailAddress,accountUuid,organizationUuid,organizationName}.
# This is the only point in the flow that knows the AUTHENTICATED dev identity (SSO login)
# at action time — stamping it turns attribution from inference into a join.
# Best-effort: file missing / no oauthAccount (Bedrock/API-key) / no node+python3 -> all empty.
# Output: single line "email|account_uuid|org_uuid|org_name" (pipes/newlines in values
# replaced with spaces to protect the delimiter contract). Override path via
# DEVFORGE_CLAUDE_JSON for testing.
# Cross-platform: usa devforge_json_field (node→python3→degraded) per ogni campo.
devforge_resolve_auth_identity() {
    local claude_json="${DEVFORGE_CLAUDE_JSON:-${HOME}/.claude.json}"
    [ -f "$claude_json" ] || { printf '|||'; return 0; }
    local ae au ou onm
    ae=$(devforge_json_field "$claude_json" "oauthAccount.emailAddress" 2>/dev/null)
    au=$(devforge_json_field "$claude_json" "oauthAccount.accountUuid" 2>/dev/null)
    ou=$(devforge_json_field "$claude_json" "oauthAccount.organizationUuid" 2>/dev/null)
    onm=$(devforge_json_field "$claude_json" "oauthAccount.organizationName" 2>/dev/null)
    # Replace pipe/newline/CR/quote chars to protect the delimiter contract
    ae="${ae//|/ }"; ae="${ae//$'\n'/ }"; ae="${ae//$'\r'/ }"; ae="${ae//\"/ }"
    au="${au//|/ }"; au="${au//$'\n'/ }"; au="${au//$'\r'/ }"; au="${au//\"/ }"
    ou="${ou//|/ }"; ou="${ou//$'\n'/ }"; ou="${ou//$'\r'/ }"; ou="${ou//\"/ }"
    onm="${onm//|/ }"; onm="${onm//$'\n'/ }"; onm="${onm//$'\r'/ }"; onm="${onm//\"/ }"
    printf '%s|%s|%s|%s' "$ae" "$au" "$ou" "$onm"
}

# Raw cumulative session token total (from token-stats.json). Fallback 0 if the
# file/session dir is absent or no interpreter is available. Used to anchor token spend
# to outcomes/blocks (e.g. pr_merged) without computing anything in the producer.
# Cross-platform: usa devforge_json_field (node→python3→degraded); degrado a 0 già atteso.
devforge_session_token_total() {
    local f="${DEVFORGE_SESSION_DIR:-}/token-stats.json"
    if [ -n "${DEVFORGE_SESSION_DIR:-}" ] && [ -f "$f" ]; then
        local v
        v=$(devforge_json_field "$f" "total" 2>/dev/null)
        # devforge_json_field è solo per campi stringa; total è numerico ma
        # entrambi i rami (node+python3) lo convertono a stringa via String(v||"").
        # Se il valore è vuoto o non-numerico ricadiamo a 0.
        if [[ "$v" =~ ^[0-9]+$ ]]; then
            echo "$v"
        else
            echo 0
        fi
    else
        echo 0
    fi
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
    # Prefer pinned session user.json — cross-platform via devforge_json_field (node→python3→degraded)
    if [ -n "$DEVFORGE_SESSION_DIR" ] && [ -f "${DEVFORGE_SESSION_DIR}/user.json" ]; then
        local raw
        raw=$(devforge_json_field "${DEVFORGE_SESSION_DIR}/user.json" "raw" 2>/dev/null)
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
    # Prefer pinned session user.json — cross-platform via devforge_json_field (node→python3→degraded)
    if [ -n "$DEVFORGE_SESSION_DIR" ] && [ -f "${DEVFORGE_SESSION_DIR}/user.json" ]; then
        local src
        src=$(devforge_json_field "${DEVFORGE_SESSION_DIR}/user.json" "source" 2>/dev/null)
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

# Initialize per-session state directory and pin identity for the session lifetime.
# Cross-platform: usa devforge_json_field (node→python3→degraded) per leggere user.json.
devforge_init_session() {
    local sid
    sid=$(devforge_get_sid)
    DEVFORGE_SESSION_DIR="${HOME}/.claude/devforge-state/${sid}"
    DEVFORGE_PINNED_SID="$sid"
    if [ -f "${DEVFORGE_SESSION_DIR}/user.json" ]; then
        DEVFORGE_PINNED_USER=$(devforge_json_field "${DEVFORGE_SESSION_DIR}/user.json" "raw" 2>/dev/null)
        [ -n "$DEVFORGE_PINNED_USER" ] && DEVFORGE_PINNED_USER=$(devforge_canonicalize_user "$DEVFORGE_PINNED_USER")
        # Pin authenticated SSO identity from user.json.identity (additive; empty if absent)
        DEVFORGE_AUTH_EMAIL=$(devforge_json_field "${DEVFORGE_SESSION_DIR}/user.json" "identity.auth_email" 2>/dev/null)
        DEVFORGE_AUTH_ACCOUNT_UUID=$(devforge_json_field "${DEVFORGE_SESSION_DIR}/user.json" "identity.auth_account_uuid" 2>/dev/null)
    fi
    [ -z "$DEVFORGE_PINNED_USER" ] && DEVFORGE_PINNED_USER=$(devforge_get_user)
    export DEVFORGE_SESSION_DIR DEVFORGE_PINNED_USER DEVFORGE_PINNED_SID DEVFORGE_AUTH_EMAIL DEVFORGE_AUTH_ACCOUNT_UUID
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

# Derive org/repo slug from a git remote URL (SSH scp-form or HTTPS).
# Returns empty string if the slug cannot be derived (no URL, single-segment, etc.).
# Usage: devforge_repo_slug "<remote_url>"
# Examples:
#   git@gitlab.itsiae.it:itsiae/diritti-api.git  → itsiae/diritti-api
#   https://github.com/itsiae/diritti-api.git    → itsiae/diritti-api
#   https://github.com/itsiae/diritti-api        → itsiae/diritti-api
#   ""                                           → ""
devforge_repo_slug() {
    local url="$1"
    [ -n "$url" ] || { printf ''; return 0; }
    url="${url%.git}"             # strip trailing .git
    url="${url#*://}"             # strip scheme (https://, ssh://)
    url="${url#*@}"               # strip user@ (SSH)
    url="${url/://}"              # first ':' → '/' (SSH scp-form host:org/repo)
    local repo rest org
    repo="${url##*/}"
    rest="${url%/*}"
    org="${rest##*/}"
    if [ -n "$org" ] && [ -n "$repo" ] && [ "$org" != "$repo" ]; then
        printf '%s/%s' "$org" "$repo"
    else
        printf ''
    fi
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

    # Attribution determinism: repo_remote (git origin URL, RAW) + pinned auth identity.
    # repo_remote survives the GitLab->GitHub mirror; auth_* come from session pinning
    # (DEVFORGE_AUTH_*), no per-event re-read of ~/.claude.json. All best-effort (empty if absent).
    # repo_slug (org/repo) derived from repo_remote for join-key use at the consumer.
    local repo_remote auth_email_v auth_uuid_v safe_repo_remote safe_auth_email safe_auth_uuid safe_repo_slug
    repo_remote=$(git remote get-url origin 2>/dev/null || echo "")
    auth_email_v="${DEVFORGE_AUTH_EMAIL:-}"
    auth_uuid_v="${DEVFORGE_AUTH_ACCOUNT_UUID:-}"
    safe_repo_remote=$(devforge_sanitize_json_str "$repo_remote")
    safe_auth_email=$(devforge_sanitize_json_str "$auth_email_v")
    safe_auth_uuid=$(devforge_sanitize_json_str "$auth_uuid_v")
    safe_repo_slug=$(devforge_sanitize_json_str "$(devforge_repo_slug "$repo_remote")")

    # Zero-loss PR-A: build the JSON line once, then atomic append via Python
    # (lock + fsync, cross-OS). Replaces raw `>> file` to eliminate race.
    local json_line
    json_line=$(printf '{"event_id":"%s","schema_version":2,"session_seq":%s,"hook_name":"%s","actor_canonical":"%s","repo_root":"%s","project_canonical":"%s","repo_remote":"%s","repo_slug":"%s","auth_email":"%s","auth_account_uuid":"%s","ts":"%s","user":"%s","user_raw":"%s","user_source":"%s","sid":"%s","branch":"%s","jira_id":%s,"project":"%s","event":"%s","status":"%s","meta":%s}' \
        "$event_id" "$seq" "$hook_name" "$safe_user" "$safe_repo_root" "$safe_project_canonical" \
        "$safe_repo_remote" "$safe_repo_slug" "$safe_auth_email" "$safe_auth_uuid" \
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

    # Attribution determinism: repo_remote (git origin URL, RAW) + pinned auth identity.
    # See devforge_log for rationale. duration_ms stays between status and meta (unchanged).
    # repo_slug (org/repo) derived from repo_remote; duration_source="wallclock" is a
    # static marker that tells the consumer this duration was measured via epoch_ns wallclock.
    local repo_remote auth_email_v auth_uuid_v safe_repo_remote safe_auth_email safe_auth_uuid safe_repo_slug
    repo_remote=$(git remote get-url origin 2>/dev/null || echo "")
    auth_email_v="${DEVFORGE_AUTH_EMAIL:-}"
    auth_uuid_v="${DEVFORGE_AUTH_ACCOUNT_UUID:-}"
    safe_repo_remote=$(devforge_sanitize_json_str "$repo_remote")
    safe_auth_email=$(devforge_sanitize_json_str "$auth_email_v")
    safe_auth_uuid=$(devforge_sanitize_json_str "$auth_uuid_v")
    safe_repo_slug=$(devforge_sanitize_json_str "$(devforge_repo_slug "$repo_remote")")

    # Zero-loss PR-A: atomic append via Python (lock + fsync)
    local json_line
    json_line=$(printf '{"event_id":"%s","schema_version":2,"session_seq":%s,"hook_name":"%s","actor_canonical":"%s","repo_root":"%s","project_canonical":"%s","repo_remote":"%s","repo_slug":"%s","auth_email":"%s","auth_account_uuid":"%s","ts":"%s","user":"%s","user_raw":"%s","user_source":"%s","sid":"%s","branch":"%s","jira_id":%s,"project":"%s","event":"%s","status":"%s","duration_ms":%d,"duration_source":"wallclock","meta":%s}' \
        "$event_id" "$seq" "$hook_name" "$safe_user" "$safe_repo_root" "$safe_project_canonical" \
        "$safe_repo_remote" "$safe_repo_slug" "$safe_auth_email" "$safe_auth_uuid" \
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

# Portable JSON field reader: node first (Claude Code runs on Node), python3 fallback.
# Empty string + observable telemetry_degraded if no interpreter. Never aborts.
# Supports dotted paths (e.g. "oauthAccount.emailAddress", "identity.auth_email").
#
# IMPORTANTE — solo campi STRINGA identità:
#   Valori falsy (0, false, stringa vuota, null) sono INDISTINGUIBILI da chiave mancante
#   in entrambi i rami (node: `v||""` → ""; python3: `str(v or "")` → "").
#   Non usare questa funzione per campi booleani o numerici: il risultato sarà sempre "".
#
# Anti-ricorsione: nel percorso DEGRADED (node e python3 entrambi assenti), la chiamata
# a devforge_log("telemetry_degraded") raggiunge devforge_get_user_raw e
# devforge_get_user_source, che a loro volta chiamano devforge_json_field di nuovo se
# DEVFORGE_SESSION_DIR è impostato e user.json esiste — producendo un loop infinito.
# Scenario reale: Windows senza node E senza python3 con user.json presente.
# La guardia _DEVFORGE_JF_DEGRADING=1 (inline env-var scoping) interrompe il ciclo:
# qualsiasi chiamata rientrante vede la variabile impostata e salta l'emissione,
# restituendo stringa vuota immediatamente senza ulteriori ricorsioni.
devforge_json_field() {
    local file="$1" path="$2" out=""
    [ -f "$file" ] || { printf ''; return 0; }
    if command -v node >/dev/null 2>&1; then
        out=$(node -e 'try{const fs=require("fs");const d=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));const v=process.argv[2].split(".").reduce((o,k)=>(o&&o[k]!=null)?o[k]:"",d);process.stdout.write(String(v||""))}catch(e){process.exit(3)}' "$file" "$path" 2>/dev/null) && { printf '%s' "$out"; return 0; }
    fi
    if command -v python3 >/dev/null 2>&1; then
        out=$(python3 -c 'import json,sys,functools
d=json.load(open(sys.argv[1], encoding="utf-8"))
v=functools.reduce(lambda o,k:(o.get(k,"") if isinstance(o,dict) else ""),sys.argv[2].split("."),d)
sys.stdout.write(str(v or ""))' "$file" "$path" 2>/dev/null) && { printf '%s' "$out"; return 0; }
    fi
    # DEGRADED: neither node nor python3 available.
    # Re-entry guard: if we are already inside the degraded-log emission path
    # (devforge_log → get_user_raw/get_user_source → devforge_json_field),
    # skip the log call to break the infinite recursion cycle.
    # The guard uses inline env-var scoping so every child call in this subshell
    # chain sees _DEVFORGE_JF_DEGRADING=1 and returns immediately.
    if [ -z "${_DEVFORGE_JF_DEGRADING:-}" ]; then
        _DEVFORGE_JF_DEGRADING=1 devforge_log "telemetry_degraded" "warning" '{"reason":"no_json_interpreter"}' 2>/dev/null || true
    fi
    printf ''
}
