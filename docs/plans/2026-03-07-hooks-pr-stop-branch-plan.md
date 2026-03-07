# Hooks Estesi: pr-gate, stop-gate, branch-check — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Aggiungere 3 hook automatici che non dipendono dalla disciplina del developer
**Architettura:** Hook bash via additionalContext injection — stesso meccanismo del pre-commit esistente. Ogni script legge TOOL_COMMAND da stdin JSON, decide se attivare, inietta istruzioni che Claude esegue.
**Stack:** Bash, JSON, hooks.json
**SP:** 3

---

### Task 1: `hooks/pr-gate` — Security Scan Pre-PR

**File coinvolti:**
- Crea: `hooks/pr-gate`

**Step 1: Verifica che il file NON esiste (test fallente)**

```bash
bash -c 'echo "{\"command\":\"gh pr create\"}" | bash hooks/pr-gate | python3 -c "import json,sys; d=json.load(sys.stdin); assert \"additional_context\" in d or \"hookSpecificOutput\" in d, \"pr-gate output mancante\""'
```
Output atteso: `bash: hooks/pr-gate: No such file or directory` — FAIL confermato.

**Step 2: Crea `hooks/pr-gate`**

```bash
#!/usr/bin/env bash
# pr-gate — PreToolUse hook: security scan before gh pr create/edit

set -euo pipefail

HOOK_INPUT=$(cat)
TOOL_COMMAND=$(echo "$HOOK_INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"command"[[:space:]]*:[[:space:]]*"//;s/"$//' || true)

# Only activate on gh pr create or gh pr edit
if [[ ! "$TOOL_COMMAND" =~ gh[[:space:]]+pr[[:space:]]+(create|edit) ]]; then
    echo '{}'
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${PLUGIN_ROOT}/lib/logger.sh"
devforge_log "pr_gate" "success" "{\"check\":\"pr_security_activated\",\"command\":\"${TOOL_COMMAND}\"}"

escape_for_json() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

read -r -d '' PR_GATE_INSTRUCTIONS << 'INSTRUCTIONS_EOF' || true
# DevForge PR Security Gate

Stai per eseguire `gh pr create` o `gh pr edit`. PRIMA di procedere, esegui questo security scan.

## Step 1: Identifica i file modificati nel branch

```bash
git diff $(git merge-base HEAD origin/sviluppo 2>/dev/null || git merge-base HEAD origin/main 2>/dev/null || echo "HEAD~1")...HEAD --name-only
```

## Step 2: Per ogni file modificato, controlla

**CRITICO — Blocca gh pr create:**
- AWS Key: `AKIA[0-9A-Z]{16}`
- Password hardcoded: `[pP]assword\s*[:=]\s*["'][^"']+["']`
- Private key: `-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----`
- Connection string con credenziali: `(mysql|postgres|mongodb)://[^:]+:[^@]+@`
- API Key hardcoded: `[aA][pP][iI][-_]?[kK][eE][yY]\s*[:=]\s*["'][^"']+["']`

**ALTO — Warn + richiedi conferma:**
- IAM policy con `"*"` su Action o Resource
- S3 bucket con `acl = "public-read"` o `block_public_acls = false`
- Lambda senza VPC su handler che tratta `ISRC`, `IBAN`, `codice_fiscale`

**MEDIO — Warning:**
- `console.log` o `print()` con variabili che sembrano PII
- Valori sensibili non gestiti da Secrets Manager

## Step 3: Mostra risultati

**Se CRITICO trovato:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  DevForge — CRITICO  ·  Security issue rilevato pre-PR            ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  File:    [file]  Issue: [descrizione]                             ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  Perche': Security issue critico blocca la PR                      ┃
┃  Se NO:   Vulnerabilita' critica entra nel repository              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
NON procedere con gh pr create. Risolvi prima il problema CRITICO.
```

**Se ALTO trovato:** mostra pre-flight card ALTO e chiedi conferma prima di procedere.

**Se nessun issue:** procedi con `gh pr create` normalmente.
INSTRUCTIONS_EOF

pr_gate_escaped=$(escape_for_json "$PR_GATE_INSTRUCTIONS")
pr_gate_context="<EXTREMELY_IMPORTANT>\nDevForge PR Security Gate attivo.\n\n${pr_gate_escaped}\n</EXTREMELY_IMPORTANT>"

cat <<EOF
{
  "additional_context": "${pr_gate_context}",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "${pr_gate_context}"
  }
}
EOF

exit 0
```

