#!/usr/bin/env bash
# Helpers per skill-advisory hook. Source-only, no shebang exec.

set -euo pipefail

STATE_FILE="${STATE_FILE_OVERRIDE:-${CLAUDE_PROJECT_DIR:-.}/.claude/projects/$(basename "$(pwd)")/.skill-state}"

# Read state field (returns empty string if missing or file inexistent)
read_state() {
    local key="$1"
    [ -f "$STATE_FILE" ] || { echo ""; return 0; }
    python3 -c "
import json, sys
try:
    data = json.load(open('$STATE_FILE'))
    print(data.get('$key', ''))
except Exception:
    print('')
" 2>/dev/null || echo ""
}

# Suggestion table: skill_name -> required_state_key (empty = no prereq)
suggestion_for() {
    case "$1" in
        siae-verification)
            local last_fix=$(read_state last_fix_or_implementation_done)
            [ -z "$last_fix" ] && echo "Suggerimento: la verifica si applica DOPO un fix o implementazione completata. Se stai iniziando nuovo lavoro, valuta siae-brainstorming."
            ;;
        siae-architecture)
            local last_brainstorm=$(read_state last_brainstorm_step)
            [ -z "$last_brainstorm" ] || [ "$last_brainstorm" -lt 4 ] 2>/dev/null && echo "Suggerimento: architecture skill è specialistica per Step 4 brainstorming (proposta opzioni). Considera siae-brainstorming prima."
            ;;
        siae-finishing-branch)
            local last_verify=$(read_state last_verification_passed)
            [ -z "$last_verify" ] && echo "Suggerimento: pre-PR checklist si applica DOPO siae-verification passata. Considera invocarla prima."
            ;;
        siae-tdd)
            local last_brainstorm=$(read_state last_brainstorm_completed)
            [ -z "$last_brainstorm" ] && echo "Suggerimento: TDD assume design approvato. Se non hai brainstormato il task, valuta siae-brainstorming prima."
            ;;
        *) ;;  # nessun suggerimento per altre skill
    esac
}
