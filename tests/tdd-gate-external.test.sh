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

# --- Test 5: file .tf (IaC) → ALLOW (no TDD for IaC) ---
reset_session
INPUT="{\"file_path\":\"${REPO_ROOT}/modules/vpc/security-groups.tf\"}"
RESULT=$(echo "$INPUT" | bash "$HOOK")
if echo "$RESULT" | grep -q '"decision"'; then
    echo "FAIL: test5 — file .tf bloccato dal TDD gate"
    FAIL=$((FAIL+1))
else
    echo "PASS: test5 — file .tf non bloccato (IaC exempt)"
    PASS=$((PASS+1))
fi

# --- Test 6: file .hcl (IaC) → ALLOW (no TDD for IaC) ---
reset_session
INPUT="{\"file_path\":\"${REPO_ROOT}/infra/terragrunt.hcl\"}"
RESULT=$(echo "$INPUT" | bash "$HOOK")
if echo "$RESULT" | grep -q '"decision"'; then
    echo "FAIL: test6 — file .hcl bloccato dal TDD gate"
    FAIL=$((FAIL+1))
else
    echo "PASS: test6 — file .hcl non bloccato (IaC exempt)"
    PASS=$((PASS+1))
fi

# --- Test 7: path relativo → normalizzato e bloccato come prod code ---
reset_session
INPUT='{"file_path":"src/service.java"}'
RESULT=$(echo "$INPUT" | bash "$HOOK")
if echo "$RESULT" | grep -q '"decision"'; then
    echo "PASS: test7 — path relativo normalizzato e bloccato"
    PASS=$((PASS+1))
else
    echo "FAIL: test7 — path relativo non gestito"
    FAIL=$((FAIL+1))
fi

# --- Test 8: path relativo con ./ prefix → normalizzato ---
reset_session
INPUT='{"file_path":"./src/handler.ts"}'
RESULT=$(echo "$INPUT" | bash "$HOOK")
if echo "$RESULT" | grep -q '"decision"'; then
    echo "PASS: test8 — path ./relativo normalizzato e bloccato"
    PASS=$((PASS+1))
else
    echo "FAIL: test8 — path ./relativo non gestito"
    FAIL=$((FAIL+1))
fi

# --- Test 9: path assoluto resta invariato ---
reset_session
INPUT="{\"file_path\":\"${REPO_ROOT}/lib/something.py\"}"
RESULT=$(echo "$INPUT" | bash "$HOOK")
if echo "$RESULT" | grep -q '"decision"'; then
    echo "PASS: test9 — path assoluto bloccato correttamente"
    PASS=$((PASS+1))
else
    echo "FAIL: test9 — path assoluto non bloccato"
    FAIL=$((FAIL+1))
fi

# --- Riepilogo ---
echo ""
echo "Risultato: ${PASS} PASS, ${FAIL} FAIL"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
