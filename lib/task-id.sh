#!/usr/bin/env bash
# task-id.sh — task-scoped enforcement primitives (ADR-001)
# ─────────────────────────────────────────────────────────────────
# Source-only library. No side effects on load. All side effects
# happen inside function calls.
#
# Used by: tdd-gate, brainstorming-gate, stop-gate, pre-commit,
# pr-blind-review-gate, plan-gate-write (PR #2 dual-write cutover).
#
# Task identity:
#   task_id = sha256(branch_name + "|" + design_doc_path + "|" + design_doc_mtime)[:12]
#
# Scope: only evaluated on itsiae/* repos. Outside scope = empty task_id,
# which the gates treat as "no-op" (early-exit).
# ─────────────────────────────────────────────────────────────────

# _devforge_taskid_sha256 — portable SHA-256 wrapper (issue #238).
# DUPLICATED (not imported) from logger.sh because task-id.sh is a
# source-only library per the header contract above — it does not declare
# a hard dependency on logger.sh and may be sourced standalone (e.g. by
# diagnostic scripts or future unit tests). Maintainers: keep this body
# byte-identical to _devforge_shasum (modulo -a 256) and add b2sum/other
# backends in BOTH places atomically.
_devforge_taskid_sha256() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum
    else
        cat >/dev/null
        printf '0000000000000000000000000000000000000000000000000000000000000000  -\n'
    fi
}

