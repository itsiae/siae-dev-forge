# Session-Aware Enforcement — Design Doc

**Data**: 2026-03-15
**Autore**: Lorenzo (AI CC Lead)
**SP**: 3 SP-Umano / 2 SP-Augmented
**Tipo**: Enhancement — hook enforcement + bug fix

## Contesto

Il plugin siae-dev-forge ha 30 skill ma solo 1 hard enforcement reale (pr-gate secret scan con `decision: block`). Le 29 skill rimanenti dipendono interamente dalla compliance volontaria del modello dopo aver letto il catalogo iniettato al SessionStart.

Il file `~/.claude/.devforge-session-skills` (scritto dal `post-skill` hook) traccia già quali skill sono state invocate nella sessione corrente, ma nessun hook lo legge per enforcement. Questo design trasforma quel file da puro telemetry a **fonte di verità per enforcement**.

## Obiettivi

1. Ogni `git commit` senza `siae-git-workflow` invocata → reminder automatico
2. Ogni `Edit`/`Write` su codice produzione senza `siae-tdd` → reminder automatico
3. Ogni `EnterPlanMode` senza `siae-brainstorming` → reminder automatico
4. Il `stop-gate` non fallisce silenziosamente se `jq` è assente
5. Il catalogo skill viene re-iniettato periodicamente (ogni ~20 Bash call + ogni git commit)
6. Il trigger nel catalogo per skill con `Trigger:` dopo la prima frase non viene troncato

## Non-obiettivi

- Trasformare i reminder in `decision: block` (troppo aggressivo, rischio di bloccare il modello su task legittimi)
- Aggiungere hook su ogni singolo tool (overhead eccessivo)
- Cambiare l'architettura del plugin

## Design

### Fix 1 — Trigger truncation in `skills-core.js`

**File**: `lib/skills-core.js` riga 288-289

**Problema**: dopo `Trigger:`, la regex `.+` cattura tutto fino a fine stringa (joinata da spazi). Per skill come `siae-code-standards` la description è `"Standard di codifica SIAE multi-stack. Trigger: scrittura codice Java, TypeScript, Python, HCL/Terraform. Naming conventions, struttura progetto..."` — il trigger cattura anche il testo descrittivo dopo il periodo.

**Fix**: dopo il match di `Trigger:`, troncare alla prima frase (periodo) per isolare solo le keyword di trigger.

```javascript
// PRIMA (riga 289):
trigger = triggerMatch[1].replace(/\.\s*$/, '');

// DOPO:
trigger = triggerMatch[1].split('.')[0].trim();
```

**Risultato atteso per code-standards**: `"scrittura codice Java, TypeScript, Python, HCL/Terraform"` (invece di 120+ char troncati con testo non-trigger).

---

### Fix 2 — `pre-commit` verifica `siae-git-workflow` in session-skills

**File**: `hooks/pre-commit` dopo riga 39 (blocco `git commit`)

**Meccanismo**: leggere `~/.claude/.devforge-session-skills` e verificare che contenga `siae-git-workflow`. Se assente, prepend al quality gate un reminder EXTREMELY_IMPORTANT.

```bash
SESSION_SKILLS_FILE="${HOME}/.claude/.devforge-session-skills"
SESSION_SKILLS=$(cat "$SESSION_SKILLS_FILE" 2>/dev/null || echo "")

SKILL_REMINDER=""
if ! echo "$SESSION_SKILLS" | grep -qF "siae-git-workflow"; then
    SKILL_REMINDER="STOP — Non hai invocato siae-git-workflow in questa sessione. DEVI invocarla PRIMA di procedere con il commit. La skill stabilisce naming convention, conventional commits, e pre-flight checks. Invocala ora con: Skill tool → siae-git-workflow"
fi
```

Il reminder viene prepeso al quality gate (non lo sostituisce).

**Enforcement**: `additional_context` (soft) — non blocca il commit, ma il modello riceve l'istruzione prima del quality gate.

