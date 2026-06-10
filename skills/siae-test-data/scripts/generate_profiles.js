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

// ── Tabelle CF ───────────────────────────────────────────────────────────────
const MESI_CF = ['A','B','C','D','E','H','L','M','P','R','S','T'];
const DISP = {
  '0':1,'1':0,'2':5,'3':7,'4':9,'5':13,'6':15,'7':17,'8':19,'9':21,
  'A':1,'B':0,'C':5,'D':7,'E':9,'F':13,'G':15,'H':17,'I':19,'J':21,
  'K':2,'L':4,'M':18,'N':20,'O':11,'P':3,'Q':6,'R':8,'S':12,'T':14,
  'U':16,'V':10,'W':22,'X':25,'Y':24,'Z':23,
};
const PARI = {
  '0':0,'1':1,'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,
  'A':0,'B':1,'C':2,'D':3,'E':4,'F':5,'G':6,'H':7,'I':8,'J':9,
  'K':10,'L':11,'M':12,'N':13,'O':14,'P':15,'Q':16,'R':17,'S':18,'T':19,
  'U':20,'V':21,'W':22,'X':23,'Y':24,'Z':25,
};
const TO_CHAR = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
const VOWELS  = new Set('AEIOU');

function normalizza(s) {
  return s.toUpperCase().trim()
    .replace(/[ÀÁÂÄÃ]/g,'A').replace(/[ÈÉÊË]/g,'E')
    .replace(/[ÌÍÎÏ]/g,'I').replace(/[ÒÓÔÖÕ]/g,'O')
    .replace(/[ÙÚÛÜ]/g,'U').replace(/Ç/g,'C')
    .replace(/Ñ/g,'N').replace(/ß/g,'S')
    .replace(/[^A-Z]/g,'');
}
function _cons(s) { return [...s].filter(c => !VOWELS.has(c)).join(''); }
function _voc(s)  { return [...s].filter(c =>  VOWELS.has(c)).join(''); }

function codiceCognome(cog) {
  const s = normalizza(cog);
  return (_cons(s) + _voc(s) + 'XXX').slice(0,3);
}
function codiceNome(nom) {
  const s = normalizza(nom);
  const c = _cons(s);
  if (c.length >= 4) return c[0]+c[2]+c[3];
  return (_cons(s) + _voc(s) + 'XXX').slice(0,3);
}
function codiceData(dataISO, genere) {
  const [y,m,d] = dataISO.split('-').map(Number);
  const aa  = String(y % 100).padStart(2,'0');
  const mes = MESI_CF[m - 1];
  const gg  = String(d + (genere.toUpperCase() === 'F' ? 40 : 0)).padStart(2,'0');
  return aa + mes + gg;
}
function checksumCF(cf15) {
  let tot = 0;
  for (let i = 0; i < 15; i++)
    tot += (i % 2 === 0 ? DISP : PARI)[cf15[i]];
  return TO_CHAR[tot % 26];
}
function calcolaCF(nome, cognome, dataISO, genere, belfiore) {
  const p = codiceCognome(cognome) + codiceNome(nome) +
            codiceData(dataISO, genere) + belfiore.toUpperCase();
  return p + checksumCF(p);
}

// ── Entry point (completato in task-07) ─────────────────────────────────────
function main() {}

if (require.main === module) main();
module.exports = { loadRef, parseArgs, makePRNG,
  normalizza, codiceCognome, codiceNome, checksumCF, calcolaCF };
