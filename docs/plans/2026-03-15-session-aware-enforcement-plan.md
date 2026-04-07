# Session-Aware Enforcement — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Trasformare il session-skills tracking da puro telemetry a fonte di enforcement, aggiungendo reminder automatici quando skill prerequisito non sono state invocate.
**Architettura:** 6 fix incrementali sugli hook esistenti + 2 nuovi hook + 1 fix in skills-core.js
**Stack:** Bash (hooks), Node.js (skills-core.js)
**SP:** 3 SP-Umano / 2 SP-Augmented
**Design doc:** `docs/plans/2026-03-15-session-aware-enforcement-design.md`

---

### Task 1: Fix trigger truncation in skills-core.js [PENDING]

**File coinvolti:**
- Modifica: `lib/skills-core.js` (riga 289)
- Test: `tests/run-all.sh` (test strutturale esistente)

**Step 1: Verifica output attuale del catalogo**

```bash
cd siae-dev-forge && node -e "
const { buildCatalog } = require('./lib/skills-core.js');
const cat = buildCatalog('.');
cat.skills.filter(s => s.trigger.length > 100).forEach(s => {
    console.log(s.name + ': ' + s.trigger.substring(0, 80) + '...');
});
"
```
Output atteso: skill con trigger > 100 char (incluso testo non-trigger dopo il periodo)

**Step 2: Applica il fix — tronca trigger al primo periodo dopo `Trigger:`**

Modifica `lib/skills-core.js` riga 289:

```javascript
// PRIMA:
trigger = triggerMatch[1].replace(/\.\s*$/, '');

// DOPO:
trigger = triggerMatch[1].split('.')[0].trim();
```

**Step 3: Verifica output post-fix**

```bash
cd siae-dev-forge && node -e "
const { buildCatalog } = require('./lib/skills-core.js');
const cat = buildCatalog('.');
const cs = cat.skills.find(s => s.name === 'siae-code-standards');
console.log('code-standards trigger:', cs.trigger);
console.log('length:', cs.trigger.length);
// Deve essere: 'scrittura codice Java, TypeScript, Python, HCL/Terraform'
// NON deve contenere: 'Naming conventions, struttura progetto...'
"
```
Output atteso: trigger pulito, solo keyword, < 80 char

**Step 4: Esegui test strutturali**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: tutti i test PASS

**Step 5: Commit**

```bash
git add lib/skills-core.js
git commit -m "fix(skills-core): tronca trigger al primo periodo dopo Trigger: keyword"
```

---

### Task 2: pre-commit verifica siae-git-workflow + re-injection catalogo [PENDING]

**File coinvolti:**
- Modifica: `hooks/pre-commit` (aggiunta ~50 righe)
- Modifica: `hooks/session-start` (aggiunta 1 riga reset counter)

**Step 1: Aggiungi counter e skill check nel pre-commit**

Modifica `hooks/pre-commit`. Inserire DOPO riga 21 (PLUGIN_ROOT) e PRIMA della funzione `escape_for_json` (riga 28), il blocco di session-awareness:

```bash
# --- Session-aware enforcement + catalog re-injection ---
SESSION_SKILLS_FILE="${HOME}/.claude/.devforge-session-skills"
SESSION_SKILLS=$(cat "$SESSION_SKILLS_FILE" 2>/dev/null || echo "")

# Tool counter for periodic catalog re-injection
TOOL_COUNTER_FILE="${HOME}/.claude/.devforge-tool-counter"
COUNTER=$(cat "$TOOL_COUNTER_FILE" 2>/dev/null || echo "0")
COUNTER=$((COUNTER + 1))
echo "$COUNTER" > "$TOOL_COUNTER_FILE"

# Generate catalog re-injection every N Bash calls
CATALOG_REINJECT=""
REINJECT_INTERVAL=20
if [ $((COUNTER % REINJECT_INTERVAL)) -eq 0 ]; then
    if command -v node >/dev/null 2>&1; then
        RAW_CATALOG=$(node "${PLUGIN_ROOT}/lib/skills-core.js" "${PLUGIN_ROOT}" 2>/dev/null || echo "")
        if [ -n "$RAW_CATALOG" ]; then
            CATALOG_REINJECT="$RAW_CATALOG"
        fi
    fi
fi
# --- End session-aware block ---
```

**Step 2: Modifica il blocco `git commit` per aggiungere skill check**

