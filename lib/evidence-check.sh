#!/usr/bin/env bash
# evidence-check.sh — Verify skill meaningful-use via validates_via predicate
# ─────────────────────────────────────────────────────────────────
# Part of: PR #1 anti-dilution (ADR-002 Evidence Contract)
# Used by: gate hooks in PR #2 (dual-write cutover)
# ─────────────────────────────────────────────────────────────────

# devforge_skill_validated SKILL_NAME [TASK_ID]
# Returns 0 if the skill is validated for this context.
#
# Precedence (PR #2 task-scope wiring):
#   1. If TASK_ID is provided AND the ledger file
#      ~/.claude/.devforge-task-skills/<task_id>/skills_validated
#      contains SKILL_NAME (exact match), return 0 immediately.
#      This is the only path that discriminates between two tasks in the
#      same session.
#   2. Otherwise, run the session-wide predicate check (PR #1 behaviour).
#      If the predicate passes AND task_id is non-empty, record the skill
#      in the ledger so future invocations short-circuit at step 1 — and
#      so `devforge_task_id_transition` has real evidence to copy forward
#      on design-doc revision.
devforge_skill_validated() {
    local skill="${1:?skill name required}"
    local task_id="${2:-}"
    local predicate_result=1

    # Task-scoped ledger check (PR #2 wiring)
    if [ -n "$task_id" ]; then
        local ledger="${HOME}/.claude/.devforge-task-skills/${task_id}/skills_validated"
        if [ -f "$ledger" ] && grep -qxF "$skill" "$ledger" 2>/dev/null; then
            return 0
        fi
    fi

    # Session-wide predicate check (PR #1 behaviour)
    case "$skill" in
        siae-tdd)
            _devforge_check_tdd_red_green && predicate_result=0
            ;;
        siae-brainstorming)
            _devforge_check_design_doc_produced && predicate_result=0
            ;;
        siae-git-workflow)
            _devforge_check_conventional_commit && predicate_result=0
            ;;
        siae-verification)
            _devforge_check_verification_run_passed && predicate_result=0
            ;;
        siae-blind-review)
            _devforge_check_blind_review_completed && predicate_result=0
            ;;
        *)
            predicate_result=1
            ;;
    esac

    # Cache success into task ledger so the next call on the same task
    # short-circuits (and evidence copy-forward has something to copy).
    if [ "$predicate_result" = "0" ] && [ -n "$task_id" ]; then
        local dir="${HOME}/.claude/.devforge-task-skills/${task_id}"
        mkdir -p "$dir"
        local vfile="${dir}/skills_validated"
        touch "$vfile"
        if ! grep -qxF "$skill" "$vfile" 2>/dev/null; then
            printf '%s\n' "$skill" >> "$vfile"
        fi
    fi

    return "$predicate_result"
}

_devforge_check_tdd_red_green() {
    local state_file="${HOME}/.claude/.devforge-tdd-state"
    [ -f "$state_file" ] || return 1
    local phase
    phase="$(cut -d'|' -f1 < "$state_file")"
    case "$phase" in
        GREEN|REFACTOR) return 0 ;;
        *) return 1 ;;
    esac
}

_devforge_check_design_doc_produced() {
    local session_start="${DEVFORGE_SESSION_START_S:-0}"
    [ -d docs/plans ] || return 1
    local latest
    latest=$(ls -1t docs/plans/*-design.md 2>/dev/null | head -1)
    [ -n "$latest" ] && [ -f "$latest" ] || return 1
    local mtime
    mtime=$(stat -f %m "$latest" 2>/dev/null || stat -c %Y "$latest" 2>/dev/null || echo 0)
    [ "$mtime" -ge "$session_start" ]
}

_devforge_check_conventional_commit() {
    # Must be inside a git repo
    git rev-parse --git-dir >/dev/null 2>&1 || return 1
    local msg
    msg=$(git log -1 --format=%s 2>/dev/null) || return 1
    [ -n "$msg" ] || return 1
    # Conventional Commits regex (permissive, accepts ! for breaking changes)
    echo "$msg" | grep -qE '^(feat|fix|chore|docs|refactor|test|style|perf|build|ci|revert)(\([^)]+\))?!?:'
}

_devforge_check_verification_run_passed() {
    local log_file="${DEVFORGE_LOG_FILE:-}"
    [ -n "$log_file" ] && [ -f "$log_file" ] || return 1
    local sid="${DEVFORGE_SESSION_ID:-}"
    if [ -n "$sid" ]; then
        grep -E "\"sid\":\"$sid\"" "$log_file" 2>/dev/null | \
            grep -E '"event":"verification_run"' | \
            grep -qE '"exit":0' || return 1
    else
        grep -E '"event":"verification_run"' "$log_file" 2>/dev/null | \
            grep -qE '"exit":0' || return 1
    fi
    return 0
}

_devforge_check_blind_review_completed() {
    local log_file="${DEVFORGE_LOG_FILE:-}"
    [ -n "$log_file" ] && [ -f "$log_file" ] || return 1
    local sid="${DEVFORGE_SESSION_ID:-}"
    if [ -n "$sid" ]; then
        grep -E "\"sid\":\"$sid\"" "$log_file" 2>/dev/null | \
            grep -qE '"event":"blind_review_verdict"' || return 1
    else
        grep -qE '"event":"blind_review_verdict"' "$log_file" 2>/dev/null || return 1
    fi
    return 0
}
