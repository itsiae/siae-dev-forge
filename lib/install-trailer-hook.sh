#!/usr/bin/env bash
# DevForge — installer for the prepare-commit-msg "DevForge-Author" trailer hook.
#
# Stamps `DevForge-Author: <sso-email>` into each commit so the authenticated
# author survives the GitLab->GitHub mirror (which rewrites git author/committer),
# even outside telemetry — any consumer can recover the real author from the commit.
#
# Idempotent, zero-harm (never clobbers a foreign prepare-commit-msg), best-effort.
# Invoked from hooks/session-start. Per saltare un singolo commit: git commit --no-verify.
#
# Return codes: 0 = installed/refreshed/not-applicable; 2 = skipped (foreign hook present).

devforge_install_trailer_hook() {
    command -v git >/dev/null 2>&1 || return 0
    git rev-parse --git-dir >/dev/null 2>&1 || return 0   # not inside a git repo

    local hooks_dir target marker base_marker
    hooks_dir=$(git rev-parse --git-path hooks 2>/dev/null) || return 0
    [ -n "$hooks_dir" ] || return 0
    mkdir -p "$hooks_dir" 2>/dev/null || return 0
    target="${hooks_dir}/prepare-commit-msg"
    marker="# DEVFORGE-TRAILER-HOOK v2"
    # Base prefix shared by all DevForge-owned versions of this hook.
    # Version bump (v1→v2, v2→v3, …) intentionally triggers re-deploy of the
    # hook content; both old and new versions are "owned" by DevForge and must
    # be overwritten.  Only hooks that lack the base marker entirely (husky,
    # commitlint, custom team scripts, …) are truly foreign and must be preserved.
    base_marker="# DEVFORGE-TRAILER-HOOK"

    # Zero-harm: a prepare-commit-msg without our base marker is a foreign hook
    # (husky, custom). Never clobber it — skip and let the caller log it.
    # A hook that carries the base marker (any version) is DevForge-owned and
    # will be refreshed to the current version below.
    if [ -f "$target" ] && ! grep -qF "$base_marker" "$target" 2>/dev/null; then
        return 2
    fi

    # Guard: capability check for git interpret-trailers + version >= 2.15.
    # On failure: emit install-time telemetry if devforge_log is available
    # (it is when called from session-start which already sourced logger.sh).
    # Install the hook anyway (best-effort) — the hook itself handles runtime failure.
    local _git_ver_raw _git_ver_ok
    _git_ver_raw=$(git --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "0.0.0")
    _git_ver_ok=0
    if git interpret-trailers --help >/dev/null 2>&1; then
        # Parse major.minor and compare >= 2.15
        local _maj _min
        _maj=$(printf '%s' "$_git_ver_raw" | cut -d. -f1)
        _min=$(printf '%s' "$_git_ver_raw" | cut -d. -f2)
        if [ "${_maj:-0}" -gt 2 ] || { [ "${_maj:-0}" -eq 2 ] && [ "${_min:-0}" -ge 15 ]; }; then
            _git_ver_ok=1
        fi
    fi
    if [ "$_git_ver_ok" -eq 0 ]; then
        if command -v devforge_log >/dev/null 2>&1; then
            devforge_log "trailer_hook_skipped_old_git" "warning" \
                "{\"git_version\":\"${_git_ver_raw}\"}" 2>/dev/null || true
        fi
        # Fall through: install the hook anyway (best-effort)
    fi

    # Write (or refresh) our self-contained hook. Quoted heredoc: the hook's own
    # variables ($1, ${EMAIL}, $(...)) are written literally, not expanded now.
    cat > "$target" <<'HOOK'
#!/usr/bin/env bash
# DEVFORGE-TRAILER-HOOK v2
# Stamps "DevForge-Author: <sso-email>" so the authenticated author survives the
# GitLab->GitHub mirror, even outside telemetry. Best-effort; NEVER blocks a commit.
set +e
MSG_FILE="$1"; SRC="${2:-}"
# No single meaningful author for merge/squash commits.
case "$SRC" in merge|squash) exit 0 ;; esac
# Resolve authenticated SSO email from Claude Code's local oauth account (best-effort).
# Self-contained node→python3 chain (this hook does NOT source logger.sh).
CJ="${DEVFORGE_CLAUDE_JSON:-${HOME}/.claude.json}"
EMAIL=""
if [ -f "$CJ" ]; then
    if command -v node >/dev/null 2>&1; then
        EMAIL=$(node -e 'try{const fs=require("fs");process.stdout.write(String((JSON.parse(fs.readFileSync(process.argv[1],"utf8")).oauthAccount||{}).emailAddress||""))}catch(e){process.exit(3)}' "$CJ" 2>/dev/null)
    fi
    if [ -z "$EMAIL" ] && command -v python3 >/dev/null 2>&1; then
        EMAIL=$(python3 -c "import json,sys;print((json.load(open(sys.argv[1])).get('oauthAccount') or {}).get('emailAddress','') or '')" "$CJ" 2>/dev/null)
    fi
fi
# Strip control chars and quotes. Also strip ':' to prevent colon-injection into the
# trailer value from a tampered ~/.claude.json (local file, best-effort defence).
# Valid email addresses never contain ':', so this does not affect legitimate values.
EMAIL=$(printf '%s' "$EMAIL" | tr -d '\n\r":')
[ -z "$EMAIL" ] && exit 0
[ -f "$MSG_FILE" ] || exit 0
command -v git >/dev/null 2>&1 || exit 0
# --in-place: on failure, the message file is left untouched (no data loss).
# --if-exists doNothing: idempotent per-token (amend/re-run never duplicate).
# Capture exit code: on failure do NOT write trailer but always exit 0 (never block commit).
git interpret-trailers --in-place --if-exists doNothing \
    --trailer "DevForge-Author: ${EMAIL}" "$MSG_FILE"
_trailer_rc=$?
[ "$_trailer_rc" -ne 0 ] && exit 0
exit 0
HOOK
    chmod +x "$target" 2>/dev/null || true
    return 0
}

# Allow both `bash install-trailer-hook.sh` (execute) and `source` (test).
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    devforge_install_trailer_hook
    exit $?
fi
