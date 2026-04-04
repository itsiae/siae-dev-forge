# Task 05: YAML Parser js-yaml (D5)

**Deliverable:** D5
**Dipendenze:** Task 04 (package.json pattern)
**File coinvolti:** nuovo `package.json` (root), `lib/skills-core.js`

---

## Step 1 — Test: verifica che il parser regex fallisce su edge case

```bash
# Crea un frontmatter di test con : nei valori
cat > /tmp/test-skill.md << 'EOF'
---
name: test-skill
description: "Skill con due punti: questo rompe il parser"
---
# Test
EOF
node -e "
const {extractFrontmatter} = require('./lib/skills-core');
const r = extractFrontmatter('/tmp/test-skill.md');
console.log('description:', r?.description);
console.log('expected: Skill con due punti: questo rompe il parser');
"
```
Output atteso: description troncata o errata (conferma bug).

## Step 2 — Crea `package.json` minimale a root

```json
{
  "name": "siae-dev-forge",
  "version": "1.36.0-mvp",
  "private": true,
  "description": "DevForge CLI plugin — internal tooling",
  "dependencies": {
    "js-yaml": "^4.1.0"
  }
}
```

```bash
npm install
```

Verifica che `.gitignore` contenga `node_modules/`. Se no, aggiungilo.

## Step 3 — Sostituisci extractFrontmatter in skills-core.js

In `lib/skills-core.js`, sostituisci la funzione `extractFrontmatter` (righe 27-78):

```javascript
const yaml = require('js-yaml');

function extractFrontmatter(filePath) {
  let content;
  try {
    content = fs.readFileSync(filePath, 'utf8');
  } catch {
    return null;
  }

  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return null;

  try {
    const parsed = yaml.load(match[1]);
    if (!parsed || typeof parsed !== 'object') return null;
    return parsed;
  } catch {
    return null;
  }
}
```

Rimuovi la funzione `readPhaseFromFrontmatter` (righe 158-168) — dopo questa modifica, `extractFrontmatter` gia' estrae `sdlc_phase` come campo nativo.

## Step 4 — Aggiorna gli import in skills-core.js

Assicurati che `require('js-yaml')` sia in cima al file, dopo `const path = require('path');`.

## Step 5 — Test: verifica che il parser funziona sugli edge case

```bash
node -e "
const {extractFrontmatter} = require('./lib/skills-core');
const r = extractFrontmatter('/tmp/test-skill.md');
console.log('description:', r?.description);
console.assert(r.description === 'Skill con due punti: questo rompe il parser', 'FAIL');
console.log('PASS: two-colon description parsed correctly');
"
```
Output atteso: PASS.

```bash
# Verifica che tutte le skill esistenti vengono parsate
node -e "
const {findSkillsInDir} = require('./lib/skills-core');
const skills = findSkillsInDir('./skills');
console.log('Parsed:', skills.length, 'skills');
console.assert(skills.length >= 36, 'Expected at least 36 skills');
console.log('PASS');
"
```

## Step 6 — Run test suite

```bash
tests/run-all.sh --fast
```
Output atteso: tutti i test passano.

## Step 7 — Commit

```bash
git add package.json package-lock.json .gitignore lib/skills-core.js
git commit -m "refactor(skills-core): replace regex frontmatter parser with js-yaml

- Add js-yaml dependency via package.json
- extractFrontmatter now uses yaml.load() — handles colons, quotes, arrays
- Remove readPhaseFromFrontmatter (now extracted natively)

Co-Authored-By: SIAE DevForge"
```
