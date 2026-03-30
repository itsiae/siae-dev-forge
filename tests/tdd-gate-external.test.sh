#!/usr/bin/env bash
# Test: tdd-gate permette file esterni al repo
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$(cd "$SCRIPT_DIR/../hooks" && pwd)/tdd-gate"

# Svuota session skills per simulare siae-tdd NON invocata
echo "" > "${HOME}/.claude/.devforge-session-skills"

# Input: file Python FUORI dal repo (path fittizio)
INPUT='{"file_path":"/tmp/genera_traccia.py"}'
RESULT=$(echo "$INPUT" | bash "$HOOK")

# Il gate deve restituire '{}' (ALLOW), NON un blocco
if echo "$RESULT" | grep -q '"decision"'; then
    echo "FAIL: file esterno al repo e' stato bloccato"
    echo "Output: $RESULT"
    exit 1
fi

echo "PASS: file esterno al repo non bloccato"
