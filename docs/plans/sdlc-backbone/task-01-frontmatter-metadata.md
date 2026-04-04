# Task 01: Frontmatter Backbone Metadata

**Dipendenze:** nessuna
**File coinvolti:** 37 `skills/*/SKILL.md` + nuova `skills/siae-review-gate/SKILL.md`

---

## Step 1 — Aggiungi 3 campi a ogni SKILL.md

Per ciascuna delle 38 skill (37 esistenti + siae-review-gate da Task 8), aggiungere nel frontmatter YAML:

```yaml
backbone_role: backbone | specialist | support
backbone_stage: brainstorming | plan | execution | tdd | review | verification | finish | null
hard_gate: true | false
```

## Step 2 — Mappa completa

### Backbone (7 skill)

| Skill | backbone_stage | hard_gate |
|-------|---------------|-----------|
| siae-brainstorming | brainstorming | true |
| siae-writing-plans | plan | true |
| siae-executing-plans | execution | false |
| siae-tdd | tdd | true |
| siae-review-gate | review | true |
| siae-verification | verification | true |
| siae-finishing-branch | finish | true |

### Specialist (22 skill)

| Skill | backbone_stage |
|-------|---------------|
| siae-architecture | brainstorming |
| siae-codebase-map | brainstorming |
| siae-microservices-map | brainstorming |
| siae-service-logic-map | brainstorming |
| siae-code-standards | execution |
| siae-security | execution |
| siae-iac | execution |
| siae-data-engineering | execution |
| siae-frontend | execution |
| siae-flutter | execution |
| siae-finops | execution |
| siae-parallel-agents | execution |
| siae-subagent-development | execution |
| siae-automation | tdd |
| siae-qa | tdd |
| siae-robot-framework | tdd |
| siae-nr-test-flows | tdd |
| siae-requesting-review | review |
| siae-receiving-review | review |
| siae-blind-review | review |
| siae-debugging | verification |
| siae-documentation | finish |
| siae-git-workflow | finish |

### Support (8 skill)

| Skill | backbone_stage |
|-------|---------------|
| siae-onboarding | null |
| siae-git-env | null |
| siae-git-worktrees | null |
| siae-writing-skills | null |
| siae-autoresearch | null |
| siae-retrospective | null |
| siae-branching-strategy-check | null |
| using-devforge | null |

## Step 3 — Aggiorna extractFrontmatter in skills-core.js

`extractFrontmatter()` deve estrarre anche `backbone_role`, `backbone_stage`, `hard_gate` e passarli in `findSkillsInDir()`.

In `skills-core.js`, aggiornare `findSkillsInDir` per includere i nuovi campi:

```javascript
skills.push({
  name: fm.name,
  description: fm.description || '',
  triggers: fm.triggers || [],
  type: fm.type || null,
  sdlc_phase: fm.sdlc_phase || null,
  backbone_role: fm.backbone_role || 'support',
  backbone_stage: fm.backbone_stage || null,
  hard_gate: fm.hard_gate === true || fm.hard_gate === 'true',
  dirName: entry.name,
  filePath: skillFile,
});
```

## Step 4 — Verifica

```bash
node -e "
const {findSkillsInDir} = require('./lib/skills-core');
const skills = findSkillsInDir('./skills');
const missing = skills.filter(s => !s.backbone_role);
if (missing.length) {
  missing.forEach(s => console.error('MISSING backbone_role:', s.name));
  process.exit(1);
}
const backbone = skills.filter(s => s.backbone_role === 'backbone');
const specialist = skills.filter(s => s.backbone_role === 'specialist');
const support = skills.filter(s => s.backbone_role === 'support');
console.log('Backbone:', backbone.length, backbone.map(s=>s.name));
console.log('Specialist:', specialist.length);
console.log('Support:', support.length);
console.assert(backbone.length === 7, 'Expected 7 backbone skills');
console.log('PASS');
"
```

## Step 5 — Commit

```bash
git add skills/*/SKILL.md lib/skills-core.js
git commit -m "feat(backbone): add backbone_role/backbone_stage/hard_gate to all 38 SKILL.md

- 7 backbone skills: brainstorming, plan, execution, tdd, review, verification, finish
- 22 specialist skills: mapped to their backbone stage
- 8 support skills: no stage binding
- skills-core.js extracts new frontmatter fields

Co-Authored-By: SIAE DevForge"
```
