/**
 * Test: la disambiguazione del catalogo skill e del hook reinject
 * deve rendere brainstorming SEMPRE obbligatorio per task implementativi.
 */
const assert = require('assert');
const path = require('path');
const fs = require('fs');
const { buildCatalog } = require('../lib/skills-core');

const pluginDir = path.resolve(__dirname, '..');
const catalog = buildCatalog(pluginDir);
const table = catalog.table;

// --- skills-core.js catalog disambiguation ---

// 1. No "(NON brainstorming)" in disambiguation
const nonBrainstormingMatches = (table.match(/\(NON brainstorming\)/g) || []);
assert.strictEqual(nonBrainstormingMatches.length, 0,
  `Found ${nonBrainstormingMatches.length} occurrences of "(NON brainstorming)" — brainstorming deve essere sempre invocato`);
console.log('PASS: Nessuna occorrenza di "(NON brainstorming)" nel catalogo');

// 2. No "SOLO quando" in disambiguation
assert.ok(!table.includes('SOLO quando'),
  'Found "SOLO quando" — brainstorming non ha eccezioni');
console.log('PASS: Nessuna occorrenza di "SOLO quando" nel catalogo');

// 3. Must contain "SEMPRE" for brainstorming
assert.ok(table.includes('SEMPRE'),
  'brainstorming non marcato come SEMPRE nel catalogo');
console.log('PASS: brainstorming marcato come SEMPRE nel catalogo');

// 4. Specialized skills must indicate "+ brainstorming"
const plusBrainstorming = (table.match(/\+ `siae-brainstorming`/g) || []);
assert.ok(plusBrainstorming.length >= 4,
  `Solo ${plusBrainstorming.length} skill indicano "+ siae-brainstorming" (attese >= 4)`);
console.log(`PASS: ${plusBrainstorming.length} skill specializzate indicano "+ siae-brainstorming"`);

// --- hooks/devforge-reinject coherence ---

const reinjectPath = path.join(pluginDir, 'hooks', 'devforge-reinject');
const reinjectContent = fs.readFileSync(reinjectPath, 'utf8');

// 5. Reinject must contain "brainstorming SEMPRE"
assert.ok(reinjectContent.includes('brainstorming SEMPRE'),
  'hooks/devforge-reinject non contiene "brainstorming SEMPRE"');
console.log('PASS: hooks/devforge-reinject contiene "brainstorming SEMPRE"');

// 6. Reinject must NOT contain "SOLO per feature nuove"
assert.ok(!reinjectContent.includes('SOLO per feature nuove'),
  'hooks/devforge-reinject contiene ancora "SOLO per feature nuove"');
console.log('PASS: hooks/devforge-reinject non contiene "SOLO per feature nuove"');

// 7. Reinject must mention git ops exception (coherence with skills-core.js)
assert.ok(reinjectContent.includes('escluse pure operazioni git'),
  'hooks/devforge-reinject non menziona eccezione per operazioni git pure');
console.log('PASS: hooks/devforge-reinject coerente con skills-core.js su eccezione git');

console.log('\nTutti i test passano');
