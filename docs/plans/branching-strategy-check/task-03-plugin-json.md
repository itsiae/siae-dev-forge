# Task 03 — Aggiorna plugin.json skill count

**Stato:** [PENDING]
**File coinvolti:**
- `.claude-plugin/plugin.json` (MODIFY)

---

## Step 1 — Modifica plugin.json

Apri `.claude-plugin/plugin.json` e modifica la descrizione:

```
# DA:
"description": "SIAE Development Forge - AI SDLC Chain per sviluppo software conforme a standard SIAE. 34 skill, 8 comandi, 3 agent, 5 hook.",

# A:
"description": "SIAE Development Forge - AI SDLC Chain per sviluppo software conforme a standard SIAE. 35 skill, 8 comandi, 3 agent, 5 hook.",
```

---

## Step 2 — Verifica

```bash
grep "skill" .claude-plugin/plugin.json
```

Output atteso: `35 skill`.

---

## Step 3 — Commit

```bash
git add .claude-plugin/plugin.json
git commit -m "chore(plugin): bump skill count to 35 (add branching-strategy-check)"
```
