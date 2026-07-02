#!/usr/bin/env bash
# diff-risk-classifier.sh — classifica il rischio di un diff per lo scaling dei gate PR.
# Output (stdout): 'low' (solo doc/manifest) | 'code' (qualsiasi altro / dubbio).
# Fail-safe: ogni errore o dubbio → 'code' (mai 'low' per accidente).
# Design: docs/plans/2026-06-19-pr-gate-proportional-scaling-design.md

# True se il path è low-risk: estensione documentale OR manifest plugin per path esatto.
_devforge_path_is_lowrisk() {
    case "$1" in
        *.md|*.txt|*.rst|*.pdf|*.png|*.jpg|*.jpeg|*.svg) return 0 ;;
        .claude-plugin/plugin.json|.claude-plugin/marketplace.json) return 0 ;;
        *) return 1 ;;
    esac
}

# Stampa 'low' | 'code'. $1 = base branch (OBBLIGATORIO: il chiamante DEVE
# risolvere il base reale via lib/pr-base-resolver.sh — REQ-DF-03, niente default origin/main).
devforge_classify_diff_risk() {
    local base="${1:?devforge_classify_diff_risk richiede un base esplicito (usa devforge_resolve_pr_base)}"
    local status
    status=$(git diff --name-status "${base}...HEAD" 2>/dev/null) || { printf 'code'; return 0; }
    [ -z "$status" ] && { printf 'code'; return 0; }
    local line op p1 p2
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        op=$(printf '%s' "$line" | cut -f1)
        case "$op" in
            R*)  # rename: cut -f2 = OLD, cut -f3 = NEW — entrambi devono essere low-risk
                p1=$(printf '%s' "$line" | cut -f2)
                p2=$(printf '%s' "$line" | cut -f3)
                _devforge_path_is_lowrisk "$p1" || { printf 'code'; return 0; }
                _devforge_path_is_lowrisk "$p2" || { printf 'code'; return 0; }
                ;;
            *)
                p1=$(printf '%s' "$line" | cut -f2)
                _devforge_path_is_lowrisk "$p1" || { printf 'code'; return 0; }
                ;;
        esac
    done <<EOF
$status
EOF
    printf 'low'
}
