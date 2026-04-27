# Task 12 — Rimuovere 3 hook fusi + aggiornare hooks.json

**Stato:** [PENDING]
**Execution:** in-session
**Dipendenze:** T11 (devforge-context esiste e tested)
**Durata stimata:** 8 min

## Goal

Sostituire i 3 hook `UserPromptSubmit` con il solo `devforge-context`. `batch-reset` resta. Archivio (non elimina) i 3 hook rimossi in `hooks/.archived/` per forensic/rollback.

## Step

### Step 1: archive hook obsoleti

```bash
mkdir -p hooks/.archived
git mv hooks/user-prompt-context hooks/.archived/user-prompt-context-v1.45
git mv hooks/devforge-reinject hooks/.archived/devforge-reinject-v1.45
git mv hooks/devforge-context-always hooks/.archived/devforge-context-always-v1.45
```

### Step 2: aggiorna hooks/hooks.json

**Prima (righe 16-41 pattern attuale)**:

```json
"UserPromptSubmit": [
  {
    "matcher": "",
    "hooks": [
      { "command": "... user-prompt-context", "timeout": 5 },
      { "command": "... devforge-reinject", "timeout": 5 },
      { "command": "... devforge-context-always", "timeout": 5 },
      { "command": "... batch-reset", "timeout": 5 }
    ]
  }
]
```

**Dopo**:

```json
"UserPromptSubmit": [
  {
    "matcher": "",
    "hooks": [
      {
        "type": "command",
        "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' devforge-context",
        "timeout": 5
      },
      {
        "type": "command",
        "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' batch-reset",
        "timeout": 5
      }
    ]
  }
]
```

### Step 3: verifica JSON valido

```bash
python3 -c "import json; json.load(open('hooks/hooks.json')); print('JSON ok')"
```
Output atteso: `JSON ok`.

### Step 4: verifica che tutti gli hook referenziati esistono

```bash
python3 <<'PY'
import json, os, sys
h = json.load(open('hooks/hooks.json'))
missing = []
for event, configs in h['hooks'].items():
    for cfg in configs:
        for hook in cfg['hooks']:
            # Extract hook name from command
            cmd = hook['command']
            if "run-hook.cmd'" in cmd:
                name = cmd.split("run-hook.cmd'")[1].strip().strip("'\"")
                if not os.path.exists(f"hooks/{name}"):
                    missing.append(f"{event}: {name}")
print("MISSING:" if missing else "ALL OK")
for m in missing: print(" ", m)
sys.exit(1 if missing else 0)
PY
```
Output atteso: `ALL OK`.

### Step 5: smoke test invocazione

```bash
echo '{}' | bash hooks/run-hook.cmd devforge-context 2>&1 | head -5
```
Output atteso: JSON valido (non errore).

### Step 6: re-run baseline suite

```bash
bash tests/run-all.sh 2>&1 | grep -E "PASS:|FAIL:|SKIP" | tail -3
```
Output atteso: `PASS: >= 168`, `FAIL: <= 6`.

### Step 7: commit

```bash
git add hooks/hooks.json hooks/.archived/
git commit -m "refactor(hooks): replace 3 UserPromptSubmit hooks with devforge-context

Part of PR #1 anti-dilution (ADR-004).
Removed from hooks.json UserPromptSubmit chain:
- user-prompt-context
- devforge-reinject
- devforge-context-always

Replaced by: devforge-context (unified, budget 2KB, diff-based dedup).
batch-reset retained (separate responsibility).

Archived files in hooks/.archived/ for forensic/rollback.

Net effect:
- 3 hook invocations -> 1 per UserPromptSubmit
- ~12KB periodic reinject -> <=2KB per-emission with dedup
- EXTREMELY_IMPORTANT wolf-cry -> tier-based usage only"
```

## Acceptance

- [ ] 3 hook spostati in `hooks/.archived/` (non eliminati)
- [ ] `hooks/hooks.json` mostra solo 2 hook UserPromptSubmit: devforge-context + batch-reset
- [ ] JSON valido (python3 json.load ok)
- [ ] Tutti gli hook referenziati esistono fisicamente
- [ ] `tests/run-all.sh` baseline preserved (PASS >= 168, FAIL <= 6)
- [ ] Commit `refactor(hooks):`

## Safeguard

Se `tests/run-all.sh` regressa:
1. `git reset --hard HEAD~1` per annullare commit
2. Analizza quale test regressa
3. Se è un test che controllava specificamente `user-prompt-context`/`devforge-reinject`/`devforge-context-always`: aggiorna il test per puntare a `devforge-context` (il comportamento funzionale va preservato)
4. Se è un test comportamentale: fix devforge-context per coprire la gap
