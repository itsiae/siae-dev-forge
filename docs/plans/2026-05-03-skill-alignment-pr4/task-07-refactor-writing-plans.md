# Task 07 — Refactor `siae-writing-plans` (Progressive Disclosure + Description Rewrite)

**Goal:** Ridurre `siae-writing-plans/SKILL.md` da 422 a <200 righe.

**File coinvolti:**
- `skills/siae-writing-plans/SKILL.md`
- `skills/siae-writing-plans/reference/writing-plans-task-template.md` (nuovo)
- `skills/siae-writing-plans/reference/writing-plans-execution-handoff.md` (nuovo)

## Step 1 — Heading map

```bash
wc -l skills/siae-writing-plans/SKILL.md
grep -n '^##\|^###' skills/siae-writing-plans/SKILL.md
```

Sezioni candidate:
- Template task bite-sized (formato dettagliato) → `reference/writing-plans-task-template.md`
- Pattern subagent-development integration → `reference/writing-plans-execution-handoff.md`

## Step 2 — Crea reference

```bash
mkdir -p skills/siae-writing-plans/reference
```

## Step 3 — Estrai template task bite-sized

In `reference/writing-plans-task-template.md`:

```markdown
# siae-writing-plans — Template Task Bite-Sized

> Reference linked da `../SKILL.md`. Pattern dettagliato per ogni task-NN-*.md.

## Anatomia task

[contenuto template completo: file coinvolti, step TDD, codice, comandi]

## Esempio completo

[esempio task con tutte le sezioni]

## Anti-pattern

[lista anti-pattern: vague "implementa la validazione", path generici, ecc.]
```

## Step 4 — Estrai execution handoff

In `reference/writing-plans-execution-handoff.md`:

```markdown
# siae-writing-plans — Execution Handoff

> Reference linked da `../SKILL.md`. Pattern dettagliato Step 5.

## Subagent (stessa sessione)
[contenuto]

## Sessione separata
[contenuto]

## Decisione: quale scegliere
[flowchart criteri]
```

## Step 5 — Rewrite SKILL.md <200

Struttura:
1. Frontmatter "Use when X"
2. HARD-GATE inline
3. Processo step 1-5 (summary 1 riga ciascuno con link)
4. Step 3b placeholder scan (obbligatorio inline, è gate critico)
5. Step 3c plan review (obbligatorio inline, è gate critico)
6. REQUIRED SUB-SKILL list

Frontmatter target:

```yaml
---
name: siae-writing-plans
description: >
  Use when transforming an approved design doc into a step-by-step implementation
  plan with bite-sized tasks. Produces docs/plans/<topic>/ directory with overview
  + task-NN files. Examples: "scrivi piano implementativo", "decomponi design in
  task", "trasforma design in piano".
---
```

Body summary:

```markdown
## Processo

1. **Leggi design doc** approvato in `docs/plans/`
2. **Decomponi** in task atomici 2-5 minuti — template: `reference/writing-plans-task-template.md`
3. **Scrivi** piano come directory `docs/plans/<topic>/` con overview + task-NN files
4. **Placeholder scan** (gate inline) — zero TBD/TODO/vague
5. **Plan review** (gate inline) — subagent reviewer, max 5 iterazioni
6. **Salva + commit** + execution handoff — vedi `reference/writing-plans-execution-handoff.md`
```

## Step 6 — Verifica

```bash
wc -l skills/siae-writing-plans/SKILL.md  # <200
```

## Step 7 — Smoke test no-regression

Prompt test:
- "scrivi piano implementativo per X" → skill attivata
- "decomponi design in task" → skill attivata
- "trasforma il design in piano" → skill attivata

## Step 8 — Commit

```bash
git add skills/siae-writing-plans/
git commit -m "refactor(skills): siae-writing-plans progressive disclosure (422 → <200)

- Template task bite-sized e execution handoff estratti in reference/
- Description riscritta 'Use when X' Anthropic pattern
- Step 3b placeholder scan e Step 3c plan review mantenuti inline (gate critici)
- NO-REGRESSION verificata su 3 smoke prompt"
```

## Criteri accettazione

- `wc -l` < 200
- 2 file in `reference/`
- Step 3b/3c gate mantenuti INLINE (non spostare in reference, sono critici)
- 3 smoke prompt attivano la skill

## NO-REGRESSION

Skill `siae-writing-plans` deve continuare ad attivarsi su prompt di pianificazione post-design. Verifica anche che cross-link `REQUIRED SUB-SKILL: siae-subagent-development` e `siae-executing-plans` siano preservati.
