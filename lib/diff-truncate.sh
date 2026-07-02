#!/usr/bin/env bash
# diff-truncate.sh — evita hang/loop su diff enormi tra branch (REQ-DF-03).
# Se il diff supera DEVFORGE_MAX_DIFF_LINES righe, emette --stat + --name-only +
# nota di troncamento esplicita invece del diff completo. Non blocca mai (return 0).
# Design: docs/plans/2026-07-01-devforge-siae-conventions-and-flow/design.md

# devforge_diff_or_summary <base> [max_lines]
# $1 = base branch/ref (es. "origin/main", "main", risultato di devforge_resolve_pr_base)
# $2 = soglia righe (default: $DEVFORGE_MAX_DIFF_LINES, o 2000 se non settata)
# Stdout: diff completo (sotto soglia) oppure stat+name-only+nota (sopra soglia).
# Return: sempre 0 (fail-safe, mai hang).
devforge_diff_or_summary() {
    local base="${1:-}"
    local max_lines="${2:-${DEVFORGE_MAX_DIFF_LINES:-2000}}"
    [ -z "$base" ] && { printf 'diff troncato oltre %s righe — richiedi i file mancanti on-demand (base non specificata)\n' "$max_lines"; return 0; }

    local full_diff line_count
    full_diff=$(git diff "${base}...HEAD" 2>/dev/null) || { printf ''; return 0; }
    [ -z "$full_diff" ] && return 0

    line_count=$(printf '%s\n' "$full_diff" | wc -l | tr -d ' ')

    if [ "$line_count" -le "$max_lines" ]; then
        printf '%s\n' "$full_diff"
        return 0
    fi

    git diff --stat "${base}...HEAD" 2>/dev/null
    printf '\n'
    git diff --name-only "${base}...HEAD" 2>/dev/null
    printf '\ndiff troncato oltre %s righe — richiedi i file mancanti on-demand\n' "$max_lines"
    return 0
}
