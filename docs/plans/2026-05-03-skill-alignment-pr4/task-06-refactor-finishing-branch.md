# Task 06 — Refactor `siae-finishing-branch` (Progressive Disclosure + Description Rewrite)

**Goal:** Ridurre `siae-finishing-branch/SKILL.md` da 520 a <200 righe (la skill più gonfia del backbone).

**File coinvolti:**
- `skills/siae-finishing-branch/SKILL.md`
- `skills/siae-finishing-branch/reference/finishing-branch-checklist.md` (nuovo)
- `skills/siae-finishing-branch/reference/finishing-branch-scenarios.md` (nuovo)

## Step 1 — Heading map

```bash
wc -l skills/siae-finishing-branch/SKILL.md
grep -n '^##\|^###' skills/siae-finishing-branch/SKILL.md
```

Identifica:
- Pre-flight checklist completa → `reference/finishing-branch-checklist.md`
- Scenari (revert, hotfix, squash merge follow-up) → `reference/finishing-branch-scenarios.md`

## Step 2 — Crea reference

```bash
mkdir -p skills/siae-finishing-branch/reference
```

## Step 3 — Estrai checklist completa

In `reference/finishing-branch-checklist.md`:

```markdown
# siae-finishing-branch — Checklist completa pre-PR

> Reference dettagliato linked da `../SKILL.md`. Use when ready to open PR.

## Pre-flight (obbligatorio)
[contenuto originale checklist]

## Coverage check
[contenuto]

## Branch hygiene
[contenuto]

## CHANGELOG / version bump
[contenuto]
```

## Step 4 — Estrai scenari

In `reference/finishing-branch-scenarios.md`:

```markdown
# siae-finishing-branch — Scenari specifici

> Reference linked da `../SKILL.md`. Casi non lineari.

## Revert PR già mergiata
[contenuto]

## Hotfix urgente
[contenuto]

## Post squash-merge follow-up
[contenuto]

## Rebase vs merge contesto branch lungo
[contenuto]
```

## Step 5 — Rewrite SKILL.md target <200 righe

Struttura:
1. Frontmatter "Use when X" pattern
2. HARD-GATE (mantenuto inline)
3. Sequenza step principali (5-7 step max, 1 riga ciascuno con link reference)
4. REQUIRED SUB-SKILL list (siae-blind-review, siae-receiving-review, siae-requesting-review)
5. Checkpoint format

Frontmatter target:

```yaml
---
name: siae-finishing-branch
description: >
  Use when preparing a feature/fix branch for PR. Pre-flight checklist completo
  (test, coverage, CHANGELOG, version bump, branch hygiene) prima di pushare e
  aprire la PR. Best after: siae-verification passed. Examples: "pronto per PR",
  "apro la PR", "ready to merge".
---
```

Body sequenza step:

```markdown
## Sequenza pre-PR

1. **Pre-flight checklist** — vedi `reference/finishing-branch-checklist.md`
2. **Smoke test** — esegui ultima volta tutti i test
3. **CHANGELOG / version bump** — vedi checklist sezione
4. **Branch hygiene** — squash WIP commits, rebase su main aggiornato
5. **Push + PR open** — `git push` + invoca `siae-requesting-review`

## Scenari specifici

Vedi `reference/finishing-branch-scenarios.md` (revert, hotfix, post-squash, ...).
```

## Step 6 — Verifica

```bash
wc -l skills/siae-finishing-branch/SKILL.md  # <200
ls skills/siae-finishing-branch/reference/   # 2 file
```

## Step 7 — Smoke test no-regression

Test prompt: "sono pronto per PR" → skill `siae-finishing-branch` deve attivarsi.
Test prompt: "apro pull request" → idem.
Test prompt: "ready to merge" → idem.

## Step 8 — Commit

```bash
git add skills/siae-finishing-branch/
git commit -m "refactor(skills): siae-finishing-branch progressive disclosure (520 → <200)

- Estratte checklist completa e scenari specifici in reference/
- Description riscritta 'Use when X. Best after: siae-verification passed'
- NO-REGRESSION: 3 smoke prompt verificati ('pronto per PR', 'apro PR', 'ready to merge')"
```

## Criteri accettazione

- `wc -l SKILL.md` < 200
- 2 file in `reference/`
- Description "Use when X" + sequence hint "Best after: siae-verification"
- 3 smoke prompt attivano la skill

## NO-REGRESSION reference

Pre-PR-4 baseline: skill si attivava su "pronto per PR", "ready to merge", "apro PR". Tutti devono ancora attivare la skill post-task.
