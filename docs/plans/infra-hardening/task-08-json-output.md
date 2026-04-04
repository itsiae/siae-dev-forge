# Task 08: Output JSON skills-core (D8)

**Deliverable:** D8
**Dipendenze:** Task 01 (DEVFORGE_STATE_DIR per test)
**File coinvolti:** `lib/skills-core.js`, `tests/run-all.sh`

---

## Step 1 — Test: verifica che il CLI non supporta --format json

```bash
node lib/skills-core.js . json 2>&1 | head -5
```
Output atteso: output Markdown (non JSON), perche' il flag non esiste.

## Step 2 — Aggiungi flag format al CLI entry point

In `lib/skills-core.js`, sostituisci il blocco `if (require.main === module)` (righe 352-356):

```javascript
if (require.main === module) {
  const pluginDir = process.argv[2] || path.resolve(__dirname, '..');
  const format = process.argv[3] || 'markdown';
  const catalog = buildCatalog(pluginDir);

  if (format === 'json') {
    const out = catalog.skills.map(s => ({
      name: s.name,
      triggers: s.triggers || [],
      type: s.type,
      phase: s.phase,
    }));
    process.stdout.write(JSON.stringify(out, null, 2) + '\n');
  } else if (format === 'shortlist') {
    // D9 will use this — placeholder for now
    const query = process.argv[4] || '';
    const matched = matchSkills(query, catalog.skills);
    process.stdout.write(JSON.stringify(matched, null, 2) + '\n');
  } else {
    process.stdout.write(catalog.table + '\n');
  }
}
```

Nota: il branch `shortlist` prepara il terreno per D9. `matchSkills` verra' implementata in Task 09.

## Step 3 — Aggiungi export per matchSkills (placeholder)

In fondo al modulo, aggiungi `matchSkills` alla lista exports (sara' implementata in Task 09):

```javascript
module.exports = {
  extractFrontmatter,
  findSkillsInDir,
  resolveSkillPath,
  stripFrontmatter,
  buildCatalog,
  // matchSkills,  // D9
};
```

## Step 4 — Aggiorna test catalogo in run-all.sh

In `tests/run-all.sh`, sezione "Dynamic Catalog Validation" (riga ~143):

```bash
# PRIMA (BUG — conta disambiguazione):
catalog_output=$(node "${PLUGIN_ROOT}/lib/skills-core.js" "${PLUGIN_ROOT}" 2>&1)
catalog_lines=$(echo "$catalog_output" | wc -l | tr -d ' ')
catalog_skills=$((catalog_lines - 2))

# DOPO (FIX — JSON output, conta solo skill):
catalog_json=$(node "${PLUGIN_ROOT}/lib/skills-core.js" "${PLUGIN_ROOT}" json 2>&1)
catalog_skills=$(echo "$catalog_json" | node -e "
  let d=''; process.stdin.on('data',c=>d+=c);
  process.stdin.on('end',()=>{ try{console.log(JSON.parse(d).length)}catch{console.log(0)} });
")
```

## Step 5 — Verifica

```bash
# JSON output contiene solo skill, no disambiguazione
node lib/skills-core.js . json | node -e "
  let d=''; process.stdin.on('data',c=>d+=c);
  process.stdin.on('end',()=>{
    const arr = JSON.parse(d);
    console.log('Skills:', arr.length);
    console.assert(arr.length >= 36, 'Expected >= 36');
    console.assert(arr[0].name, 'Expected name field');
    console.log('PASS');
  });
"
```

```bash
# Markdown output invariato (backward compatible)
node lib/skills-core.js . markdown | head -3
```
Output atteso: header tabella Markdown.

```bash
# Test suite
tests/run-all.sh --fast
```

## Step 6 — Commit

```bash
git add lib/skills-core.js tests/run-all.sh
git commit -m "feat(skills-core): add --format json output for machine consumption

- CLI: node lib/skills-core.js <root> json → JSON array of skills
- CLI: node lib/skills-core.js <root> markdown → Markdown table (default, unchanged)
- Fix test catalog count: uses JSON length instead of wc -l (was counting disambiguation lines)

Co-Authored-By: SIAE DevForge"
```
