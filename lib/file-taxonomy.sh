#!/usr/bin/env bash
# file-taxonomy.sh — extension and path classification for DevForge gates (ADR-005)
# ─────────────────────────────────────────────────────────────────
# Source-only library. Centralizes the "which extension triggers which gate"
# decision so hooks/tdd-gate and hooks/brainstorming-gate stop duplicating
# regexes and stay in sync.
#
# Classes:
#   tdd_required           .java .ts .tsx .js .jsx .py .vue .go .kt
#                          .rb .rs .swift .scala .sql
#   brainstorming_only     .tf .hcl        (superset = tdd_required + these)
#   config_only            .yaml .yml .json .toml .ini .properties
#   ambiguous              .sh .bash       — deny by default, opt-in via
#                                           DEVFORGE_BASH_TDD=1
#   always_excluded        anything under test/ tests/ __tests__ spec/ docs/
#                          plans/ evals/, or matching *.spec.* *.test.*
#                          *Test.java/kt *IT.java/kt test_*.py *_test.go,
#                          or .md
# ─────────────────────────────────────────────────────────────────

# _devforge_file_excluded PATH
# Return 0 if PATH sits under a DevForge-excluded location (tests, docs, md).
_devforge_file_excluded() {
    local f="$1"

    # Markdown — always excluded
    case "$f" in *.md) return 0 ;; esac

    # Test directories anywhere in the path
    case "$f" in
        test/*|*/test/*|\
        tests/*|*/tests/*|\
        __tests__/*|*/__tests__/*|\
        spec/*|*/spec/*|\
        docs/*|*/docs/*|\
        plans/*|*/plans/*|\
        evals/*|*/evals/*) return 0 ;;
    esac

    # Test file naming conventions
    case "$f" in
        *.spec.*|*.test.*) return 0 ;;
        *Test.java|*Test.kt|*IT.java|*IT.kt) return 0 ;;
        test_*.py|*/test_*.py) return 0 ;;
        *_test.go) return 0 ;;
    esac

    return 1
}

# devforge_file_requires_tdd PATH
# Return 0 if PATH is production source code that must go through tdd-gate.
devforge_file_requires_tdd() {
    local f="${1:-}"
    [ -z "$f" ] && return 1

    # Exclusions win over extension matches.
    _devforge_file_excluded "$f" && return 1

    case "$f" in
        *.java|*.ts|*.tsx|*.js|*.jsx|*.py|*.vue|*.go|*.kt|\
        *.rb|*.rs|*.swift|*.scala|*.sql) return 0 ;;
        *.sh|*.bash)
            # Ambiguous class — opt-in only, so DevForge's own shell hooks
            # do not deadlock themselves.
            [ "${DEVFORGE_BASH_TDD:-0}" = "1" ] && return 0
            return 1
            ;;
        *) return 1 ;;
    esac
}

# devforge_file_requires_brainstorming PATH
# Return 0 if PATH needs a brainstorm-approved design. Superset of TDD scope
# plus Terraform/HCL (no TDD, but design-gated because IaC changes are risky).
devforge_file_requires_brainstorming() {
    local f="${1:-}"
    [ -z "$f" ] && return 1
    _devforge_file_excluded "$f" && return 1

    case "$f" in
        *.tf|*.hcl) return 0 ;;
    esac

    devforge_file_requires_tdd "$f"
}

# devforge_file_is_config_only PATH
# Return 0 if PATH is pure configuration — validated by lint/schema, not tests.
# Note: this does NOT perform exclusion checks, because a .yaml inside tests/
# is still structurally a config file.
devforge_file_is_config_only() {
    case "${1:-}" in
        *.yaml|*.yml|*.json|*.toml|*.ini|*.properties) return 0 ;;
        *) return 1 ;;
    esac
}
