/**
 * Test: i trigger del catalogo non devono rompersi su estensioni/file pattern
 * e il catalogo deve rendere esplicito il flow coupling tra skill core e
 * skill specialistiche.
 */
const assert = require('assert');
const path = require('path');
const { buildCatalog } = require('../lib/skills-core');

const pluginDir = path.resolve(__dirname, '..');
const catalog = buildCatalog(pluginDir);

function getTrigger(skillName) {
  const skill = catalog.skills.find(s => s.name === skillName);
  assert.ok(skill, `Skill non trovata: ${skillName}`);
  return skill.trigger;
}

const iacTrigger = getTrigger('siae-iac');
assert.ok(iacTrigger.includes('.tf'), `siae-iac trigger troncato: ${iacTrigger}`);
assert.ok(iacTrigger.includes('.hcl'), `siae-iac trigger troncato: ${iacTrigger}`);
console.log('PASS: siae-iac mantiene .tf/.hcl nel trigger');

const frontendTrigger = getTrigger('siae-frontend');
assert.ok(frontendTrigger.includes('Vue.js'), `siae-frontend trigger troncato: ${frontendTrigger}`);
console.log('PASS: siae-frontend mantiene Vue.js nel trigger');

const robotTrigger = getTrigger('siae-robot-framework');
assert.ok(robotTrigger.includes('.robot'), `siae-robot-framework trigger troncato: ${robotTrigger}`);
assert.ok(robotTrigger.includes('.resource'), `siae-robot-framework trigger troncato: ${robotTrigger}`);
assert.ok(!robotTrigger.startsWith(':'), `siae-robot-framework trigger malformato: ${robotTrigger}`);
console.log('PASS: siae-robot-framework mantiene .robot/.resource nel trigger');

const brainstormingTrigger = getTrigger('siae-brainstorming');
assert.ok(brainstormingTrigger.includes('QUALSIASI task implementativo'),
  `siae-brainstorming non marcata come workflow core: ${brainstormingTrigger}`);
console.log('PASS: siae-brainstorming marcata come workflow core');

const securityTrigger = getTrigger('siae-security');
assert.ok(securityTrigger.includes('SEMPRE') || securityTrigger.includes('companion'),
  `siae-security non marcata come always-on: ${securityTrigger}`);
console.log('PASS: siae-security marcata come always-on');

const blindReviewTrigger = getTrigger('siae-blind-review');
assert.ok(blindReviewTrigger.includes('SEMPRE') || blindReviewTrigger.includes('audit'),
  `siae-blind-review non marcata come workflow review: ${blindReviewTrigger}`);
console.log('PASS: siae-blind-review marcata come workflow review');

assert.ok(catalog.table.includes('**Core Workflow DevForge (obbligatorio):**'),
  'Manca la sezione Core Workflow DevForge');
console.log('PASS: sezione Core Workflow presente');

assert.ok(catalog.table.includes('**Legame Delle Skill Specialistiche Al Flusso:**'),
  'Manca la sezione di legame al flusso');
assert.ok(catalog.table.includes('skill specialistica + `siae-brainstorming`'),
  'Le skill specialistiche non sono agganciate al brainstorming');
assert.ok(catalog.table.includes('`siae-security` SEMPRE') || catalog.table.includes('+ `siae-security`'),
  'Le skill specialistiche non sono agganciate alla security');
assert.ok(catalog.table.includes('workflow review') || catalog.table.includes('`siae-blind-review` SEMPRE'),
  'Le skill specialistiche non sono agganciate alla code review');
assert.ok(catalog.table.includes('skill specialistica + `siae-verification`'),
  'Le skill specialistiche non sono agganciate alla verification');
console.log('PASS: le skill specialistiche sono agganciate al flusso core');

console.log('\nTutti i test passano');
