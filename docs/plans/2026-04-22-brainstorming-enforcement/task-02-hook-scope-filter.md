# Task 02 — Hook scope filter + escape hatch

**Stato:** [PENDING]
**Stima:** 10 min
**Dipendenze:** Task 01

## Goal

Creare `hooks/brainstorming-gate` con scope filter (stesso di `tdd-gate`: prod ext + itsiae repo + no test) e escape hatch `DEVFORGE_ENFORCEMENT_OFF=1`. Copre scenari 6, 7, 8, 9 (out of scope + escape).

## File coinvolti

- `tests/hooks/brainstorming-gate.test.sh` (MODIFY — aggiungi 4 scenari prima di `echo "SETUP OK"`)
- `hooks/brainstorming-gate` (NEW, eseguibile)

## Step 1 — Test RED: 4 scenari out-of-scope

Aggiungi **prima** di `echo "SETUP OK"`:

```bash
# ─── Scenario 6: file docs (.md) → out of scope, pass silent ───
invoke_gate "${TEST_REPO}/README.md"
if [ "$(count_events brainstorming_nudge_soft)" != "0" ] || [ "$(count_events brainstorming_gate_blocked)" != "0" ]; then
    echo "FAIL scenario 6: hook ha elaborato file .md (out of scope)"
    cat "$DEVFORGE_LOG_FILE"
    exit 1
fi
echo "PASS scenario 6: file .md → pass (out of scope)"

# ─── Scenario 7: file IaC (.tf) → out of scope, pass silent ───
echo "resource {}" > "${TEST_REPO}/main.tf"
invoke_gate "${TEST_REPO}/main.tf"
if [ "$(count_events brainstorming_nudge_soft)" != "0" ]; then
    echo "FAIL scenario 7: hook ha elaborato file .tf (out of scope)"
    exit 1
fi
echo "PASS scenario 7: file .tf → pass (out of scope)"

# ─── Scenario 8: repo non-itsiae → out of scope, pass silent ───
NON_ITSIAE_REPO=$(mktemp -d)
(cd "$NON_ITSIAE_REPO" && git init -q && git config user.email t@t && git config user.name t && \
  git remote add origin "https://github.com/other-org/repo.git" && \
  echo "ts" > f.ts && git add f.ts && git commit -q -m init)
invoke_gate "${NON_ITSIAE_REPO}/f.ts"
if [ "$(count_events brainstorming_nudge_soft)" != "0" ]; then
    echo "FAIL scenario 8: hook ha elaborato repo non-itsiae"
    rm -rf "$NON_ITSIAE_REPO"
    exit 1
fi
rm -rf "$NON_ITSIAE_REPO"
echo "PASS scenario 8: repo non-itsiae → pass (out of scope)"

# ─── Scenario 9: DEVFORGE_ENFORCEMENT_OFF=1 → escape hatch ───
DEVFORGE_ENFORCEMENT_OFF=1 invoke_gate "${TEST_REPO}/hello.ts"
if [ "$(count_events brainstorming_nudge_soft)" != "0" ]; then
    echo "FAIL scenario 9: ENFORCEMENT_OFF non ha escapato"
    exit 1
fi
echo "PASS scenario 9: DEVFORGE_ENFORCEMENT_OFF=1 → escape immediato"
```

## Step 2 — Run test, verifica RED

```bash
bash tests/hooks/brainstorming-gate.test.sh 2>&1 | grep -E "PASS|FAIL" | tail
```

**Output atteso RED (senza hook):** 0 linee `PASS scenario` stampate perché `invoke_gate` non trova l'hook e termina con errore silenzioso (redirect `2>/dev/null` in `invoke_hook`). Il test si ferma sul primo FAIL atteso oppure può non stampare nulla se tutti gli scenari di questo task dipendono dal hook mancante. L'importante: **nessun "PASS scenario 6-9"** finché Step 3 non crea il hook.

Se vedi `PASS scenario 6-9` senza aver creato il hook, c'è un problema — l'invoke ritorna vuoto e il grep trova 0 match correttamente, ma è per il motivo SBAGLIATO (hook non esistente, non out-of-scope). Fix: lo scenario 6/7/8 deve almeno verificare che l'hook RESTITUISCA QUALCOSA (exit 0 non errore). Aggiungi verifica opzionale tipo `[ -x hooks/brainstorming-gate ] || echo "HOOK MANCA"`.

In pratica, dopo Step 3 i 4 scenari devono tutti passare con hook effettivamente funzionante (non per casualità).