**Step 3: Rendi eseguibile e testa**

```bash
chmod +x hooks/pr-gate
```

```bash
echo '{"command":"gh pr create --title \"test\""}' | bash hooks/pr-gate | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'hookSpecificOutput' in d; print('PASS pr-gate: gh pr create attivato')"
```
Output atteso: `PASS pr-gate: gh pr create attivato`

```bash
echo '{"command":"git push origin main"}' | bash hooks/pr-gate
```
Output atteso: `{}` — non attivato su comandi non-PR.

**Step 4: Commit**

```bash
git add hooks/pr-gate
git commit -m "feat(hooks): aggiungi pr-gate — security scan pre-gh-pr-create"
```

---

### Task 2: `hooks/stop-gate` — Verification Reminder Pre-Stop

**File coinvolti:**
- Crea: `hooks/stop-gate`

**Step 1: Verifica che il file NON esiste (test fallente)**

```bash
bash -c 'echo "{}" | bash hooks/stop-gate | python3 -c "import json,sys; d=json.load(sys.stdin); assert \"hookSpecificOutput\" in d"'
```
Output atteso: `bash: hooks/stop-gate: No such file or directory` — FAIL confermato.

**Step 2: Crea `hooks/stop-gate`**

```bash
#!/usr/bin/env bash
# stop-gate — Stop hook: siae-verification reminder before Claude stops

set -euo pipefail

escape_for_json() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

STOP_GATE_INSTRUCTIONS="Se il tuo ultimo output contiene un claim di completamento — parole come 'fatto', 'fixato', 'completato', 'funziona', 'done', 'fixed', 'PASS', 'completato con successo', 'implementato', 'risolto' — DEVI invocare siae-verification prima di fermarti. Segui il protocollo IDENTIFICA -> ESEGUI -> LEGGI -> VERIFICA -> AFFERMA. Se il tuo output e' una risposta normale, una domanda, un'analisi o un aggiornamento di stato senza claim di completamento, ignora questo messaggio silenziosamente."

stop_gate_escaped=$(escape_for_json "$STOP_GATE_INSTRUCTIONS")
stop_gate_context="<EXTREMELY_IMPORTANT>\nDevForge Verification Gate: ${stop_gate_escaped}\n</EXTREMELY_IMPORTANT>"

cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "Stop",
    "additionalContext": "${stop_gate_context}"
  }
}
EOF

exit 0
```

**Step 3: Rendi eseguibile e testa**

```bash
chmod +x hooks/stop-gate
```

```bash
echo '{}' | bash hooks/stop-gate | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'hookSpecificOutput' in d; assert d['hookSpecificOutput']['hookEventName'] == 'Stop'; print('PASS stop-gate: Stop hook output corretto')"
```
Output atteso: `PASS stop-gate: Stop hook output corretto`

**Step 4: Commit**

```bash
git add hooks/stop-gate
git commit -m "feat(hooks): aggiungi stop-gate — siae-verification reminder pre-stop"
```

---

### Task 3: `hooks/pre-commit` — Estensione branch-check

**File coinvolti:**
- Modifica: `hooks/pre-commit`

**Step 1: Test fallente — verifica che git checkout -b NON produce output context**

```bash
echo '{"command":"git checkout -b feature/SPORT-456-test"}' | bash hooks/pre-commit | python3 -c "import json,sys; d=json.load(sys.stdin); assert d == {}, f'Expected empty dict, got: {d}'"
```
Output atteso: successo (restituisce `{}` perché al momento il pre-commit ignora checkout).

Il test diventa: dopo la modifica deve restituire JSON con `additional_context` per branch con JIRA ID.

**Step 2: Modifica `hooks/pre-commit`**

Trova la sezione:
```bash
# Only activate on git commit commands — exit silently for everything else
if [[ ! "$TOOL_COMMAND" =~ git[[:space:]]+commit ]]; then
    echo '{}'
    exit 0
fi
```

