/**
 * Test: using-devforge deve restare una meta-skill backbone corta, non tornare
 * a essere un manuale lungo con catalogo statico e mappe duplicate.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const filePath = path.resolve(__dirname, '..', 'skills', 'using-devforge', 'SKILL.md');
const content = fs.readFileSync(filePath, 'utf8');
const lines = content.split('\n');

assert.ok(lines.length <= 160, `using-devforge troppo lunga: ${lines.length} righe`);
console.log(`PASS: using-devforge resta compatta (${lines.length} righe)`);

assert.ok(content.includes('## DevForge Backbone Core'),
  'Manca la sezione DevForge Backbone Core');
assert.ok(content.includes('## Always-On Companion Skills'),
  'Manca la sezione Always-On Companion Skills');
assert.ok(content.includes('## Skill Priority') || content.includes('## Priority & Rules'),
  'Manca la sezione Skill Priority / Priority & Rules');
assert.ok(content.includes('## Gate Operativi'),
  'Manca la sezione Gate Operativi');
console.log('PASS: sezioni backbone core presenti');

assert.ok(content.includes('**OBBLIGO CATALOGO:**'),
  'Manca l’obbligo di scansione del catalogo dinamico');
assert.ok(content.includes("anche l'1% di probabilita'"),
  'Manca la regola dell’1%');
console.log('PASS: 1% rule e obbligo catalogo presenti');

assert.ok(content.includes('skill di dominio + `siae-security` + `siae-tdd`'),
  'Security non e\' marcata come companion always-on');
assert.ok(content.includes('workflow review'),
  'Code review non e\' marcata come companion always-on');
console.log('PASS: security e code review marcate come companion always-on');

assert.ok(!content.includes('## Skill Dependency Map'),
  'using-devforge contiene ancora Skill Dependency Map');
assert.ok(!content.includes('## Catena SDLC'),
  'using-devforge contiene ancora Catena SDLC');
assert.ok(!content.includes('| Skill | INVOCA SE l\'utente menziona | Tipo | Fase SDLC |'),
  'using-devforge contiene ancora un catalogo statico duplicato');
console.log('PASS: contenuti lunghi e duplicati rimossi');

console.log('\nTutti i test passano');