## Step 3 — Implementazione hook

Crea `hooks/brainstorming-gate` con contenuto esatto:

```bash
#!/usr/bin/env bash
# PreToolUse hook: progressive enforcement siae-brainstorming su Edit/Write
# ─────────────────────────────────────────────────────────────────
# Hook:     brainstorming-gate
# Evento:   PreToolUse
# Matcher:  Edit, Write
# Timeout:  5s
# Formato:  decision:"block" se counter >= 2 (W2+ mode) e no brainstorming
# History:  v1.45.0 NEW
# ─────────────────────────────────────────────────────────────────

set -euo pipefail
export DEVFORGE_CURRENT_HOOK="brainstorming-gate"

HOOK_INPUT=$(cat)

# Escape hatch: DEVFORGE_ENFORCEMENT_OFF=1 → skip immediato
if [ "${DEVFORGE_ENFORCEMENT_OFF:-0}" = "1" ]; then
    echo '{}'
    exit 0
fi

# Extract file_path (pattern tdd-gate)
if command -v jq >/dev/null 2>&1; then
    FILE_PATH=$(echo "$HOOK_INPUT" | jq -r '.file_path // .tool_input.file_path // empty' 2>/dev/null || true)
else
    FILE_PATH=$(echo "$HOOK_INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"//;s/"$//' || true)
fi

if [ -z "$FILE_PATH" ]; then
    echo '{}'
    exit 0
fi

# Normalize relative → absolute
if [[ "$FILE_PATH" != /* ]]; then
    FILE_PATH="$(pwd)/${FILE_PATH#./}"
fi

# Scope: file dev essere dentro un repo git (walk up to find root)
FILE_DIR="$(dirname "$FILE_PATH")"
while [ -n "$FILE_DIR" ] && [ ! -d "$FILE_DIR" ]; do
    FILE_DIR="$(dirname "$FILE_DIR")"
done
if [ -z "$FILE_DIR" ]; then
    echo '{}'
    exit 0
fi
FILE_GIT_ROOT="$(git -C "$FILE_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$FILE_GIT_ROOT" ]; then
    echo '{}'
    exit 0
fi

# Scope: solo repo itsiae
REMOTE_URL="$(git -C "$FILE_GIT_ROOT" remote get-url origin 2>/dev/null || true)"
if ! echo "$REMOTE_URL" | grep -qE "[/:]itsiae/"; then
    echo '{}'
    exit 0
fi

# Scope: solo file prod (stessa regex di tdd-gate)
PROD_EXTENSIONS="\.java$|\.ts$|\.tsx$|\.js$|\.jsx$|\.py$|\.vue$|\.go$|\.kt$"
if ! echo "$FILE_PATH" | grep -qE "$PROD_EXTENSIONS"; then
    echo '{}'
    exit 0
fi

# Esclude test files e docs
EXCLUDED_PATHS="test/|tests/|__tests__|spec/|Test\.(java|kt)$|IT\.(java|kt)$|\.spec\.|\.test\.|test_.*\.py$|_test\.go$|docs/|plans/|SKILL\.md|CLAUDE\.md|\.md$|evals/"
if echo "$FILE_PATH" | grep -qE "$EXCLUDED_PATHS"; then
    echo '{}'
    exit 0
fi

# Scope filter passato — da qui in avanti Task 03 aggiunge la logica
echo '{}'
exit 0
```

## Step 4 — Rendi eseguibile + verifica

```bash
chmod +x hooks/brainstorming-gate
bash tests/hooks/brainstorming-gate.test.sh 2>&1 | grep -E "PASS|FAIL"
```

**Output atteso:**

```
PASS scenario 6: file .md → pass (out of scope)
PASS scenario 7: file .tf → pass (out of scope)
PASS scenario 8: repo non-itsiae → pass (out of scope)
PASS scenario 9: DEVFORGE_ENFORCEMENT_OFF=1 → escape immediato
```

## Step 5 — Commit

```bash
git add hooks/brainstorming-gate tests/hooks/brainstorming-gate.test.sh
git commit -m "feat(hook): brainstorming-gate scaffold con scope filter [T02]"
```

## Definition of Done

- [ ] Scenari 6, 7, 8, 9 passano
- [ ] Hook eseguibile (`chmod +x`)
- [ ] Escape hatch `DEVFORGE_ENFORCEMENT_OFF=1` funzionante
- [ ] Scope filter identico a tdd-gate per coerenza
- [ ] Commit creato
