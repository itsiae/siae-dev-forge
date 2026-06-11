# Task 01 — Scaffold: entry point, loadRef, parseArgs, Mulberry32

**Stato:** [PENDING]

**Goal:** Creare `skills/siae-test-data/scripts/generate_profiles.js` con le
fondamenta: cache JSON (`loadRef`), parser CLI (`parseArgs`), PRNG seedato
(`mulberry32`), entry point `main()` stub.

**File coinvolti:**
- `skills/siae-test-data/scripts/generate_profiles.js` — CREA

---

## Step 1 — Test RED

File: `skills/siae-test-data/tests/test_node_fallback.py` (crea se non esiste)

```python
"""Test integrazione Node.js fallback — siae-test-data."""
import subprocess, sys, os, json, time, pytest

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scripts')
SCRIPTS_DIR = os.path.abspath(SCRIPTS_DIR)

def _node(*args, timeout=10):
    return subprocess.run(
        ['node', 'generate_profiles.js', *args],
        cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=timeout
    )

@pytest.fixture(scope='session', autouse=True)
def require_node():
    r = subprocess.run(['node', '--version'], capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip('node non disponibile')

class TestScaffold:
    def test_file_esiste_e_richiede_senza_errori(self):
        r = subprocess.run(
            ['node', '-e',
             "const m=require('./generate_profiles.js'); "
             "console.log(typeof m.loadRef + ',' + typeof m.parseArgs)"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'function,function'

    def test_loadref_carica_nomi_italiani(self):
        r = subprocess.run(
            ['node', '-e',
             "const {loadRef}=require('./generate_profiles.js');"
             "const d=loadRef('nomi_italiani.json');"
             "console.log(Array.isArray(d.nomi_maschili))"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'true'
```

Run: `cd skills/siae-test-data && python -m pytest tests/test_node_fallback.py::TestScaffold -v`
Output atteso: `FAILED` (file non esiste)

---

## Step 2 — Verifica RED

```
FAILED tests/test_node_fallback.py::TestScaffold::test_file_esiste_e_richiede_senza_errori
```

---

## Step 3 — Implementazione GREEN

Crea `skills/siae-test-data/scripts/generate_profiles.js`:

```js
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

// ── Entry point (stub — completato in task-07) ───────────────────────────────
function main() {}

if (require.main === module) main();
module.exports = { loadRef, parseArgs, makePRNG };
```

---

## Step 4 — Verifica GREEN

Run: `cd skills/siae-test-data && python -m pytest tests/test_node_fallback.py::TestScaffold -v`
Output atteso:
```
PASSED tests/test_node_fallback.py::TestScaffold::test_file_esiste_e_richiede_senza_errori
PASSED tests/test_node_fallback.py::TestScaffold::test_loadref_carica_nomi_italiani
```

---

## Step 5 — Commit

```
test(siae-test-data): RED scaffold Node.js fallback
feat(siae-test-data): scaffold generate_profiles.js — loadRef, parseArgs, mulberry32
```

## Criteri di accettazione

- [ ] `require('./generate_profiles.js')` eseguito senza errori
- [ ] `loadRef('nomi_italiani.json').nomi_maschili` è un Array
- [ ] `makePRNG('seed').choice(['a','b','c'])` ritorna sempre lo stesso valore per lo stesso seed
- [ ] 2 test TestScaffold PASS
