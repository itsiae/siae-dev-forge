# Task 35 — Register pr-release-gate in hooks.json

**Stato:** [PENDING]
**SP:** 0.5 Human / 0.25 Augmented
**Dipendenze:** task-34

## Goal

Aggiungere entry per `pr-release-gate` in `hooks/hooks.json` come PostToolUse Bash matcher.

## File coinvolti

- Edit: `hooks/hooks.json`

## Step

### Step 1 — Edit hooks.json

Leggi `hooks/hooks.json`, trova sezione `PostToolUse.matcher=Bash`, aggiungi entry:
```json
{
  "type": "command",
  "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" pr-release-gate",
  "timeout": 30
}
```

(Concretamente: nell'array `"hooks"` del matcher `Bash` dentro `PostToolUse`, aggiungi questo nuovo entry come ULTIMO hook PostToolUse:Bash.)

### Step 2 — Verifica JSON valid

Run:
```bash
python3 -c "import json; json.loads(open('hooks/hooks.json').read())"
```
Output atteso: no errors.

### Step 3 — Verifica entry presente

Run:
```bash
grep -c "pr-release-gate" hooks/hooks.json
```
Output atteso: `1`

### Step 4 — Commit

```bash
git add hooks/hooks.json
git commit -m "feat(release-risk): register pr-release-gate hook in hooks.json"
```

## Criteri di accettazione

- [ ] Entry aggiunta in `PostToolUse[matcher=Bash].hooks[]`
- [ ] Timeout: 30
- [ ] JSON syntax valid
- [ ] grep count: 1 occorrenza
- [ ] Commit eseguito