Sostituisci con:
```bash
# Route to appropriate check based on command
if [[ "$TOOL_COMMAND" =~ git[[:space:]]+commit ]]; then
    : # proceed to quality gate below
elif [[ "$TOOL_COMMAND" =~ git[[:space:]]+(checkout[[:space:]]+-b|switch[[:space:]]+-c) ]]; then
    # Branch check: warn if feature branch without design doc
    BRANCH_NAME=$(echo "$TOOL_COMMAND" | grep -oE '[a-zA-Z0-9/_.-]+$' || true)
    JIRA_ID=$(echo "$BRANCH_NAME" | grep -oE '[A-Z]+-[0-9]+' | head -1 || true)

    if [ -z "$JIRA_ID" ]; then
        # No JIRA ID — skip silently
        echo '{}'
        exit 0
    fi

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
    PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
    PLANS_DIR="${PLUGIN_ROOT}/docs/plans"

    if [ -d "$PLANS_DIR" ] && ls "$PLANS_DIR"/*"${JIRA_ID}"*design* 2>/dev/null | head -1 | grep -q .; then
        # Design doc found — proceed silently
        echo '{}'
        exit 0
    fi

    # Design doc NOT found — inject warning
    WARNING_MSG="Stai creando il branch '${BRANCH_NAME}'. Non esiste un design doc in docs/plans/ per ${JIRA_ID}. Hai eseguito siae-brainstorming prima di iniziare il codice? Procedo comunque con git checkout, ma il design e' consigliato prima dell'implementazione."

    escape_for_json() {
        local s="$1"
        s="${s//\\/\\\\}"
        s="${s//\"/\\\"}"
        s="${s//$'\n'/\\n}"
        s="${s//$'\r'/\\r}"
        s="${s//$'\t'/\\t}"
        printf '%s' "$s"
    }

    warning_escaped=$(escape_for_json "$WARNING_MSG")
    branch_context="<IMPORTANT>\nDevForge Branch Check: ${warning_escaped}\n</IMPORTANT>"

    cat <<EOF
{
  "additional_context": "${branch_context}",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "${branch_context}"
  }
}
EOF
    exit 0
else
    # All other commands — exit silently
    echo '{}'
    exit 0
fi
```

**Step 3: Testa la modifica**

```bash
# Branch con JIRA ID senza design doc → deve iniettare warning
echo '{"command":"git checkout -b feature/SPORT-999-test"}' | bash hooks/pre-commit | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'hookSpecificOutput' in d or 'additional_context' in d; print('PASS branch-check: warning iniettato per SPORT-999')"
```
Output atteso: `PASS branch-check: warning iniettato per SPORT-999`

```bash
# Branch senza JIRA ID → silenzioso
echo '{"command":"git checkout -b fix/quick-hotfix"}' | bash hooks/pre-commit
```
Output atteso: `{}`

```bash
# git commit → quality gate attivo (comportamento invariato)
echo '{"command":"git commit -m \"test\""}' | bash hooks/pre-commit | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'hookSpecificOutput' in d; print('PASS pre-commit: quality gate invariato')"
```
Output atteso: `PASS pre-commit: quality gate invariato`

**Step 4: Commit**

```bash
git add hooks/pre-commit
git commit -m "feat(hooks): estende pre-commit con branch-check per git checkout -b"
```

---

### Task 4: `hooks/hooks.json` — Aggiunta pr-gate e Stop entry

**File coinvolti:**
- Modifica: `hooks/hooks.json`

**Step 1: Verifica stato attuale**

```bash
cat hooks/hooks.json | python3 -c "import json,sys; d=json.load(sys.stdin); entries=d['hooks'].get('PreToolUse',[]); assert len(entries)==1; print('PASS: 1 PreToolUse entry (atteso)')"
```
Output atteso: `PASS: 1 PreToolUse entry (atteso)`