---

### Fix 3 — PreToolUse su `Edit`/`Write` per `siae-tdd`

**File nuovo**: `hooks/tdd-gate`
**hooks.json**: aggiungere PreToolUse entry con matcher `Edit` e `Write`

**Logica**:
1. Estrarre il path del file target da stdin JSON (`file_path` per Edit/Write)
2. Controllare se è codice di produzione:
   - **Estensioni produzione**: `.java`, `.ts`, `.tsx`, `.js`, `.jsx`, `.py`, `.vue`, `.tf`, `.hcl`, `.go`, `.kt`
   - **Path esclusi** (regex): `test/`, `__tests__/`, `tests/`, `spec/`, `*Test.java`, `*IT.java`, `*.spec.ts`, `*.test.ts`, `*.test.py`, `test_*.py`, `docs/`, `*.md`, `*.json`, `*.yml`, `*.yaml`, `*.xml`, `*.sh`, `*.css`, `*.scss`, `*.html`, `SKILL.md`, `CLAUDE.md`, `plans/`
3. Se è codice produzione E `siae-tdd` non è in `session-skills` → iniettare reminder
4. Se non è codice produzione → `echo '{}'` silenzioso

**Performance**: deve completare in < 100ms. Solo operazioni su file flat (grep su file da ~100 byte) + check estensione. Nessuna I/O di rete.

**Formato reminder**:
```
STOP — Stai modificando codice di produzione ({file_path}) ma NON hai invocato siae-tdd in questa sessione.
La Legge di Ferro: TEST PRIMA DEL CODICE, SEMPRE.
Invoca siae-tdd PRIMA di scrivere codice di produzione.
```

---

### Fix 4 — PreToolUse su `EnterPlanMode` per `siae-brainstorming`

**File nuovo**: `hooks/plan-gate`
**hooks.json**: aggiungere PreToolUse entry con matcher `EnterPlanMode`

**Logica**:
1. Leggere `~/.claude/.devforge-session-skills`
2. Se `siae-brainstorming` non è presente → iniettare reminder
3. Altrimenti → `echo '{}'`

Hook molto semplice (~30 righe).

**Formato reminder**:
```
STOP — Stai per entrare in PlanMode ma NON hai invocato siae-brainstorming.
NESSUNA IMPLEMENTAZIONE SENZA DESIGN APPROVATO.
Invoca siae-brainstorming PRIMA di procedere con il piano.
```

---

### Fix 5 — Fallback `jq` nel `stop-gate`

**File**: `hooks/stop-gate` righe 86-94

**Fix**: cascata di fallback per JSON parsing: `jq` → `node -e` → `python3 -c`

```bash
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
        let d=''; process.stdin.on('data',c=>d+=c);
        process.stdin.on('end',()=>{
            try {
                const j=JSON.parse(d);
                const msgs=(j.messages||j.transcript||[]).filter(m=>m.role==='assistant');
                const last=msgs[msgs.length-1];
                if(!last){process.stdout.write('');return;}
                const c=last.content;
                if(typeof c==='string'){process.stdout.write(c);}
                else{process.stdout.write((c||[]).filter(b=>b.type==='text').map(b=>b.text).join(' '));}
            }catch{process.stdout.write('');}
        });
    " 2>/dev/null || true)
elif command -v python3 >/dev/null 2>&1; then
    LAST_ASSISTANT_MSG=$(echo "$INPUT" | python3 -c "
import sys,json
try:
    j=json.load(sys.stdin)
    msgs=[m for m in (j.get('messages') or j.get('transcript') or []) if m.get('role')=='assistant']
    if not msgs: print('',end='')
    else:
        c=msgs[-1].get('content','')
        if isinstance(c,str): print(c,end='')
        else: print(' '.join(b.get('text','') for b in c if b.get('type')=='text'),end='')
except: print('',end='')
    " 2>/dev/null || true)
fi
```

