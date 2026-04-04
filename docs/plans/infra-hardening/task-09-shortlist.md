# Task 09: Shortlist Contestuale in Reinject (D9)

**Deliverable:** D9
**Dipendenze:** Task 07 (frontmatter strutturato con triggers), Task 08 (CLI shortlist branch)
**File coinvolti:** `lib/skills-core.js`, `hooks/devforge-reinject`

---

## Step 1 — Implementa `matchSkills` in skills-core.js

Aggiungi la funzione prima di `buildCatalog`:

```javascript
/**
 * Match skills against a user query based on trigger keywords.
 * Returns top-N skills sorted by number of matching triggers.
 * Falls back to empty array if no triggers match.
 */
function matchSkills(query, skills, topN = 7) {
  if (!query || !query.trim()) return [];
  const q = query.toLowerCase();
  const scored = skills.map(s => {
    const triggers = s.triggers || [];
    const hits = triggers.filter(t => q.includes(t.toLowerCase()));
    return { ...s, score: hits.length };
  });
  return scored
    .filter(s => s.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, topN);
}
```

## Step 2 — Aggiungi export e attiva CLI shortlist

Aggiungi `matchSkills` agli exports:

```javascript
module.exports = {
  extractFrontmatter,
  findSkillsInDir,
  resolveSkillPath,
  stripFrontmatter,
  buildCatalog,
  matchSkills,
};
```

Il branch CLI `shortlist` in Task 08 e' gia' preparato. Verifica che funzioni:

```bash
node lib/skills-core.js . shortlist "ho un bug, il test fallisce"
```
Output atteso: JSON con skill tipo `siae-debugging`, `siae-tdd`, `siae-brainstorming`.

## Step 3 — Aggiorna `hooks/devforge-reinject` per usare shortlist

In `hooks/devforge-reinject`, sezione "Build compact DevForge context" (dopo riga 38):

```bash
# ── Read user message from stdin ──
USER_MSG=""
if [ ! -t 0 ]; then
    USER_MSG=$(cat | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('message', ''))
except:
    print('')
" 2>/dev/null || echo "")
fi

# ── Skill shortlist (contextual) ──
if [ -n "$USER_MSG" ] && command -v node >/dev/null 2>&1; then
    shortlist=$(node "${PLUGIN_ROOT}/lib/skills-core.js" "${PLUGIN_ROOT}" shortlist "$USER_MSG" 2>/dev/null || echo "")
    if [ -n "$shortlist" ] && [ "$shortlist" != "[]" ]; then
        # Build compact table from shortlist JSON
        skill_catalog=$(echo "$shortlist" | node -e "
let d='';process.stdin.on('data',c=>d+=c);process.stdin.on('end',()=>{
  const skills=JSON.parse(d);
  const lines=['| Skill | Trigger | Tipo |','|-------|---------|------|'];
  skills.forEach(s=>lines.push('| '+s.name+' | '+(s.triggers||[]).slice(0,3).join(', ')+' | '+s.type+' |'));
  console.log(lines.join('\n'));
});
" 2>/dev/null || echo "")
    fi
fi

# Fallback: full catalog if shortlist empty or failed
if [ -z "${skill_catalog:-}" ]; then
    skill_catalog=$(node "${PLUGIN_ROOT}/lib/skills-core.js" "${PLUGIN_ROOT}" 2>/dev/null || echo "")
fi
```

## Step 4 — Verifica shortlist

```bash
# Test matching con query specifica
node -e "
const {buildCatalog, matchSkills} = require('./lib/skills-core');
const c = buildCatalog('.');
const r = matchSkills('ho un bug nel frontend', c.skills);
console.log('Matched:', r.map(s=>s.name));
console.assert(r.length > 0, 'Expected at least 1 match');
console.assert(r.length <= 7, 'Expected max 7 matches');
console.log('PASS');
"
```

```bash
# Test fallback con query vuota
node -e "
const {buildCatalog, matchSkills} = require('./lib/skills-core');
const c = buildCatalog('.');
const r = matchSkills('', c.skills);
console.assert(r.length === 0, 'Empty query should return empty');
console.log('PASS: empty query returns empty (triggers fallback in hook)');
"
```

## Step 5 — Run test suite

```bash
tests/run-all.sh
```

## Step 6 — Commit

```bash
git add lib/skills-core.js hooks/devforge-reinject
git commit -m "feat(reinject): contextual skill shortlist based on user query

- Add matchSkills(query, skills, topN=7) to skills-core.js
- devforge-reinject uses shortlist of top-7 skills matching user message
- Falls back to full catalog if no matches or shortlist fails
- CLI: node lib/skills-core.js <root> shortlist 'query'

Co-Authored-By: SIAE DevForge"
```
