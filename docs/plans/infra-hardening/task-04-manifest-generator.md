# Task 04: Manifest Generato (D4)

**Deliverable:** D4
**Dipendenze:** Task 01 (DEVFORGE_STATE_DIR per test)
**File coinvolti:** nuovo `scripts/generate-manifest.js`, `plugin.json`, `.claude-plugin/marketplace.json`, `README.md`

---

## Step 1 — Test: verifica drift attuale

```bash
ls skills/ | wc -l                          # skill count reale
grep -o '[0-9]* skill' plugin.json          # count dichiarato in plugin.json
grep -o '[0-9]* skill' .claude-plugin/marketplace.json 2>/dev/null  # count marketplace
grep -oE '[0-9]+ skill' README.md           # count README
```

Output atteso: numeri diversi (conferma drift).

## Step 2 — Crea `scripts/generate-manifest.js`

```javascript
#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');

// Count skills (directories in skills/ with SKILL.md)
const skillsDir = path.join(ROOT, 'skills');
const skillCount = fs.readdirSync(skillsDir, { withFileTypes: true })
  .filter(d => d.isDirectory() && fs.existsSync(path.join(skillsDir, d.name, 'SKILL.md')))
  .length;

// Count hooks (from hooks.json)
const hooksJson = JSON.parse(fs.readFileSync(path.join(ROOT, 'hooks', 'hooks.json'), 'utf8'));
const hookCount = hooksJson.hooks ? hooksJson.hooks.length : 0;

// Count commands (directories in commands/)
const cmdsDir = path.join(ROOT, 'commands');
let cmdCount = 0;
if (fs.existsSync(cmdsDir)) {
  cmdCount = fs.readdirSync(cmdsDir, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .length;
}

// Count agents (directories in agents/)
const agentsDir = path.join(ROOT, 'agents');
let agentCount = 0;
if (fs.existsSync(agentsDir)) {
  agentCount = fs.readdirSync(agentsDir, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .length;
}

const summary = `${skillCount} skill, ${hookCount} hook, ${cmdCount} comandi, ${agentCount} agent`;
console.log(`Counts: ${summary}`);

// Update plugin.json description
const pluginPath = path.join(ROOT, '.claude-plugin', 'plugin.json');
if (fs.existsSync(pluginPath)) {
  const plugin = JSON.parse(fs.readFileSync(pluginPath, 'utf8'));
  // Replace count pattern in description
  plugin.description = plugin.description.replace(
    /\d+ skill,?\s*\d+ hook,?\s*\d+ comand[io],?\s*\d+ agent/i,
    summary
  );
  fs.writeFileSync(pluginPath, JSON.stringify(plugin, null, 2) + '\n');
  console.log('Updated: plugin.json');
}

// Update marketplace.json description
const marketplacePath = path.join(ROOT, '.claude-plugin', 'marketplace.json');
// Nota: entrambi i file sono in .claude-plugin/
if (fs.existsSync(marketplacePath)) {
  const mp = JSON.parse(fs.readFileSync(marketplacePath, 'utf8'));
  mp.description = mp.description.replace(
    /\d+ skill,?\s*\d+ hook,?\s*\d+ comand[io],?\s*\d+ agent/i,
    summary
  );
  fs.writeFileSync(marketplacePath, JSON.stringify(mp, null, 2) + '\n');
  console.log('Updated: marketplace.json');
}

// Update README.md count line
const readmePath = path.join(ROOT, 'README.md');
if (fs.existsSync(readmePath)) {
  let readme = fs.readFileSync(readmePath, 'utf8');
  readme = readme.replace(
    /\d+ skill,?\s*\d+ hook,?\s*\d+ comand[io],?\s*\d+ agent/i,
    summary
  );
  fs.writeFileSync(readmePath, readme);
  console.log('Updated: README.md');
}
```

## Step 3 — Run e verifica allineamento

```bash
node scripts/generate-manifest.js
git diff plugin.json .claude-plugin/marketplace.json README.md
```
Output atteso: diff mostra i numeri allineati al count reale.

```bash
# Seconda esecuzione: idempotente
node scripts/generate-manifest.js && git diff plugin.json .claude-plugin/marketplace.json README.md
```
Output atteso: nessun diff (idempotente).

## Step 4 — Commit

```bash
git add scripts/generate-manifest.js .claude-plugin/plugin.json .claude-plugin/marketplace.json README.md
git commit -m "feat(manifest): add generate-manifest.js to sync skill/hook/cmd counts

- Auto-counts skills, hooks, commands, agents from filesystem
- Updates plugin.json, marketplace.json, README.md descriptions
- Idempotent: running twice produces no diff
- Fixes metadata drift (was: README 30, plugin 35, marketplace 34, actual 37)

Co-Authored-By: SIAE DevForge"
```