Nel blocco `if [[ "$TOOL_COMMAND" =~ git[[:space:]]+commit ]]` (riga 39), dopo la riga `: # proceed to quality gate below`, aggiungere:

```bash
    # Check if siae-git-workflow was invoked this session
    SKILL_REMINDER=""
    if ! echo "$SESSION_SKILLS" | grep -qF "siae-git-workflow"; then
        SKILL_REMINDER="\\n\\n<EXTREMELY_IMPORTANT>\\nDevForge Skill Gate: NON hai invocato siae-git-workflow in questa sessione.\\nDEVI invocarla PRIMA di procedere con il commit.\\nLa skill stabilisce naming convention, conventional commits, e pre-flight checks.\\nInvoca ora: Skill tool → siae-devforge:siae-git-workflow\\n</EXTREMELY_IMPORTANT>\\n"
    fi
```

Poi, nel blocco di output JSON in fondo (riga 247-255), preporre `SKILL_REMINDER` e appendere `CATALOG_REINJECT` al contesto:

```bash
# Compose catalog section if due for re-injection
catalog_reinject_section=""
if [ -n "$CATALOG_REINJECT" ]; then
    catalog_reinject_escaped=$(escape_for_json "$CATALOG_REINJECT")
    catalog_reinject_section="\\n\\n**DevForge Skill Catalog (re-injection periodica):**\\n\\n${catalog_reinject_escaped}"
fi

skill_reminder_escaped=""
if [ -n "$SKILL_REMINDER" ]; then
    skill_reminder_escaped="${SKILL_REMINDER}"
fi

precommit_context="${skill_reminder_escaped}<EXTREMELY_IMPORTANT>\\nDevForge Pre-Commit Quality Gate attivo.\\n\\n**PRIMA di eseguire qualsiasi commit, DEVI completare TUTTE le verifiche seguenti sui file staged. Usa le pre-flight card del DevForge Visual Design System per segnalare problemi.**\\n\\n${precommit_escaped}${catalog_reinject_section}\\n</EXTREMELY_IMPORTANT>"
```

**Step 3: Modifica il blocco else (comandi non-git) per re-injection periodica**

Sostituire il blocco else alle righe 79-82:

```bash
else
    # Non-git commands: inject catalog re-injection if counter hit
    if [ -n "$CATALOG_REINJECT" ]; then
        catalog_reinject_escaped=$(escape_for_json "$CATALOG_REINJECT")
        reinject_context="<IMPORTANT>\\nDevForge Skill Catalog (reminder periodico — invoca le skill rilevanti):\\n\\n${catalog_reinject_escaped}\\n</IMPORTANT>"

        cat <<EOF
{
  "additional_context": "${reinject_context}",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "${reinject_context}"
  }
}
EOF
        exit 0
    fi
    echo '{}'
    exit 0
fi
```

**Step 4: Aggiungi reset counter in session-start**

Modifica `hooks/session-start` riga 165-167 (blocco reset contatori), aggiungere:

```bash
echo "0" > "${HOME}/.claude/.devforge-tool-counter"
```

**Step 5: Test manuale**

```bash
# Simula 20 Bash call per verificare re-injection
cd siae-dev-forge
for i in $(seq 1 21); do echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | bash hooks/pre-commit; done
# La 20a invocazione deve restituire JSON con additional_context contenente il catalogo
# Le altre devono restituire {}
```
Output atteso: 19x `{}`, 1x JSON con catalogo, 1x `{}`

**Step 6: Esegui test strutturali**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: tutti i test PASS

**Step 7: Commit**

```bash
git add hooks/pre-commit hooks/session-start
git commit -m "feat(hooks): pre-commit verifica siae-git-workflow + re-injection catalogo ogni 20 call"
```

---

### Task 3: Nuovo hook tdd-gate (PreToolUse su Edit/Write) [PENDING]

**File coinvolti:**
- Crea: `hooks/tdd-gate`
- Modifica: `hooks/hooks.json` (aggiunta entry PreToolUse per Edit e Write)

**Step 1: Crea il file `hooks/tdd-gate`**

