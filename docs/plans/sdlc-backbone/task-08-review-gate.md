# Task 08: Nuova Skill siae-review-gate

**Dipendenze:** Task 01 (frontmatter metadata)
**File coinvolti:** nuovo `skills/siae-review-gate/SKILL.md`

---

## Step 1 — Crea directory e SKILL.md

```bash
mkdir -p skills/siae-review-gate
```

Contenuto di `skills/siae-review-gate/SKILL.md`:

```yaml
---
name: siae-review-gate
description: >
  Orchestra la fase di review: verifica file modificati, suggerisce tipo
  di review, avanza la fase SDLC. Backbone skill per la fase review.
triggers:
  - review
  - pronto per review
  - code review
  - chiedi review
  - rivedi il codice
type: Rigid
sdlc_phase: "5. Review"
backbone_role: backbone
backbone_stage: review
hard_gate: true
---

# siae-review-gate — Fase Review SDLC

> **Tipo:** Rigid | **Fase SDLC:** 5. Review

## LA LEGGE DI FERRO

NESSUNA CHIUSURA SENZA REVIEW

## Scopo

Orchestra la fase di review del backbone SDLC. Verifica che ci sia codice
da revieware, suggerisce il tipo di review appropriato, e avanza la fase.

## Processo

### Step 1 — Verifica file modificati

Controlla che ci siano file modificati rispetto al branch base:

git diff --stat $(git merge-base HEAD origin/main)..HEAD

Se nessun file modificato: "Nessun codice da revieware. La fase review e'
completata vacuamente."

### Step 2 — Suggerisci tipo di review

| Condizione | Review suggerita |
|-----------|-----------------|
| PR aperta e review richiesta | siae-receiving-review |
| Codice pronto, nessuna PR | siae-requesting-review |
| Utente chiede audit indipendente | siae-blind-review |

### Step 3 — Avanza fase

Dopo che il review type scelto e' stato completato, la fase review e' completata.
L'utente puo' procedere a verification.
```

## Step 2 — Aggiorna generate-manifest.js

Esegui `node scripts/generate-manifest.js` per aggiornare i conteggi (38 skill ora).

## Step 3 — Verifica

```bash
# Skill esiste e ha frontmatter corretto
node -e "
const {findSkillsInDir} = require('./lib/skills-core');
const skills = findSkillsInDir('./skills');
const rg = skills.find(s => s.name === 'siae-review-gate');
console.assert(rg, 'siae-review-gate not found');
console.assert(rg.backbone_role === 'backbone', 'Expected backbone role');
console.assert(rg.backbone_stage === 'review', 'Expected review stage');
console.log('PASS');
"
```

## Step 4 — Commit

```bash
git add skills/siae-review-gate/SKILL.md .claude-plugin/plugin.json .claude-plugin/marketplace.json README.md
git commit -m "feat(backbone): add siae-review-gate backbone skill for review phase

- New skill that orchestrates the review phase
- Suggests review type (blind, requesting, receiving)
- Backbone role, review stage, hard gate

Co-Authored-By: SIAE DevForge"
```
