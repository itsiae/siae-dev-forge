# Task 02 — Plugin manifest count audit (pre-bump)

**Stato:** [PENDING]
**SP:** 1 Human / 0.5 Augmented
**Dipendenze:** task-01

## Goal

Eseguire audit accurato dei count nel `.claude-plugin/plugin.json` prima del bump 1.56→1.57, per fixare l'incoerenza attuale ("39 skill, 11 comandi, 3 agent, 21 hook" vs realtà 41/16/5/23).

## File coinvolti

- Read: `.claude-plugin/plugin.json` (description attuale)
- Audit on-disk: `skills/`, `commands/`, `agents/`, `hooks/`
- Output: `docs/plans/2026-05-14-siae-release-risk/manifest-audit.md` (audit report)

## Step

### Step 1 — Count skills

Run:
```bash
ls -1 skills/ | grep -vE "^\." | wc -l
```
Output atteso: `41`

### Step 2 — Count commands

Run:
```bash
ls -1 commands/*.md | wc -l
```
Output atteso: `16`

### Step 3 — Count agents

Run:
```bash
ls -1 agents/*.md | wc -l
```
Output atteso: `5` (code-reviewer, doc-generator, mcp-impact-analyst, qa-investigator, spec-reviewer). NOTA: `agents/SPORT_KG_TOOLS.yaml` NON conta come agent (è registry).

### Step 4 — Count hooks

Run:
```bash
ls -1 hooks/ | grep -vE "^(lib|run-hook\.cmd|hooks\.json|ENV_VARS\.md)$" | wc -l
```
Output atteso: `23`

### Step 5 — Scrivi audit report

Scrivi `docs/plans/2026-05-14-siae-release-risk/manifest-audit.md`:
```markdown
# Plugin manifest audit — pre-bump 1.57.0

| Tipo | On-disk pre-merge | Manifest attuale | Drift | Post-merge atteso |
|---|---|---|---|---|
| Skills | 41 | 39 | -2 | 42 (+1) |
| Commands | 16 | 11 | -5 | 17 (+1) |
| Agents | 5 | 3 | -2 | 5 (invariato) |
| Hooks | 23 | 21 | -2 | 24 (+1) |

**Drift cause:** manifest description non aggiornato in PR precedenti (recurring issue).
**Fix:** task-38 bump applica counts post-merge corretti (42/17/5/24).
```

### Step 6 — Commit audit

Run:
```bash
git add docs/plans/2026-05-14-siae-release-risk/manifest-audit.md
git commit -m "docs(release-risk): plugin manifest count audit pre-bump"
```

## Criteri di accettazione

- [ ] Count on-disk verificato per skills/commands/agents/hooks
- [ ] Audit report `manifest-audit.md` scritto con drift quantificato
- [ ] Counts post-merge documentati: 42 skill, 17 cmd, 5 agent, 24 hook
- [ ] Commit eseguito