```bash
#!/usr/bin/env bash
# PreToolUse hook: reminder siae-tdd quando si modifica codice di produzione
# ─────────────────────────────────────────────────────────────────
# Hook:     tdd-gate
# Evento:   PreToolUse
# Matcher:  Edit, Write
# Timeout:  5s — Solo check file flat + estensione
# Formato:  additional_context (standard DevForge)
# ─────────────────────────────────────────────────────────────────

set -euo pipefail

HOOK_INPUT=$(cat)

# Extract file_path from tool input
FILE_PATH=$(echo "$HOOK_INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"//;s/"$//' || true)

if [ -z "$FILE_PATH" ]; then
    echo '{}'
    exit 0
fi

# Check if file is production code (by extension)
PROD_EXTENSIONS="\.java$|\.ts$|\.tsx$|\.js$|\.jsx$|\.py$|\.vue$|\.tf$|\.hcl$|\.go$|\.kt$"
if ! echo "$FILE_PATH" | grep -qE "$PROD_EXTENSIONS"; then
    echo '{}'
    exit 0
fi

# Exclude test files and non-production paths
EXCLUDED_PATHS="test/|tests/|__tests__|spec/|Test\.java$|IT\.java$|\.spec\.|\.test\.|test_.*\.py$|docs/|plans/|SKILL\.md|CLAUDE\.md|\.md$|evals/"
if echo "$FILE_PATH" | grep -qE "$EXCLUDED_PATHS"; then
    echo '{}'
    exit 0
fi

# Check if siae-tdd was invoked this session
SESSION_SKILLS_FILE="${HOME}/.claude/.devforge-session-skills"
SESSION_SKILLS=$(cat "$SESSION_SKILLS_FILE" 2>/dev/null || echo "")

if echo "$SESSION_SKILLS" | grep -qF "siae-tdd"; then
    echo '{}'
    exit 0
fi

# siae-tdd NOT invoked — inject reminder
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${PLUGIN_ROOT}/lib/logger.sh"
devforge_log "tdd_gate" "warning" "{\"file_path\":\"${FILE_PATH}\",\"skill_missing\":\"siae-tdd\"}"

# Escape for JSON
escape_for_json() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

BASENAME=$(basename "$FILE_PATH")
TDD_MSG="STOP — Stai modificando codice di produzione (${BASENAME}) ma NON hai invocato siae-tdd in questa sessione. La Legge di Ferro: TEST PRIMA DEL CODICE, SEMPRE. Invoca siae-tdd PRIMA di scrivere codice di produzione: Skill tool -> siae-devforge:siae-tdd"
tdd_escaped=$(escape_for_json "$TDD_MSG")
tdd_context="<EXTREMELY_IMPORTANT>\nDevForge TDD Gate: ${tdd_escaped}\n</EXTREMELY_IMPORTANT>"

cat <<EOF
{
  "additional_context": "${tdd_context}",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "${tdd_context}"
  }
}
EOF
exit 0
```

Rendere eseguibile: `chmod +x hooks/tdd-gate`

**Step 2: Aggiungi entry in hooks.json**

Aggiungere nel blocco `PreToolUse` di `hooks.json`, DOPO le entry Bash esistenti:

```json
{
  "matcher": "Edit",
  "hooks": [
    {
      "type": "command",
      "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' tdd-gate",
      "timeout": 5
    }
  ]
},
{
  "matcher": "Write",
  "hooks": [
    {
      "type": "command",
      "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' tdd-gate",
      "timeout": 5
    }
  ]
}
```

**Step 3: Test manuale**

```bash
cd siae-dev-forge
# Simula Edit su file Java senza siae-tdd in session
echo "" > ~/.claude/.devforge-session-skills
echo '{"tool_name":"Edit","tool_input":{"file_path":"/tmp/UserService.java","old_string":"x","new_string":"y"}}' | bash hooks/tdd-gate
# Output atteso: JSON con EXTREMELY_IMPORTANT + TDD Gate reminder

# Simula Edit su file .md (non produzione)
echo '{"tool_name":"Edit","tool_input":{"file_path":"/tmp/README.md","old_string":"x","new_string":"y"}}' | bash hooks/tdd-gate
# Output atteso: {}

# Simula Edit su file test
echo '{"tool_name":"Edit","tool_input":{"file_path":"/tmp/tests/test_service.py","old_string":"x","new_string":"y"}}' | bash hooks/tdd-gate
# Output atteso: {}

# Simula con siae-tdd gia' invocata
echo "siae-tdd" > ~/.claude/.devforge-session-skills
echo '{"tool_name":"Edit","tool_input":{"file_path":"/tmp/UserService.java","old_string":"x","new_string":"y"}}' | bash hooks/tdd-gate
# Output atteso: {}
```

**Step 4: Esegui test strutturali**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: tutti i test PASS

**Step 5: Commit**

