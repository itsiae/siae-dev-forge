#!/usr/bin/env bash
# block-explainer.sh — PR #3 / ADR-009.
#
# Provides devforge_block_explainer SKILL_NAME which echoes a single-line
# suffix like "La tua adoption siae-tdd: 42% · team median: 78%" for gate
# block messages. Cached for 24h to avoid fork-bombing Python on every
# block.
#
# Opt-out: DEVFORGE_DISABLE_EXPLAINER=1.

_DEVFORGE_EXPLAINER_CACHE_DIR="${HOME}/.claude/.devforge-explainer-cache"
_DEVFORGE_EXPLAINER_TTL_SEC=86400  # 24h

# devforge_block_explainer SKILL_NAME
# Prints one line to stdout, or nothing if disabled / Python missing.
devforge_block_explainer() {
    [ "${DEVFORGE_DISABLE_EXPLAINER:-0}" = "1" ] && return 0
    local skill="${1:-}"
    [ -z "$skill" ] && return 0

    local analyzer="${PLUGIN_ROOT:-}"
    [ -z "$analyzer" ] && return 0
    analyzer="${analyzer}/lib/adoption-analyzer.py"
    [ -f "$analyzer" ] || return 0
    command -v python3 >/dev/null 2>&1 || return 0

    mkdir -p "$_DEVFORGE_EXPLAINER_CACHE_DIR"
    local cache="${_DEVFORGE_EXPLAINER_CACHE_DIR}/${skill}"
    local now; now=$(date +%s)
    if [ -f "$cache" ]; then
        local mtime
        mtime=$(stat -f %m "$cache" 2>/dev/null || stat -c %Y "$cache" 2>/dev/null || echo 0)
        if [ $((now - mtime)) -lt "$_DEVFORGE_EXPLAINER_TTL_SEC" ]; then
            cat "$cache"
            return 0
        fi
    fi

    local line
    line=$(python3 "$analyzer" --format block --skill "$skill" 2>/dev/null || true)
    [ -z "$line" ] && return 0
    printf '%s\n' "$line" > "$cache" 2>/dev/null || true
    printf '%s' "$line"
}
