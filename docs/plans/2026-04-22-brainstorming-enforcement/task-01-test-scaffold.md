# Task 01 — Test scaffold + helpers mock

**Stato:** [PENDING]
**Stima:** 8 min
**Dipendenze:** nessuna

## Goal

Creare `tests/hooks/brainstorming-gate.test.sh` con scaffold + helpers mock riutilizzabili dai task 02-06. Verifica che il boilerplate gira verde senza logica di hook.

## File coinvolti

- `tests/hooks/brainstorming-gate.test.sh` (NEW)

## Step 1 — Scrivi lo scaffold

Crea il file con contenuto esatto:

```bash
#!/usr/bin/env bash
# Test: brainstorming-gate hook — progressive enforcement (nudge/warn/block)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Isolated HOME + TMPREPO
TEST_HOME=$(mktemp -d)
TEST_REPO=$(mktemp -d)
TEST_LOG=$(mktemp)

trap 'rm -rf "$TEST_HOME" "$TEST_REPO" "$TEST_LOG" 2>/dev/null || true' EXIT

export HOME="$TEST_HOME"
export DEVFORGE_LOG_FILE="$TEST_LOG"
export DEVFORGE_SESSION_DIR=$(mktemp -d)
export DEVFORGE_FORCE_BASH_FALLBACK=1
mkdir -p "${HOME}/.claude"

# Setup repo di test con remote itsiae (gate scope filter lo richiede)
cd "$TEST_REPO"
git init -q
git config user.email "test@test.local"
git config user.name "Test"
git remote add origin "https://github.com/itsiae/test-repo.git"
echo "hello" > hello.ts
git add hello.ts
git commit -q -m "initial"

# Helper: invoca hook con file_path simulato
invoke_gate() {
    local file_path="$1"
    local hook_input
    hook_input=$(python3 -c 'import json,sys; print(json.dumps({"tool_name":"Edit","file_path":sys.argv[1],"tool_input":{"file_path":sys.argv[1]}}))' "$file_path")
    echo "$hook_input" | bash "${PLUGIN_ROOT}/hooks/brainstorming-gate" 2>/dev/null
}

# Helper: forza un SID noto (per testing counter SID-anchored)
set_sid() {
    echo "$1" > "${HOME}/.claude/.devforge-session-id"
}

# Helper: conta eventi per nome nel log
count_events() {
    local event_name="$1"
    grep -c "\"event\":\"${event_name}\"" "$DEVFORGE_LOG_FILE" 2>/dev/null || true
}

# Helper: leggi counter corrente
read_counter() {
    cat "${HOME}/.claude/.devforge-brainstorm-counter" 2>/dev/null || echo ""
}

# Helper: setta session-skills file con una skill invocata
set_session_skill() {
    echo "$1" > "${HOME}/.claude/.devforge-session-skills"
}

# Default SID per tutti gli scenari
set_sid "test-sid-12345"

echo "SETUP OK"
exit 0
```

## Step 2 — Rendi eseguibile + verifica

```bash
chmod +x tests/hooks/brainstorming-gate.test.sh
bash tests/hooks/brainstorming-gate.test.sh
```

**Output atteso:**

```
SETUP OK
```

Se fallisce con `no such file hooks/brainstorming-gate`, il setup è OK — questo errore è atteso finché Task 02 non crea il file. Puoi ignorarlo per questo step (lo scaffold deve terminare prima di invocare il hook).

## Step 3 — Commit

```bash
git add tests/hooks/brainstorming-gate.test.sh
git commit -m "test(hook): scaffold test brainstorming-gate con helpers mock [T01]"
```

## Definition of Done

- [ ] File eseguibile
- [ ] Esecuzione termina con "SETUP OK" ed exit 0
- [ ] Helper `invoke_gate`, `set_sid`, `count_events`, `read_counter`, `set_session_skill` definiti
- [ ] Remote origin mock itsiae già configurato
- [ ] Commit creato