```bash
git add hooks/tdd-gate hooks/hooks.json
git commit -m "feat(hooks): tdd-gate intercetta Edit/Write su codice produzione senza siae-tdd"
```

---

### Task 4: Nuovo hook plan-gate (PreToolUse su EnterPlanMode) [PENDING]

**File coinvolti:**
- Crea: `hooks/plan-gate`
- Modifica: `hooks/hooks.json` (aggiunta entry PreToolUse per EnterPlanMode)

**Step 1: Crea il file `hooks/plan-gate`**

```bash
#!/usr/bin/env bash
# PreToolUse hook: reminder siae-brainstorming prima di EnterPlanMode
# ─────────────────────────────────────────────────────────────────
# Hook:     plan-gate
# Evento:   PreToolUse
# Matcher:  EnterPlanMode
# Timeout:  5s — Solo check file flat
# Formato:  additional_context (standard DevForge)
# ─────────────────────────────────────────────────────────────────

set -euo pipefail

# Check if siae-brainstorming was invoked this session
SESSION_SKILLS_FILE="${HOME}/.claude/.devforge-session-skills"
SESSION_SKILLS=$(cat "$SESSION_SKILLS_FILE" 2>/dev/null || echo "")

if echo "$SESSION_SKILLS" | grep -qF "siae-brainstorming"; then
    echo '{}'
    exit 0
fi

# siae-brainstorming NOT invoked — inject reminder
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${PLUGIN_ROOT}/lib/logger.sh"
devforge_log "plan_gate" "warning" "{\"skill_missing\":\"siae-brainstorming\"}"

escape_for_json() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

PLAN_MSG="STOP — Stai per entrare in PlanMode ma NON hai invocato siae-brainstorming in questa sessione. NESSUNA IMPLEMENTAZIONE SENZA DESIGN APPROVATO. Invoca siae-brainstorming PRIMA di procedere: Skill tool -> siae-devforge:siae-brainstorming"
plan_escaped=$(escape_for_json "$PLAN_MSG")
plan_context="<EXTREMELY_IMPORTANT>\nDevForge Plan Gate: ${plan_escaped}\n</EXTREMELY_IMPORTANT>"

cat <<EOF
{
  "additional_context": "${plan_context}",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "${plan_context}"
  }
}
EOF
exit 0
```

Rendere eseguibile: `chmod +x hooks/plan-gate`

**Step 2: Aggiungi entry in hooks.json**

Aggiungere nel blocco `PreToolUse` di `hooks.json`:

```json
{
  "matcher": "EnterPlanMode",
  "hooks": [
    {
      "type": "command",
      "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' plan-gate",
      "timeout": 5
    }
  ]
}
```

**Step 3: Test manuale**

```bash
cd siae-dev-forge
# Senza brainstorming
echo "" > ~/.claude/.devforge-session-skills
echo '{"tool_name":"EnterPlanMode","tool_input":{}}' | bash hooks/plan-gate
# Output atteso: JSON con EXTREMELY_IMPORTANT + Plan Gate reminder

# Con brainstorming gia' invocata
echo "siae-brainstorming" > ~/.claude/.devforge-session-skills
echo '{"tool_name":"EnterPlanMode","tool_input":{}}' | bash hooks/plan-gate
# Output atteso: {}
```

**Step 4: Esegui test strutturali**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: tutti i test PASS

**Step 5: Commit**

```bash
git add hooks/plan-gate hooks/hooks.json
git commit -m "feat(hooks): plan-gate intercetta EnterPlanMode senza siae-brainstorming"
```

---

### Task 5: Fallback jq nel stop-gate [PENDING]

**File coinvolti:**
- Modifica: `hooks/stop-gate` (righe 86-94)

**Step 1: Sostituisci il blocco jq con cascata di fallback**

Sostituire le righe 86-94 di `hooks/stop-gate` con:

