/**
 * Test: la disambiguazione del catalogo skill deve rendere
 * brainstorming SEMPRE obbligatorio (zero eccezioni).
 *
 * RED: questo test fallisce perché le stringhe attuali dicono
 * "(NON brainstorming)" e "SOLO quando".
 */
const path = require('path');
const { buildCatalog } = require('../lib/skills-core');

const pluginDir = path.resolve(__dirname, '..');
const catalog = buildCatalog(pluginDir);
const table = catalog.table;

let failures = 0;

// 1. La disambiguazione NON deve contenere "(NON brainstorming)"
const nonBrainstormingMatches = (table.match(/\(NON brainstorming\)/g) || []);
if (nonBrainstormingMatches.length > 0) {
  console.error(`FAIL: Found ${nonBrainstormingMatches.length} occurrences of "(NON brainstorming)" — brainstorming deve essere sempre invocato`);
  failures++;
} else {
  console.log('PASS: Nessuna occorrenza di "(NON brainstorming)"');
}

// 2. La disambiguazione NON deve contenere "SOLO quando"
if (table.includes('SOLO quando')) {
  console.error('FAIL: Found "SOLO quando" — brainstorming non ha eccezioni');
  failures++;
} else {
  console.log('PASS: Nessuna occorrenza di "SOLO quando"');
}

// 3. La disambiguazione DEVE contenere "SEMPRE" per brainstorming
if (table.includes('brainstorming` SEMPRE')) {
  console.log('PASS: brainstorming marcato come SEMPRE');
} else {
  console.error('FAIL: brainstorming non marcato come SEMPRE');
  failures++;
}

// 4. Le skill specializzate devono indicare "+ brainstorming"
const plusBrainstorming = (table.match(/\+ `siae-brainstorming`/g) || []);
if (plusBrainstorming.length >= 4) {
  console.log(`PASS: ${plusBrainstorming.length} skill specializzate indicano "+ siae-brainstorming"`);
} else {
  console.error(`FAIL: Solo ${plusBrainstorming.length} skill indicano "+ siae-brainstorming" (attese >= 4)`);
  failures++;
}

if (failures > 0) {
  console.error(`\n${failures} test FALLITI`);
  process.exit(1);
} else {
  console.log('\nTutti i test passano');
  process.exit(0);
}