**Step 2: Aggiorna `hooks/hooks.json`**

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' session-start",
            "async": false
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' pre-commit",
            "timeout": 10
          },
          {
            "type": "command",
            "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' pr-gate",
            "timeout": 15
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' stop-gate",
            "timeout": 5
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' post-skill",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

**Step 3: Valida JSON**

```bash
python3 -c "import json; json.load(open('hooks/hooks.json')); print('PASS hooks.json: JSON valido')"
```
Output atteso: `PASS hooks.json: JSON valido`

```bash
python3 -c "
import json
d = json.load(open('hooks/hooks.json'))
assert 'Stop' in d['hooks'], 'Stop entry mancante'
assert len(d['hooks']['PreToolUse'][0]['hooks']) == 2, 'pr-gate entry mancante'
print('PASS hooks.json: Stop e pr-gate presenti')
"
```
Output atteso: `PASS hooks.json: Stop e pr-gate presenti`

**Step 4: Commit**

```bash
git add hooks/hooks.json
git commit -m "feat(hooks): aggiorna hooks.json con pr-gate (PreToolUse) e stop-gate (Stop)"
```

---

### Task 5: `tests/run-all.sh` — Sezione Hook Validation

**File coinvolti:**
- Modifica: `tests/run-all.sh`

**Step 1: Verifica che la sezione NON esiste**

```bash
grep -c "Hook Validation" tests/run-all.sh && echo "FAIL: sezione gia' presente" || echo "PASS: sezione non ancora presente"
```
Output atteso: `PASS: sezione non ancora presente`

**Step 2: Aggiungi sezione "Hook Validation" in `tests/run-all.sh`**

Inserisci PRIMA di `# --- Visual Design System Validation ---`:

```bash
# --- Hook Validation ---
echo ""
echo "=== Hook Validation ==="
echo ""

hook_ok=0
hook_fail=0

# 1. pr-gate esiste ed e' eseguibile
if [ -x "${PLUGIN_ROOT}/hooks/pr-gate" ]; then
  echo "  PASS  pr-gate: esiste ed e' eseguibile"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  pr-gate: mancante o non eseguibile"
  hook_fail=$((hook_fail + 1))
fi

# 2. stop-gate esiste ed e' eseguibile
if [ -x "${PLUGIN_ROOT}/hooks/stop-gate" ]; then
  echo "  PASS  stop-gate: esiste ed e' eseguibile"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  stop-gate: mancante o non eseguibile"
  hook_fail=$((hook_fail + 1))
fi

# 3. hooks.json contiene entry Stop e pr-gate
if python3 -c "
import json, sys
d = json.load(open('${PLUGIN_ROOT}/hooks/hooks.json'))
assert 'Stop' in d['hooks'], 'Stop entry mancante'
assert len(d['hooks']['PreToolUse'][0]['hooks']) >= 2, 'pr-gate entry mancante'
" 2>/dev/null; then
  echo "  PASS  hooks.json: Stop e pr-gate configurati"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks.json: Stop o pr-gate mancanti"
  hook_fail=$((hook_fail + 1))
fi

# 4. pre-commit gestisce git checkout -b senza crash
checkout_output=$(echo '{"command":"git checkout -b fix/no-jira-id"}' | bash "${PLUGIN_ROOT}/hooks/pre-commit" 2>/dev/null || echo "ERROR")
if [ "$checkout_output" = "{}" ] || echo "$checkout_output" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
  echo "  PASS  pre-commit: gestisce git checkout -b (exit pulito)"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  pre-commit: crash su git checkout -b"
  hook_fail=$((hook_fail + 1))
fi

echo ""
echo "  Hook totali: $((hook_ok + hook_fail)) | OK: ${hook_ok} | FAIL: ${hook_fail}"
TOTAL_PASS=$((TOTAL_PASS + hook_ok))
TOTAL_FAIL=$((TOTAL_FAIL + hook_fail))
```

**Step 3: Esegui test suite completa**

```bash
bash tests/run-all.sh 2>&1 | tail -15
```
Output atteso:
```
Hook totali: 4 | OK: 4 | FAIL: 0   (o 0 OK se hooks non ancora creati — test fallenti confermati)
```

Dopo implementazione Task 1-4, riesegui:
```bash
bash tests/run-all.sh 2>&1 | grep -E "PASS|FAIL|REPORT"
```
Output atteso: `PASS: 69 | FAIL: 0 | SKIP: 0`

**Step 4: Commit**

```bash
git add tests/run-all.sh
git commit -m "test(hooks): aggiunge Hook Validation section in run-all.sh"
```