**Priorità cascata**: jq (più veloce, < 10ms) → node (già dipendenza plugin) → python3 (quasi sempre presente su macOS/Linux).

---

### Fix 6 — Re-injection catalogo periodica

**File**: `hooks/pre-commit` (modifica al blocco else di riga 79-82)

**Meccanismo**: contatore file-based `~/.claude/.devforge-tool-counter`. Ogni invocazione Bash incrementa il contatore. Ogni N invocazioni (default: 20), re-iniettare il catalogo skill come additional_context.

```bash
# All'inizio del pre-commit, PRIMA del routing git/non-git:
TOOL_COUNTER_FILE="${HOME}/.claude/.devforge-tool-counter"
COUNTER=$(cat "$TOOL_COUNTER_FILE" 2>/dev/null || echo "0")
COUNTER=$((COUNTER + 1))
echo "$COUNTER" > "$TOOL_COUNTER_FILE"

CATALOG_REINJECT=""
REINJECT_INTERVAL=20
if [ $((COUNTER % REINJECT_INTERVAL)) -eq 0 ]; then
    # Genera catalogo leggero (solo tabella, non tutta using-devforge)
    if command -v node >/dev/null 2>&1; then
        CATALOG_REINJECT=$(node "${PLUGIN_ROOT}/lib/skills-core.js" "${PLUGIN_ROOT}" 2>/dev/null || echo "")
    fi
fi
```

**Dove iniettare**:
- Per comandi `git commit`: append al quality gate context (insieme al Fix 2)
- Per comandi `git checkout -b`: append al branch warning
- Per **tutti gli altri comandi** (blocco else riga 79-82): se `CATALOG_REINJECT` non è vuoto, emettere JSON con additional_context contenente il catalogo invece di `echo '{}'`

**Nota su compact**: il SessionStart hook già copre il compact event (matcher `startup|resume|clear|compact`). Il Fix 6 aggiunge copertura per i periodi PRIMA che il compact scatti.

**Il contatore viene resettato al SessionStart** (aggiungere reset in `session-start` riga 165-167):
```bash
echo "0" > "${HOME}/.claude/.devforge-tool-counter"
```

---

## Modifiche ai file

| File | Tipo modifica | Fix |
|------|--------------|-----|
| `lib/skills-core.js` | Edit (1 riga) | Fix 1 |
| `hooks/pre-commit` | Edit (aggiunta ~40 righe) | Fix 2, Fix 6 |
| `hooks/tdd-gate` | Nuovo file (~60 righe) | Fix 3 |
| `hooks/plan-gate` | Nuovo file (~40 righe) | Fix 4 |
| `hooks/hooks.json` | Edit (aggiunta 2 entries) | Fix 3, Fix 4 |
| `hooks/stop-gate` | Edit (sostituzione ~10 righe con ~30 righe) | Fix 5 |
| `hooks/session-start` | Edit (aggiunta 1 riga reset counter) | Fix 6 |

## Criteri di accettazione

- [ ] `node lib/skills-core.js .` mostra trigger puliti (solo keyword) per tutte le skill con `Trigger:`
- [ ] `git commit` senza `siae-git-workflow` in session → reminder visibile nel context
- [ ] `Edit` su file `.java` senza `siae-tdd` in session → reminder visibile
- [ ] `Edit` su file `.md` → nessun reminder (non è codice produzione)
- [ ] `EnterPlanMode` senza `siae-brainstorming` in session → reminder visibile
- [ ] `stop-gate` funziona senza `jq` (testare con `PATH` senza jq)
- [ ] Dopo 20 Bash call, il catalogo viene re-iniettato
- [ ] Dopo `compact`, il catalogo viene re-iniettato (già funzionante)
- [ ] `bash tests/run-all.sh` passa (test strutturali)
- [ ] Nessuna regressione sugli hook esistenti
