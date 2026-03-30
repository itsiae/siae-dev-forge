# Task 01: Aggiungere check file esterno al repo in tdd-gate

**File coinvolti:**
- `hooks/tdd-gate` (modifica — aggiungere check dopo riga 26)

**Stato:** [PENDING]

---

## Step 1 — Scrivi test: file esterno al repo deve essere ALLOW

Crea un test che simula l'input del tdd-gate con un file esterno al repo.

**File:** `tests/tdd-gate-external.test.sh` (nuovo)

```bash
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
```

## Step 2 — Esegui test, verifica che FALLISCE

**Run:** `bash tests/tdd-gate-external.test.sh`

**Output atteso:** `FAIL: file esterno al repo e' stato bloccato` (exit 1)

Il test fallisce perche' il gate attuale non ha il check per file esterni.

## Step 3 — Implementa il check in hooks/tdd-gate

**File:** `hooks/tdd-gate`

**Dopo** il blocco `if [ -z "$FILE_PATH" ]` (righe 23-26) e **prima** del check estensione (riga 28-29), aggiungi:

```bash
# Skip files outside the plugin's git repository (e.g. one-shot scripts in other dirs)
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
GIT_ROOT="$(git -C "$HOOK_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
if [ -n "$GIT_ROOT" ] && [[ "$FILE_PATH" != "$GIT_ROOT"/* ]]; then
    echo '{}'
    exit 0
fi
```

## Step 4 — Esegui test, verifica che PASSA

**Run:** `bash tests/tdd-gate-external.test.sh`

**Output atteso:** `PASS: file esterno al repo non bloccato` (exit 0)

## Step 5 — Verifica non-regressione: file interno al repo resta bloccato

**Run manuale:**

```bash
# Svuota session skills
echo "" > "${HOME}/.claude/.devforge-session-skills"

# File INTERNO al repo con estensione prod
REPO_ROOT="$(git -C hooks rev-parse --show-toplevel)"
INPUT="{\"file_path\":\"${REPO_ROOT}/hooks/tdd-gate\"}"
RESULT=$(echo "$INPUT" | bash hooks/tdd-gate)

# Deve contenere "decision": "block"
echo "$RESULT" | grep -q '"decision"' && echo "PASS: file interno bloccato" || echo "FAIL: file interno NON bloccato"
```

**Output atteso:** `PASS: file interno bloccato`

## Step 6 — Commit

```bash
git add hooks/tdd-gate tests/tdd-gate-external.test.sh
git commit -m "fix(hooks): skip TDD gate for files outside git repository

Files outside the plugin's git repo (e.g. one-shot scripts in other
directories) are not production code and should not be subject to the
TDD gate. Added prefix-match check on GIT_ROOT before extension check."
```
