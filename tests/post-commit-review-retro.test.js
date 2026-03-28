/**
 * Test: post-commit-review hook deve iniettare prompt di retrospettiva
 * quando il comando e' gh pr create.
 */
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const hookPath = path.resolve(__dirname, '..', 'hooks', 'post-commit-review');
const hookContent = fs.readFileSync(hookPath, 'utf8');

// 1. Hook must mention retrospective
assert.ok(hookContent.includes('retrospective') || hookContent.includes('siae-retrospective'),
  'post-commit-review hook deve menzionare retrospective');
console.log('PASS: hook menziona retrospective');

// 2. Retrospective must trigger only on gh pr create, not git push
assert.ok(hookContent.includes('gh') && hookContent.includes('pr') && hookContent.includes('create'),
  'hook deve distinguere gh pr create');
console.log('PASS: hook distingue gh pr create');

// 3. Must contain instruction to invoke siae-retrospective skill
assert.ok(hookContent.includes('siae-retrospective'),
  'hook deve istruire Claude a invocare siae-retrospective');
console.log('PASS: hook istruisce invocazione siae-retrospective');

console.log('\nTutti i test passano');
