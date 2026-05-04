# Task 08 — Refactor `siae-executing-plans` (Progressive Disclosure + Description Rewrite)

**Goal:** Ridurre `siae-executing-plans/SKILL.md` da 344 a <200 righe.

**File coinvolti:**
- `skills/siae-executing-plans/SKILL.md`
- `skills/siae-executing-plans/reference/executing-plans-worktree.md` (nuovo)
- `skills/siae-executing-plans/reference/executing-plans-sync.md` (nuovo)

## Step 1 — Heading map

```bash
wc -l skills/siae-executing-plans/SKILL.md
grep -n '^##\|^###' skills/siae-executing-plans/SKILL.md
```

Sezioni candidate:
- Setup worktree dettagliato → `reference/executing-plans-worktree.md`
- Checkpoint sync con writing-plans (stato task aggiornamento) → `reference/executing-plans-sync.md`

## Step 2 — Crea reference

```bash
mkdir -p skills/siae-executing-plans/reference
```

## Step 3 — Estrai worktree setup

In `reference/executing-plans-worktree.md`:

```markdown
# siae-executing-plans — Worktree Setup Dettagliato

> Reference linked da `../SKILL.md`. Setup workspace isolato.

## Quando usare worktree
[contenuto]

## Comandi setup
[contenuto bash]

## Sync hooks DevForge
[contenuto: symlink .claude/]

## Cleanup
[contenuto]
```

## Step 4 — Estrai sync con writing-plans

In `reference/executing-plans-sync.md`:

```markdown
# siae-executing-plans — Sync Stato Task

> Reference linked da `../SKILL.md`. Aggiornamento [PENDING]/[DONE]/[BLOCKED].

## Marker stato
[contenuto]

## Checkbox sync (formato legacy)
[contenuto]

## Commit stato
[contenuto]
```

## Step 5 — Rewrite SKILL.md <200

Struttura:
1. Frontmatter "Use when X"
2. HARD-GATE
3. Esecuzione step-by-step (summary)
4. Batch logic
5. REQUIRED SUB-SKILL: siae-git-worktrees (link a reference per dettagli)

Frontmatter:

```yaml
---
name: siae-executing-plans
description: >
  Use when executing an approved implementation plan in a separate session
  (different from where plan was written). Reads docs/plans/<topic>/ overview +
  task-NN files, executes batch with human checkpoints. Examples: "esegui il
  piano nella sessione nuova", "carica piano e implementa".
---
```

## Step 6 — Verifica

```bash
wc -l skills/siae-executing-plans/SKILL.md  # <200
```

## Step 7 — Smoke test

Prompt: "carica il piano e implementa" → skill attivata.

## Step 8 — Commit

```bash
git add skills/siae-executing-plans/
git commit -m "refactor(skills): siae-executing-plans progressive disclosure (344 → <200)

- Worktree setup e task state sync estratti in reference/
- Description 'Use when X' pattern
- NO-REGRESSION verificata"
```

## Criteri accettazione

- `wc -l` < 200
- 2 file `reference/`
- Smoke prompt attiva skill

## NO-REGRESSION

Cross-link `REQUIRED SUB-SKILL: siae-git-worktrees` deve essere preservato.
