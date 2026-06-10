'use strict';
const path = require('path');
const fs   = require('fs');

// ── Cache JSON reference ─────────────────────────────────────────────────────
const _refCache = {};
function loadRef(name) {
  if (!_refCache[name]) {
    _refCache[name] = JSON.parse(
      fs.readFileSync(path.join(__dirname, '..', 'references', name), 'utf8')
    );
  }
  return _refCache[name];
}

// ── CLI parser ───────────────────────────────────────────────────────────────
function parseArgs(argv) {
  const a = {};
  for (let i = 2; i < argv.length; i++) {
    if (!argv[i].startsWith('--')) continue;
    const key = argv[i].slice(2);
    const nxt = argv[i + 1];
    if (nxt && !nxt.startsWith('--')) { a[key] = nxt; i++; }
    else a[key] = true;
  }
  return a;
}

// ── PRNG Mulberry32 seedato (determinismo per-runtime) ───────────────────────
function makePRNG(strSeed) {
  let h = 0;
  for (let i = 0; i < strSeed.length; i++)
    h = (Math.imul(31, h) + strSeed.charCodeAt(i)) | 0;
  let s = h >>> 0;
  function next() {
    s = (s + 0x6D2B79F5) >>> 0;
    let z = s;
    z = Math.imul(z ^ (z >>> 15), z | 1);
    z ^= z + Math.imul(z ^ (z >>> 7), z | 61);
    return ((z ^ (z >>> 14)) >>> 0) / 4294967296;
  }
  return {
    next,
    choice: arr => arr[Math.floor(next() * arr.length)],
    randint: (lo, hi) => lo + Math.floor(next() * (hi - lo)),
  };
}

// ── Entry point (completato in task-07) ─────────────────────────────────────
function main() {}

if (require.main === module) main();
module.exports = { loadRef, parseArgs, makePRNG };