```bash
# Extract last assistant message text — cascading fallback: jq → node → python3
LAST_ASSISTANT_MSG=""
if command -v jq >/dev/null 2>&1; then
    LAST_ASSISTANT_MSG=$(echo "$INPUT" | jq -r '
        (.messages // .transcript // [])
        | map(select(.role == "assistant"))
        | last
        | if . == null then ""
          elif (.content | type) == "string" then .content
          else (.content | map(select(.type == "text") | .text) | join(" "))
          end
    ' 2>/dev/null || true)
elif command -v node >/dev/null 2>&1; then
    LAST_ASSISTANT_MSG=$(echo "$INPUT" | node -e "
        let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{
        try{const j=JSON.parse(d);const ms=(j.messages||j.transcript||[]).filter(m=>m.role==='assistant');
        const l=ms[ms.length-1];if(!l){process.stdout.write('');return;}
        const c=l.content;if(typeof c==='string')process.stdout.write(c);
        else process.stdout.write((c||[]).filter(b=>b.type==='text').map(b=>b.text).join(' '));
        }catch(e){process.stdout.write('');}});
    " 2>/dev/null || true)
elif command -v python3 >/dev/null 2>&1; then
    LAST_ASSISTANT_MSG=$(echo "$INPUT" | python3 -c "
import sys,json
try:
    j=json.load(sys.stdin)
    ms=[m for m in (j.get('messages') or j.get('transcript') or []) if m.get('role')=='assistant']
    if not ms:print('',end='')
    else:
        c=ms[-1].get('content','')
        if isinstance(c,str):print(c,end='')
        else:print(' '.join(b.get('text','') for b in c if b.get('type')=='text'),end='')
except:print('',end='')
    " 2>/dev/null || true)
else
    # No JSON parser available — log warning and skip gate
    devforge_log "stop_gate" "warning" "{\"reason\":\"no_json_parser\",\"tried\":\"jq,node,python3\"}"
fi
```

**Step 2: Test con jq disabilitato**

```bash
cd siae-dev-forge
# Simula input con messaggio di completamento
TEST_INPUT='{"messages":[{"role":"assistant","content":"Ho completato il fix."}]}'

# Test con jq
echo "$TEST_INPUT" | jq -r '(.messages // []) | map(select(.role == "assistant")) | last | .content'
# Output atteso: "Ho completato il fix."

# Test con node (simulando assenza jq)
echo "$TEST_INPUT" | node -e "
let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{
try{const j=JSON.parse(d);const ms=(j.messages||j.transcript||[]).filter(m=>m.role==='assistant');
const l=ms[ms.length-1];if(!l){process.stdout.write('');return;}
const c=l.content;if(typeof c==='string')process.stdout.write(c);
else process.stdout.write((c||[]).filter(b=>b.type==='text').map(b=>b.text).join(' '));
}catch(e){process.stdout.write('');}});
"
# Output atteso: "Ho completato il fix."

# Test con python3
echo "$TEST_INPUT" | python3 -c "
import sys,json
try:
    j=json.load(sys.stdin)
    ms=[m for m in (j.get('messages') or j.get('transcript') or []) if m.get('role')=='assistant']
    if not ms:print('',end='')
    else:
        c=ms[-1].get('content','')
        if isinstance(c,str):print(c,end='')
        else:print(' '.join(b.get('text','') for b in c if b.get('type')=='text'),end='')
except:print('',end='')
"
# Output atteso: "Ho completato il fix."
```

**Step 3: Esegui test strutturali**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: tutti i test PASS

**Step 4: Commit**

```bash
git add hooks/stop-gate
git commit -m "fix(hooks): stop-gate fallback jq -> node -> python3 per robustezza"
```

---

### Task 6: Aggiorna plugin.json e test finali [PENDING]

**File coinvolti:**
- Verifica: `.claude-plugin/plugin.json` (se serve aggiornamento hook count)
- Esegui: `tests/run-all.sh` (test completo finale)

**Step 1: Verifica hooks.json finale**

```bash
cd siae-dev-forge && cat hooks/hooks.json | python3 -m json.tool
```
Output atteso: JSON valido con le nuove entry PreToolUse per Edit, Write, EnterPlanMode

**Step 2: Verifica tutti i nuovi hook sono eseguibili**

```bash
cd siae-dev-forge && ls -la hooks/tdd-gate hooks/plan-gate
```
Output atteso: permessi -rwxr-xr-x per entrambi

**Step 3: Test strutturale completo**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: tutti i test PASS

**Step 4: Verifica catalogo post-fix 1**

```bash
cd siae-dev-forge && node -e "
const { buildCatalog } = require('./lib/skills-core.js');
const cat = buildCatalog('.');
console.log('Skill count:', cat.count);
cat.skills.forEach(s => {
    if (s.trigger.length > 100) console.log('WARN: ' + s.name + ' trigger > 100 char');
});
console.log('All triggers OK');
"
```
Output atteso: nessun WARN, "All triggers OK"

**Step 5: Commit finale (se necessario)**

Solo se ci sono file da aggiornare (plugin.json, README, etc.).
