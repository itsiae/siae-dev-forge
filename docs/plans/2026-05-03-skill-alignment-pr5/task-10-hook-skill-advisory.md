# Task 10 — Hook `skill-advisory` (PostToolUse Advisory, Non-Blocking)

**Goal:** Bash hook che osserva invocazioni skill e suggerisce skill prerequisita se mancante. **Mai blocca** (exit 0 sempre). Output suggestion via additionalContext (max 2KB).

**Pattern repo**: file hook senza estensione `.sh`, invocato via `bash run-hook.cmd skill-advisory`.

**File coinvolti:**
- `hooks/skill-advisory` (nuovo, eseguibile, NO .sh extension per coerenza col pattern repo)
- `hooks/lib/skill-advisory-helpers.sh` (nuovo, funzioni helper, .sh OK perché source-only)

## Step 1 — Crea directory

```bash
mkdir -p hooks/lib
```

## Step 2 — Helpers

In `hooks/lib/skill-advisory-helpers.sh`:

```bash
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
```

## Step 3 — Hook entrypoint

In `hooks/skill-advisory`:

```bash
#!/usr/bin/env bash
# Skill Advisory Hook — PostToolUse event
# Suggerisce skill prerequisita SE mancante nello state file.
# NEVER blocca: exit 0 sempre, output via additionalContext stdout.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib/skill-advisory-helpers.sh
source "$SCRIPT_DIR/lib/skill-advisory-helpers.sh"

# Hook receives JSON via stdin (Claude Code hook protocol)
# Extract tool_name and tool_input.skill_name (if applicable)
INPUT="$(cat)"

SKILL_NAME=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    skill = data.get('tool_input', {}).get('skill', '') or data.get('tool_input', {}).get('skill_name', '')
    # Strip plugin namespace prefix
    if ':' in skill:
        skill = skill.split(':', 1)[1]
    print(skill)
except Exception:
    print('')
" 2>/dev/null || echo "")

[ -z "$SKILL_NAME" ] && exit 0  # Not a skill invocation, silent pass

SUGGESTION=$(suggestion_for "$SKILL_NAME")

if [ -n "$SUGGESTION" ]; then
    # Output additionalContext (max 2KB) — Claude Code hook protocol
    cat <<EOF
{
  "additionalContext": "[skill-advisory] $SUGGESTION"
}
EOF
fi

exit 0  # Always 0 — non-blocking
```

## Step 4 — Make eseguibili

```bash
chmod +x hooks/skill-advisory
```

## Step 5 — Test sintassi

```bash
bash -n hooks/skill-advisory
bash -n hooks/lib/skill-advisory-helpers.sh
shellcheck hooks/skill-advisory hooks/lib/skill-advisory-helpers.sh 2>/dev/null || echo "shellcheck not installed, skipped"
```

## Step 6 — Test isolato

```bash
# Caso: nessuno state file → siae-verification suggerisce brainstorm
mkdir -p /tmp/test-skill-advisory/.claude/projects/test
STATE_FILE_OVERRIDE=/tmp/test-skill-advisory/.skill-state \
  echo '{"tool_input": {"skill": "siae-verification"}}' | hooks/skill-advisory

# Output atteso: JSON con additionalContext "Suggerimento: la verifica si applica DOPO..."

# Caso: state ha last_fix → no suggestion
echo '{"last_fix_or_implementation_done": "2026-05-03T10:00"}' > /tmp/test-skill-advisory/.skill-state
STATE_FILE_OVERRIDE=/tmp/test-skill-advisory/.skill-state \
  echo '{"tool_input": {"skill": "siae-verification"}}' | hooks/skill-advisory

# Output atteso: vuoto (no suggestion)

# Caso: skill non in tabella → no suggestion
echo '{"tool_input": {"skill": "siae-frontend"}}' | hooks/skill-advisory
# Output atteso: vuoto

# Cleanup
rm -rf /tmp/test-skill-advisory
```

## Step 7 — Commit

```bash
git add hooks/skill-advisory hooks/lib/skill-advisory-helpers.sh
git commit -m "feat(hooks): skill-advisory PostToolUse hook (non-blocking)

Hook che osserva invocazioni skill e suggerisce skill prerequisita se manca
nel .skill-state. NEVER blocca (exit 0). Output via additionalContext (≤2KB).
Skill coperte: verification, architecture, finishing-branch, tdd.
Test isolato 3 scenari OK."
```

## Criteri accettazione

- `hooks/skill-advisory` eseguibile
- shellcheck/bash -n PASS
- 3 test scenari isolati PASS
- Exit 0 sempre (verificato manualmente con `set -e` post chiamata)

## NO-REGRESSION

Hook è additivo: non blocca mai, non modifica skill esistenti. Pure observer + nudge. Zero impact sull'attivazione skill esistenti.