# devforge_compute_task_id
# Emits the current 12-char hex task_id on stdout, or an empty string if
# we are outside an itsiae/* repo (or outside any git repo).
devforge_compute_task_id() {
    # Must be inside a git worktree
    git rev-parse --git-dir >/dev/null 2>&1 || { printf ''; return 0; }

    # Must be an itsiae/* remote. Match both HTTPS (/itsiae/) and SSH
    # (:itsiae/) so "notitsiae" does not slip through.
    local remote
    remote=$(git remote get-url origin 2>/dev/null || true)
    if ! printf '%s' "$remote" | grep -qE '[/:]itsiae/'; then
        printf ''
        return 0
    fi

    local branch design_doc design_mtime material
    branch=$(git branch --show-current 2>/dev/null || echo "")
    # Detached HEAD: prefer a stable reference (tag / tracking branch) over
    # the raw HEAD sha — an amend or interactive rebase changes the sha and
    # would pointlessly invalidate the task_id. Fall back to short-sha only
    # when nothing else resolves.
    if [ -z "$branch" ]; then
        local ref
        ref=$(git describe --all --contains HEAD 2>/dev/null | sed 's@.*/@@' || true)
        if [ -z "$ref" ] || [ "$ref" = "HEAD" ]; then
            ref=$(git rev-parse --short HEAD 2>/dev/null || echo nohead)
        fi
        branch="detached@${ref}"
    fi

    design_doc=""
    design_mtime=0
    if [ -d docs/plans ]; then
        design_doc=$(ls -1t docs/plans/*-design.md 2>/dev/null | head -1 || true)
        if [ -n "$design_doc" ] && [ -f "$design_doc" ]; then
            design_mtime=$(stat -f%m "$design_doc" 2>/dev/null \
                || stat -c%Y "$design_doc" 2>/dev/null || echo 0)
        fi
    fi

    material="${branch}|${design_doc}|${design_mtime}"
    # Portable shasum/sha256sum wrapper — see _devforge_taskid_sha256 at top of file.
    printf '%s' "$material" | _devforge_taskid_sha256 | awk '{print $1}' | cut -c1-12
}

# devforge_task_id_transition OLD_ID NEW_ID
# When the task_id changes mid-session (typically because the design doc
# was revised), preserve progress by copying forward skills_validated if
# branch and design_doc path are unchanged. Any other change (branch
# switch, different design doc) is treated as a legitimately new task,
# so nothing is copied.
#
# No-ops silently if either side is missing — callers shouldn't guard.
devforge_task_id_transition() {
    local old_id="${1:-}" new_id="${2:-}"
    [ -z "$old_id" ] && return 0
    [ -z "$new_id" ] && return 0
    [ "$old_id" = "$new_id" ] && return 0

    local old_dir="${HOME}/.claude/.devforge-task-skills/${old_id}"
    local new_dir="${HOME}/.claude/.devforge-task-skills/${new_id}"
    [ -d "$old_dir" ] || return 0
    [ -f "${old_dir}/metadata" ] || return 0

    # Parse metadata: simple key=value lines
    local old_branch old_design new_branch new_design
    old_branch=$(grep -E '^branch_name=' "${old_dir}/metadata" 2>/dev/null | head -1 | cut -d= -f2- || echo '')
    old_design=$(grep -E '^design_doc=' "${old_dir}/metadata" 2>/dev/null | head -1 | cut -d= -f2- || echo '')
    new_branch=""
    new_design=""
    if [ -f "${new_dir}/metadata" ]; then
        new_branch=$(grep -E '^branch_name=' "${new_dir}/metadata" 2>/dev/null | head -1 | cut -d= -f2- || echo '')
        new_design=$(grep -E '^design_doc=' "${new_dir}/metadata" 2>/dev/null | head -1 | cut -d= -f2- || echo '')
    fi

    # Only copy forward if branch AND design_doc path are unchanged.
    if [ "$old_branch" != "$new_branch" ] || [ "$old_design" != "$new_design" ]; then
        return 0
    fi

    mkdir -p "$new_dir"
    # Copy both invoked + validated (validated is the load-bearing evidence)
    for f in skills_invoked skills_validated; do
        if [ -f "${old_dir}/${f}" ]; then
            # Append-safe merge: dedup union of old + existing new
            local tmp; tmp=$(mktemp)
            { [ -f "${new_dir}/${f}" ] && cat "${new_dir}/${f}"; cat "${old_dir}/${f}"; } \
                | awk 'NF && !seen[$0]++' > "$tmp"
            mv "$tmp" "${new_dir}/${f}"
        fi
    done
    return 0
}

# Internal: append SKILL_NAME to FILE if not already present. Uses flock when
# available to make concurrent appends atomic.
_devforge_atomic_append() {
    local file="$1" line="$2"
    local dir; dir=$(dirname "$file")
    mkdir -p "$dir"
    touch "$file"
    if command -v flock >/dev/null 2>&1; then
        (
            flock -x 9
            grep -qxF "$line" "$file" 2>/dev/null || printf '%s\n' "$line" >> "$file"
        ) 9>>"$file.lock"
        rm -f "$file.lock" 2>/dev/null || true
    else
        # macOS default ships no flock(1). Fall back to O_APPEND write, which
        # guarantees line-atomic writes up to PIPE_BUF (>= 4096 on darwin/linux)
        # for payloads of a single short skill name.
        if ! grep -qxF "$line" "$file" 2>/dev/null; then
            printf '%s\n' "$line" >> "$file"
        fi
    fi
}

# devforge_task_skill_invoked TASK_ID SKILL_NAME
# Record that SKILL_NAME was invoked inside TASK_ID's scope. Idempotent.
devforge_task_skill_invoked() {
    local task_id="${1:?task_id required}" skill="${2:?skill name required}"
    _devforge_atomic_append "${HOME}/.claude/.devforge-task-skills/${task_id}/skills_invoked" "$skill"
}

# devforge_task_skill_validated TASK_ID SKILL_NAME
# Exit 0 if SKILL_NAME has been marked as validated for TASK_ID, else non-zero.
devforge_task_skill_validated() {
    local task_id="${1:?task_id required}" skill="${2:?skill name required}"
    local f="${HOME}/.claude/.devforge-task-skills/${task_id}/skills_validated"
    [ -f "$f" ] && grep -qxF "$skill" "$f"
}

# devforge_task_skill_mark_validated TASK_ID SKILL_NAME
# Mark SKILL_NAME as validated for TASK_ID (caller has already confirmed
# the validates_via predicate). Idempotent.
devforge_task_skill_mark_validated() {
    local task_id="${1:?task_id required}" skill="${2:?skill name required}"
    _devforge_atomic_append "${HOME}/.claude/.devforge-task-skills/${task_id}/skills_validated" "$skill"
}
