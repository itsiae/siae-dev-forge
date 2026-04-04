# Task 07: Frontmatter Strutturato (D7)

**Deliverable:** D7
**Dipendenze:** Task 05 (js-yaml parser)
**File coinvolti:** 37 `skills/*/SKILL.md`, `lib/skills-core.js`

---

## Step 1 — Genera la mappa tipo/fase attuale dalle mappe hardcoded

```bash
node -e "
const sc = require('./lib/skills-core');
const skills = sc.findSkillsInDir('./skills');
const catalog = sc.buildCatalog('.');
catalog.skills.forEach(s => {
  console.log(s.name + '|' + s.type + '|' + s.phase + '|' + s.trigger.substring(0,80));
});
" | sort
```

Salva l'output come riferimento per popolare i nuovi campi frontmatter.

## Step 2 — Aggiungi `triggers`, `type`, `sdlc_phase` a ogni SKILL.md

Per ciascuna delle 37 skill, apri `skills/<nome>/SKILL.md` e aggiungi i 3 campi al frontmatter YAML.

**Template:**
```yaml
---
name: <nome>
description: >
  <descrizione esistente — rimuovere la parte "Trigger: ..." dalla description>
triggers:
  - <keyword 1>
  - <keyword 2>
  - <keyword N>
type: <Rigid|Flexible|Auto>
sdlc_phase: "<fase>"
---
```

**Regole:**
- I trigger vengono estratti dalla stringa `Trigger:` che oggi e' nella description
- Rimuovi `Trigger: ...` dalla description (non serve piu')
- `type` e `sdlc_phase` dai valori delle mappe hardcoded attuali in skills-core.js
- Skill non presenti nelle mappe: inferisci dal contenuto della skill (cerca "Tipo: Rigid" o "Tipo: Flexible")

**Skill da aggiornare (tutte le 37):**

| Skill | type | sdlc_phase |
|-------|------|------------|
| siae-architecture | Flexible | 2. Design |
| siae-automation | Rigid | 5. Testing / Automation |
| siae-autoresearch | Flexible | Meta |
| siae-blind-review | Rigid | Cross-cutting |
| siae-brainstorming | Rigid | 2. Design |
| siae-branching-strategy-check | Rigid | 3. Branching |
| siae-code-standards | Flexible | 4. Implementation |
| siae-codebase-map | Flexible | 1. Init |
| siae-data-engineering | Flexible | 4. Implementation |
| siae-debugging | Rigid | 6. QA Gate |
| siae-documentation | Flexible | 7. Release |
| siae-executing-plans | Rigid | 4. Implementation |
| siae-finishing-branch | Rigid | 3. Branching |
| siae-finops | Flexible | 4. Implementation |
| siae-flutter | Flexible | 4. Implementation |
| siae-frontend | Flexible | 4. Implementation |
| siae-git-env | Rigid | 3. Branching |
| siae-git-workflow | Rigid | 3. Branching |
| siae-git-worktrees | Rigid | 1. Init |
| siae-iac | Flexible | 4. Implementation |
| siae-microservices-map | Flexible | 1. Init |
| siae-nr-test-flows | Flexible | 5. Testing / QA |
| siae-onboarding | Auto | 1. Init |
| siae-parallel-agents | Flexible | 4. Implementation |
| siae-qa | Rigid | 5. Testing / QA |
| siae-receiving-review | Flexible | Cross-cutting |
| siae-requesting-review | Flexible | Cross-cutting |
| siae-retrospective | Flexible | Cross-cutting |
| siae-robot-framework | Flexible | 5. Testing / Automation |
| siae-security | Flexible | 4. Implementation |
| siae-service-logic-map | Flexible | 1. Init |
| siae-subagent-development | Rigid | 4. Implementation |
| siae-tdd | Rigid | 5. Testing |
| siae-verification | Rigid | Cross-cutting |
| siae-writing-plans | Rigid | 2. Design |
| siae-writing-skills | Flexible | Meta |
| using-devforge | Auto | Meta |

## Step 3 — Aggiorna `inferSkillMeta()` in skills-core.js

Rimuovi `nameTypeMap` (righe 181-201) e `namePhaseMap` (righe 225-255). Sostituisci con lettura dal frontmatter:

```javascript
function inferSkillMeta(skill) {
  // Type: from frontmatter (primary), fallback to content-based inference
  let type = skill.type || null;
  if (!type) {
    type = 'Flexible';
    try {
      const content = fs.readFileSync(skill.filePath, 'utf8').toLowerCase();
      if (/tipo:\s*\*{0,2}\s*rigid/i.test(content)) type = 'Rigid';
    } catch { /* keep default */ }
  }

  // Phase: from frontmatter (primary), fallback to description-based inference
  let phase = skill.sdlc_phase || 'Cross-cutting';

  // Trigger: from frontmatter triggers array (primary), fallback to description
  let trigger = '';
  if (Array.isArray(skill.triggers) && skill.triggers.length > 0) {
    trigger = skill.triggers.join(', ');
  } else {
    trigger = skill.description || '';
    const triggerMatch = trigger.match(/[Tt]rigger:\s*(.+)/);
    if (triggerMatch) {
      trigger = triggerMatch[1].split('.')[0].trim();
    } else {
      trigger = trigger.split('.')[0].replace(/^Use when\s*/i, '').trim();
    }
  }
  if (trigger.length > 120) trigger = trigger.substring(0, 117) + '...';

  return { type, phase, trigger };
}
```

## Step 4 — Aggiorna `findSkillsInDir` per passare i nuovi campi

```javascript
skills.push({
  name: fm.name,
  description: fm.description || '',
  triggers: fm.triggers || [],      // NUOVO
  type: fm.type || null,             // NUOVO
  sdlc_phase: fm.sdlc_phase || null, // NUOVO
  dirName: entry.name,
  filePath: skillFile,
});
```

## Step 5 — Verifica che tutte le skill hanno i 3 campi

```bash
node -e "
const {findSkillsInDir} = require('./lib/skills-core');
const skills = findSkillsInDir('./skills');
const missing = skills.filter(s => !s.triggers?.length || !s.type || !s.sdlc_phase);
if (missing.length) {
  missing.forEach(s => console.error('MISSING:', s.name, {triggers: !!s.triggers?.length, type: !!s.type, phase: !!s.sdlc_phase}));
  process.exit(1);
}
console.log('PASS: all', skills.length, 'skills have triggers, type, sdlc_phase');
"
```
Output atteso: PASS.

## Step 6 — Verifica che il catalogo Markdown e' invariato

```bash
# Il catalogo Markdown deve produrre le stesse skill di prima
node -e "
const {buildCatalog} = require('./lib/skills-core');
const c = buildCatalog('.');
console.log('Skills in catalog:', c.count);
console.assert(c.count >= 36, 'Expected at least 36 skills in catalog');
console.log('PASS');
"
```

## Step 7 — Run test suite

```bash
tests/run-all.sh --fast
```
Output atteso: tutti i test passano.

## Step 8 — Commit

```bash
git add skills/*/SKILL.md lib/skills-core.js
git commit -m "feat(triggering): add structured triggers/type/sdlc_phase to all 37 SKILL.md

- Each skill now declares triggers (keyword list), type, sdlc_phase in frontmatter
- skills-core.js reads from frontmatter instead of hardcoded maps
- Remove nameTypeMap and namePhaseMap (~70 lines)
- Remove 'Trigger:' from descriptions (now in dedicated field)

Co-Authored-By: SIAE DevForge"
```
