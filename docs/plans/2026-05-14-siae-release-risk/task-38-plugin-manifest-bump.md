# Task 38 — plugin manifest bump 1.56→1.57

**Stato:** [PENDING]
**SP:** 0.5 Human / 0.25 Augmented
**Dipendenze:** task-02 (audit), task-37 (eval ready)

## Goal

Aggiornare `.claude-plugin/plugin.json`: version 1.56.0 → 1.57.0 + description con count post-merge corretti.

## File coinvolti

- Edit: `.claude-plugin/plugin.json`

## Step

### Step 1 — Read current

Read `.claude-plugin/plugin.json`. Verifica version corrente `1.56.0`.

### Step 2 — Edit

Edit `.claude-plugin/plugin.json`:
```json
{
  "name": "siae-devforge",
  "description": "SIAE Development Forge - AI SDLC Chain per sviluppo software conforme a standard SIAE. 42 skill, 17 comandi, 5 agent, 24 hook.",
  "version": "1.57.0",
  "author": { "name": "SIAE AI Competence Center", "email": "ai-cc@siae.it" },
  "homepage": "https://github.com/itsiae/siae-dev-forge",
  "repository": "https://github.com/itsiae/siae-dev-forge",
  "license": "PROPRIETARY",
  "keywords": ["siae", "sdlc", "tdd", "code-review", "architecture", "devforge"]
}
```

### Step 3 — Verifica JSON

```bash
python3 -c "import json; v = json.loads(open('.claude-plugin/plugin.json').read()); print(v['version'], '|', v['description'])"
```
Output atteso: `1.57.0 | SIAE Development Forge - ... 42 skill, 17 comandi, 5 agent, 24 hook.`

### Step 4 — Commit

```bash
git add .claude-plugin/plugin.json
git commit -m "chore(release-risk): plugin manifest bump 1.56.0 → 1.57.0 + count audit (42/17/5/24)"
```

## Criteri di accettazione

- [ ] `version: "1.57.0"`
- [ ] `description` con count corretti: 42 skill, 17 comandi, 5 agent, 24 hook
- [ ] JSON valid
- [ ] Commit eseguito
