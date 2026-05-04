# Task 09 — Refactor `siae-brainstorming` (Progressive Disclosure + Description Rewrite)

**Goal:** Ridurre `siae-brainstorming/SKILL.md` da 214 a <180 righe (bloat lieve).

**File coinvolti:**
- `skills/siae-brainstorming/SKILL.md`
- `skills/siae-brainstorming/reference/brainstorming-checklist.md` (nuovo)
- `skills/siae-brainstorming/reference/brainstorming-jira.md` (nuovo)

## Step 1 — Heading map

```bash
wc -l skills/siae-brainstorming/SKILL.md
grep -n '^##\|^###' skills/siae-brainstorming/SKILL.md
```

Sezioni candidate:
- Checklist 7 punti dettagliata → `reference/brainstorming-checklist.md`
- JIRA integration completa (JQL queries, output ticket format) → `reference/brainstorming-jira.md`

## Step 2 — Crea reference

```bash
mkdir -p skills/siae-brainstorming/reference
```

## Step 3 — Estrai checklist

In `reference/brainstorming-checklist.md`:

```markdown
# siae-brainstorming — Checklist 7 Punti Dettagliata

> Reference linked da `../SKILL.md`. Dettaglio operativo Step 1-7.

## Step 1 — Smart Intake (dettagli)
[contenuto fonti, tabelle confidence, esempi]

## Step 2 — Scope Assessment (dettagli)
[contenuto]

## Step 3 — Inferenze + domande (dettagli)
[contenuto]

## Step 3b — Option Zero Gate (dettagli)
[contenuto]

## Step 4 — Approcci + trade-off (dettagli, doppia scala SP)
[contenuto]

## Step 5 — Design per sezioni (dettagli)
[contenuto]

## Step 6 — Salva design (dettagli)
[contenuto template doc]
```

## Step 4 — Estrai JIRA integration

In `reference/brainstorming-jira.md`:

```markdown
# siae-brainstorming — Integrazione JIRA

> Reference linked da `../SKILL.md`. Pattern MCP Atlassian + ticket output.

## Discovery ticket correlati
[JQL queries]

## Stima Story Points doppia scala
[tabella SP-Umano vs SP-Augmented]

## Output JIRA ticket format
[template campi]

## Pre-flight card creazione ticket (🔴 ALTO)
[card]
```

## Step 5 — Rewrite SKILL.md target <180

Struttura:
1. Frontmatter "Use when X"
2. HARD-GATE (inline, critico)
3. Scaling table (inline, critico)
4. 7 punti summary (1-2 righe ciascuno + link reference)
5. Step 3b/3c/6b gate inline (critici, non in reference)
6. Output checkpoint format
7. Stato terminale

Frontmatter:

```yaml
---
name: siae-brainstorming
description: >
  Use when designing any implementation task before writing code (feature, bug
  fix, refactor, config change). Forces 7-step process: intake → scope → options →
  design → review → approval → handoff to siae-writing-plans. Mandatory before any
  code change. Examples: "come progettiamo X", "valutare opzioni", "prima di
  implementare", "design feature".
---
```

## Step 6 — Verifica

```bash
wc -l skills/siae-brainstorming/SKILL.md  # <180
```

## Step 7 — Smoke test no-regression

Prompt:
- "come progettiamo X" → skill attivata
- "valutare opzioni per nuova feature" → skill attivata
- "prima di implementare X" → skill attivata
- "design fix per bug Y" → skill attivata

## Step 8 — Commit

```bash
git add skills/siae-brainstorming/
git commit -m "refactor(skills): siae-brainstorming progressive disclosure (214 → <180)

- Checklist 7 punti dettagliata + JIRA integration estratte in reference/
- HARD-GATE + scaling + 7 step summary + 3b/3c/6b gate mantenuti inline
- Description 'Use when X' Anthropic pattern, mandatory keyword preserved
- NO-REGRESSION 4 smoke prompt verificati"
```

## Criteri accettazione

- `wc -l` < 180
- 2 file `reference/`
- HARD-GATE + scaling + 3b/3c/6b gate INLINE (non in reference)
- 4 smoke prompt attivano la skill

## NO-REGRESSION

Skill `siae-brainstorming` ha utilizzo mandatorio (memory: "brainstorming sempre mandatorio"). Deve continuare ad attivarsi su QUALSIASI prompt di design/implementazione. Test esteso post-task: 10 prompt diversi (feature, bug, config, refactor, ...) tutti attivano la skill.
