#!/usr/bin/env bash
# DevForge — installer for the prepare-commit-msg "DevForge-Author" trailer hook.
#
# Stamps `DevForge-Author: <sso-email>` into each commit so the authenticated
# author survives the GitLab->GitHub mirror (which rewrites git author/committer),
# even outside telemetry — any consumer can recover the real author from the commit.
#
# Idempotent, zero-harm (never clobbers a foreign prepare-commit-msg), best-effort.
# Invoked from hooks/session-start. Opt-out: DEVFORGE_SKIP_TRAILER_HOOK=1.
#
# Return codes: 0 = installed/refreshed/not-applicable; 2 = skipped (foreign hook present).

devforge_install_trailer_hook() {
    [ "${DEVFORGE_SKIP_TRAILER_HOOK:-}" = "1" ] && return 0
    command -v git >/dev/null 2>&1 || return 0
    git rev-parse --git-dir >/dev/null 2>&1 || return 0   # not inside a git repo

    local hooks_dir target marker
    hooks_dir=$(git rev-parse --git-path hooks 2>/dev/null) || return 0
    [ -n "$hooks_dir" ] || return 0
    mkdir -p "$hooks_dir" 2>/dev/null || return 0
    target="${hooks_dir}/prepare-commit-msg"
    marker="# DEVFORGE-TRAILER-HOOK v1"

    # Zero-harm: a prepare-commit-msg without our marker is a foreign hook
    # (husky, custom). Never clobber it — skip and let the caller log it.
    if [ -f "$target" ] && ! grep -qF "$marker" "$target" 2>/dev/null; then
        return 2
    fi

    # Write (or refresh) our self-contained hook. Quoted heredoc: the hook's own
    # variables ($1, ${EMAIL}, $(...)) are written literally, not expanded now.
    cat > "$target" <<'HOOK'
#!/usr/bin/env bash
# DEVFORGE-TRAILER-HOOK v1
# Stamps "DevForge-Author: <sso-email>" so the authenticated author survives the
# GitLab->GitHub mirror, even outside telemetry. Best-effort; NEVER blocks a commit.
set +e
MSG_FILE="$1"; SRC="${2:-}"
# No single meaningful author for merge/squash commits.
case "$SRC" in merge|squash) exit 0 ;; esac
# Resolve authenticated SSO email from Claude Code's local oauth account (best-effort).
CJ="${DEVFORGE_CLAUDE_JSON:-${HOME}/.claude.json}"
EMAIL=""
if [ -f "$CJ" ] && command -v python3 >/dev/null 2>&1; then
    EMAIL=$(python3 -c "import json,sys;print((json.load(open(sys.argv[1])).get('oauthAccount') or {}).get('emailAddress','') or '')" "$CJ" 2>/dev/null)
fi
EMAIL=$(printf '%s' "$EMAIL" | tr -d '\n\r')
[ -z "$EMAIL" ] && exit 0
[ -f "$MSG_FILE" ] || exit 0
command -v git >/dev/null 2>&1 || exit 0
# --in-place: on failure, the message file is left untouched (no data loss).
# --if-exists doNothing: idempotent per-token (amend/re-run never duplicate).
git interpret-trailers --in-place --if-exists doNothing \
    --trailer "DevForge-Author: ${EMAIL}" "$MSG_FILE" 2>/dev/null
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
