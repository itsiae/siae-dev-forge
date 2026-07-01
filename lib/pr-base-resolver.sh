#!/usr/bin/env bash
# pr-base-resolver.sh — risolve il branch base corretto per una PR/diff.
# Precedenza: (1) PR esistente per il branch corrente (gh pr view); (2)
# merge-base distance voting su origin/release/* + origin/sviluppo; (3)
# git symbolic-ref refs/remotes/origin/HEAD; (4) letterale 'main'.
# Design: docs/plans/2026-07-01-devforge-siae-conventions-and-flow/design.md (REQ-DF-03)
# Algoritmo (2) da: skills/siae-finishing-branch/reference/finishing-branch-checklist.md:75-83

# _devforge_pr_base_from_gh — stampa baseRefName se una PR esiste per HEAD, altrimenti niente.
# Fail-safe: qualsiasi errore (gh assente, non autenticato, nessuna PR) → stdout vuoto.
_devforge_pr_base_from_gh() {
    command -v gh >/dev/null 2>&1 || return 1
    local base
    base=$(gh pr view --json baseRefName -q .baseRefName 2>/dev/null) || return 1
    [ -n "$base" ] || return 1
    printf '%s' "$base"
}

# _devforge_pr_base_from_voting — merge-base distance voting su
# origin/release/* + origin/sviluppo. Il candidato con distanza minore
# (git rev-list --count) vince. Stampa niente se nessun candidato esiste.
_devforge_pr_base_from_voting() {
    local candidates candidate merge_base distance
    local best_name="" best_distance=""
    candidates=$(git branch -r --list 'origin/release/*' --list 'origin/sviluppo' 2>/dev/null \
        | sed 's/^[[:space:]]*//' | sed 's#^origin/##')
    [ -n "$candidates" ] || return 1
    while IFS= read -r candidate; do
        [ -z "$candidate" ] && continue
        merge_base=$(git merge-base HEAD "origin/${candidate}" 2>/dev/null) || continue
        distance=$(git rev-list --count "${merge_base}..HEAD" 2>/dev/null) || continue
        if [ -z "$best_distance" ] || [ "$distance" -lt "$best_distance" ]; then
            best_distance="$distance"
            best_name="$candidate"
        fi
    done <<EOF
$candidates
EOF
    [ -n "$best_name" ] || return 1
    printf '%s' "$best_name"
}

# _devforge_pr_base_from_symbolic_ref — HEAD simbolico di origin (default branch remoto).
_devforge_pr_base_from_symbolic_ref() {
    local ref
    ref=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null) || return 1
    [ -n "$ref" ] || return 1
    printf '%s' "${ref#refs/remotes/origin/}"
}

# devforge_resolve_pr_base — stampa su stdout il branch base risolto.
# Non fallisce mai: l'ultimo fallback è il letterale 'main'.
devforge_resolve_pr_base() {
    local result
    result=$(_devforge_pr_base_from_gh) && [ -n "$result" ] && { printf '%s\n' "$result"; return 0; }
    result=$(_devforge_pr_base_from_voting) && [ -n "$result" ] && { printf '%s\n' "$result"; return 0; }
    result=$(_devforge_pr_base_from_symbolic_ref) && [ -n "$result" ] && { printf '%s\n' "$result"; return 0; }
    printf '%s\n' "main"
}
