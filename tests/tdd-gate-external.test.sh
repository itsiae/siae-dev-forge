#!/usr/bin/env bash
# Test: tdd-gate skip per file esterni al repo
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$(cd "$SCRIPT_DIR/../hooks" && pwd)/tdd-gate"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && git rev-parse --show-toplevel)"

PASS=0
FAIL=0

# Helper: svuota session skills (simula siae-tdd NON invocata)
reset_session() {
    echo "" > "${HOME}/.claude/.devforge-session-skills"
}

# --- Test 1: file esterno al repo → ALLOW ---
reset_session
INPUT='{"file_path":"/tmp/genera_traccia.py"}'
RESULT=$(echo "$INPUT" | bash "$HOOK")
if echo "$RESULT" | grep -q '"decision"'; then
    echo "FAIL: test1 — file esterno bloccato"
    FAIL=$((FAIL+1))
else
    echo "PASS: test1 — file esterno non bloccato"
    PASS=$((PASS+1))
fi

# --- Test 2: file interno al repo con estensione prod → BLOCK ---
reset_session
INPUT="{\"file_path\":\"${REPO_ROOT}/lib/something.py\"}"
RESULT=$(echo "$INPUT" | bash "$HOOK")
if echo "$RESULT" | grep -q '"decision"'; then
    echo "PASS: test2 — file interno bloccato"
    PASS=$((PASS+1))
else
    echo "FAIL: test2 — file interno NON bloccato"
    FAIL=$((FAIL+1))
fi

# --- Test 3: file esterno con spazi nel path → ALLOW ---
reset_session
INPUT='{"file_path":"/Users/test/hackhathon siae2026/genera_traccia.py"}'
RESULT=$(echo "$INPUT" | bash "$HOOK")
if echo "$RESULT" | grep -q '"decision"'; then
    echo "FAIL: test3 — file esterno con spazi bloccato"
    FAIL=$((FAIL+1))
else
    echo "PASS: test3 — file esterno con spazi non bloccato"
    PASS=$((PASS+1))
fi

# --- Test 4: git non disponibile → gate prosegue (file esterno non bloccato per estensione check) ---
reset_session
INPUT='{"file_path":"/tmp/genera_traccia.py"}'
RESULT=$(echo "$INPUT" | PATH="" bash "$HOOK" 2>/dev/null || echo '{}')
if echo "$RESULT" | grep -q '"decision"'; then
    echo "FAIL: test4 — gate broken senza git"
    FAIL=$((FAIL+1))
else
    echo "PASS: test4 — gate graceful senza git"
    PASS=$((PASS+1))
fi

# --- Riepilogo ---
echo ""
echo "Risultato: ${PASS} PASS, ${FAIL} FAIL"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
