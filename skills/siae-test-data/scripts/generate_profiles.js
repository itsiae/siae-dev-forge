'use strict';
const path = require('path');
const fs   = require('fs');

// ── Cache JSON reference ─────────────────────────────────────────────────────
const _refCache = {};
function loadRef(name) {
  const safe = path.basename(name);
  if (safe !== name || !safe.endsWith('.json'))
    throw new Error(`Riferimento non valido: ${name}`);
  if (!_refCache[safe]) {
    _refCache[safe] = JSON.parse(
      fs.readFileSync(path.join(__dirname, '..', 'references', safe), 'utf8')
    );
  }
  return _refCache[safe];
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
    choice:  arr => arr[Math.floor(next() * arr.length)],
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
  const parts = dataISO.split('-').map(Number);
  if (parts.length !== 3 || parts.some(isNaN))
    throw new Error(`Data non valida: ${dataISO}`);
  const [y,m,d] = parts;
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

// ── Task 03 — pivaUtils ───────────────────────────────────────────────────────
let _CODICI_PROV = null;
function _getCodiceProv(sigla) {
  if (!_CODICI_PROV) {
    const raw = loadRef('forme_giuridiche.json')['_codici_provincia_istat'];
    _CODICI_PROV = {};
    for (const [k, v] of Object.entries(raw))
      if (!k.startsWith('_')) _CODICI_PROV[k] = v;
  }
  return _CODICI_PROV[sigla] || '001';
}

function checksumPiva(piva10) {
  let s = 0;
  for (let i = 0; i < 10; i++) {
    let d = parseInt(piva10[i], 10);
    if ((i + 1) % 2 === 0) { d *= 2; if (d > 9) d -= 9; }
    s += d;
  }
  return String((10 - s % 10) % 10);
}

function validaPiva(piva) {
  if (!piva || typeof piva !== 'string') return false;
  piva = piva.trim();
  if (!/^\d{11}$/.test(piva)) return false;
  return checksumPiva(piva.slice(0, 10)) === piva[10];
}

function generaPiva(siglaProv, progressivo) {
  const codProv = _getCodiceProv(siglaProv);
  const prog    = (progressivo !== undefined && progressivo !== null) ? progressivo : 1234567;
  const piva10  = String(prog).padStart(7, '0') + codProv;
  return piva10 + checksumPiva(piva10);
}

function calcolaCFEnte11(progressivo, siglaProv) { return generaPiva(siglaProv, progressivo); }

function calcolaCFEnte10(seedStr) {
  const rng = makePRNG(seedStr);
  return Array.from({length: 10}, () => rng.randint(0, 10)).join('');
}

// ── Task 04 — addressUtils + _pickNomeCognome ────────────────────────────────
let _BELFIORE_COMUNI = null, _BELFIORE_ESTERI = null, _CAP_CITTA = null;
let _NOMI_IT = null, _NOMI_ESTERI = null;
let _COMUNI_KEYS = null, _CAP_IT_KEYS = null, _STATI_UE = null, _STATI_EXTRA_UE = null;

function _initRefs() {
  if (_BELFIORE_COMUNI) return;
  const bc = loadRef('belfiore_comuni.json');
  _BELFIORE_COMUNI = {};
  for (const [k, v] of Object.entries(bc))
    if (!k.startsWith('_')) _BELFIORE_COMUNI[k] = v;

  const be = loadRef('belfiore_esteri.json');
  _BELFIORE_ESTERI = {};
  for (const [k, v] of Object.entries(be))
    if (!k.startsWith('_')) _BELFIORE_ESTERI[k] = v;

  _CAP_CITTA   = loadRef('cap_citta.json');
  _NOMI_IT     = loadRef('nomi_italiani.json');
  _NOMI_ESTERI = loadRef('nomi_esteri.json');

  _COMUNI_KEYS    = Object.keys(_BELFIORE_COMUNI);
  _CAP_IT_KEYS    = Object.keys(_CAP_CITTA['Italia']);
  _STATI_UE       = Object.entries(_BELFIORE_ESTERI).filter(([,v]) => v.area === 'UE').map(([k]) => k);
  _STATI_EXTRA_UE = Object.entries(_BELFIORE_ESTERI).filter(([,v]) => v.area === 'EXTRA-UE').map(([k]) => k);
}

const TOPONIMI = ['VIA','PIAZZA','CORSO','VIALE','VICOLO','LARGO','PIAZZALE'];
const NOMI_VIE = [
  'Roma','Garibaldi','Mazzini','Cavour','Dante','Manzoni','Verdi',
  'Vittorio Emanuele II','XX Settembre','della Repubblica','della Liberta',
  'Marconi','Galileo Galilei','San Giovanni','delle Vigne','Aurelia','Tiburtina',
];

const _TOP_ESTERO = {
  'Germania':    ['STRASSE',  ['Hauptstrasse','Bahnhofstrasse','Berliner','Koenigsallee']],
  'Francia':     ['RUE',      ['de Rivoli','de la Paix','Saint-Honore','Lafayette']],
  'Spagna':      ['CALLE',    ['Mayor','Gran Via','Alcala','Serrano']],
  'Regno Unito': ['STREET',   ['Oxford','Baker','Regent','Bond']],
  'Giappone':    ['',         ['Shibuya','Ginza','Roppongi','Asakusa']],
  'Stati Uniti': ['STREET',   ['Main','Broadway','5th Avenue','Wall']],
  'Svizzera':    ['STRASSE',  ['Bahnhofstrasse','Limmatquai','Paradeplatz']],
  'Romania':     ['STRADA',   ['Victoriei','Lipscani','Magheru']],
  'Polonia':     ['ULICA',    ['Nowy Swiat','Marszalkowska','Florjanska']],
  'Olanda':      ['STRAAT',   ['Damrak','Kalverstraat','Leidsestraat']],
  'Belgio':      ['RUE',      ['Royale','de la Loi','Neuve']],
  'Austria':     ['STRASSE',  ['Mariahilfer','Kaerntner','Ringstrasse']],
};

function _pickNomeCognome(stato, genere, rng) {
  _initRefs();
  let nomiM, nomiF, cognomi;
  if (stato === 'Italia') {
    nomiM   = _NOMI_IT.nomi_maschili;
    nomiF   = _NOMI_IT.nomi_femminili;
    cognomi = _NOMI_IT.cognomi;
  } else {
    const pool = _NOMI_ESTERI[stato] || _NOMI_ESTERI['Germania'];
    nomiM   = pool.nomi_maschili;
    nomiF   = pool.nomi_femminili;
    cognomi = pool.cognomi;
  }
  return [rng.choice(genere.toUpperCase() === 'F' ? nomiF : nomiM), rng.choice(cognomi)];
}

function _statoRandom(area, rng) {
  _initRefs();
  return rng.choice(area === 'UE' ? _STATI_UE : _STATI_EXTRA_UE);
}

function generaIndirizzoIT(citta, rng) {
  _initRefs();
  const itInfo     = _CAP_CITTA['Italia'];
  const actualCity = itInfo[citta] ? citta : 'Roma';
  const info       = itInfo[actualCity];
  return {
    toponimo:  rng.choice(TOPONIMI),
    via:       rng.choice(NOMI_VIE),
    civico:    String(rng.randint(1, 251)),
    cap:       rng.choice(info.cap_pool),
    citta:     actualCity,
    provincia: info.provincia,
    stato:     'Italia',
    tipo:      'RES',
    edge_case: null,
  };
}

function generaIndirizzoEstero(stato, rng) {
  _initRefs();
  const extInfo     = _CAP_CITTA['Estero'];
  const actualStato = extInfo[stato] ? stato : 'Germania';
  const info        = extInfo[actualStato];
  const maxIdx      = Math.min(info.citta_pool.length, info.cap_pool.length);
  const idx         = maxIdx > 1 ? rng.randint(0, maxIdx) : 0;
  const [top, vie]  = _TOP_ESTERO[actualStato] || ['STREET', ['Main']];
  return {
    toponimo:  top,
    via:       rng.choice(vie),
    civico:    String(rng.randint(1, 251)),
    cap:       info.cap_pool[idx],
    citta:     info.citta_pool[idx],
    provincia: '—',
    stato:     actualStato,
    tipo:      'RES',
    edge_case: null,
  };
}

// ── Task 05 — profileGen PRIVATO ─────────────────────────────────────────────
function validaCF(cf) {
  if (!cf || cf.length !== 16) return false;
  cf = cf.toUpperCase();
  if (!/^[A-Z0-9]{15}[A-Z]$/.test(cf)) return false;
  return checksumCF(cf.slice(0, 15)) === cf[15];
}

function dateToExcelSerial(isoDate) {
  const [y, m, d] = isoDate.split('-').map(Number);
  const dt    = Date.UTC(y, m - 1, d);
  const epoch = Date.UTC(1899, 11, 30);
  return Math.round((dt - epoch) / 86400000);
}

function _randomDate(rng, minYear, maxYear) {
  const y  = rng.randint(minYear || 1950, (maxYear || 2005) + 1);
  const mo = rng.randint(1, 13);
  const dd = rng.randint(1, 29);
  return `${y}-${String(mo).padStart(2,'0')}-${String(dd).padStart(2,'0')}`;
}

function _randomPhone(rng, stato) {
  _initRefs();
  if (stato === 'Italia')
    return `+39 3${rng.randint(20, 99)}${rng.randint(1000000, 9999999)}`;
  const pref = (_BELFIORE_ESTERI[stato] || {}).prefisso_telefonico || '+49';
  return `${pref} ${Array.from({length: 9}, () => rng.randint(0, 10)).join('')}`;
}

function generaProfiloPrivato(pid, area, mode, rng) {
  _initRefs();
  if (area === 'ITA') area = 'IT';

  const genere = rng.choice(['M', 'F']);
  let stato, belfiore, provinciaNascita, comuneNascita;
  if (area === 'IT') {
    stato            = 'Italia';
    const comune     = rng.choice(_COMUNI_KEYS);
    const ic         = _BELFIORE_COMUNI[comune];
    belfiore         = ic.codice_belfiore;
    provinciaNascita = ic.provincia;
    comuneNascita    = comune;
  } else {
    stato            = _statoRandom(area, rng);
    belfiore         = _BELFIORE_ESTERI[stato].codice_belfiore;
    provinciaNascita = '—';
    comuneNascita    = null;
  }

  const [nome, cognome] = _pickNomeCognome(stato, genere, rng);
  const dataNasc        = _randomDate(rng);
  const cf              = calcolaCF(nome, cognome, dataNasc, genere, belfiore);

  const anagrafica = {
    nome, cognome,
    codice_fiscale:      cf,
    data_nascita:        dataNasc,
    data_nascita_serial: dateToExcelSerial(dataNasc),
    genere,
    cittadinanza:        stato === 'Italia' ? 'Italiana' : stato,
    stato_nascita:       stato,
    provincia_nascita:   provinciaNascita,
    comune_nascita:      comuneNascita,
  };

  const profilo = {
    profilo_id:      pid,
    macro_categoria: 'PRIVATO',
    tipo_persona:    'FISICA',
    tipo_profilo:    area === 'IT' ? 'P-IT' : (area === 'UE' ? 'P-EU' : 'P-EXT'),
    anagrafica,
  };

  if (mode !== 'LIGHT') {
    profilo.contatti  = { telefono: _randomPhone(rng, stato) };
    profilo.indirizzo = area === 'IT'
      ? generaIndirizzoIT(rng.choice(_CAP_IT_KEYS), rng)
      : generaIndirizzoEstero(stato, rng);
  }

  return profilo;
}

// ── Task 06 — profileGen BUSINESS ────────────────────────────────────────────
function generaRappLegale(pid, area) {
  _initRefs();
  const rng    = makePRNG(pid + '-RL');
  const genere = rng.choice(['M', 'F']);
  let stato, belfiore;
  if (!area || area === 'IT' || area === 'ITA') {
    stato    = 'Italia';
    belfiore = _BELFIORE_COMUNI[rng.choice(_COMUNI_KEYS)].codice_belfiore;
  } else {
    stato    = _statoRandom(area, rng);
    belfiore = _BELFIORE_ESTERI[stato].codice_belfiore;
  }
  const [nome, cognome] = _pickNomeCognome(stato, genere, rng);
  const dataNasc        = _randomDate(rng, 1950, 1990);
  const cf              = calcolaCF(nome, cognome, dataNasc, genere, belfiore);
  return { cf, nome, cognome, data_nascita: dataNasc, genere };
}

function generaProfiloBusiness(pid, area, fg, mode, rng) {
  _initRefs();
  if (area === 'ITA') area = 'IT';
  const fgAll  = loadRef('forme_giuridiche.json');
  const fgData = fgAll[fg] || fgAll['SDC'];

  let siglaProv, sedeLegale;
  if (area === 'IT') {
    const citta = rng.choice(_CAP_IT_KEYS);
    siglaProv   = _CAP_CITTA['Italia'][citta].provincia;
    sedeLegale  = Object.assign(generaIndirizzoIT(citta, rng), {tipo: 'SEDE_LEGALE'});
  } else {
    const statoBiz = _statoRandom(area, rng);
    sedeLegale     = Object.assign(generaIndirizzoEstero(statoBiz, rng), {tipo: 'SEDE_LEGALE'});
    siglaProv      = 'RM';
  }

  let pidHash = 0;
  for (let i = 0; i < pid.length; i++)
    pidHash = (Math.imul(31, pidHash) + pid.charCodeAt(i)) | 0;
  const progressivo = 1000000 + ((pidHash >>> 0) % 8000000);

  let cfEnte, piva;
  if (['SDC','SDP','COOP'].includes(fg)) {
    if (area === 'IT') { cfEnte = generaPiva(siglaProv, progressivo); piva = cfEnte; }
    else               { cfEnte = '—'; piva = null; }
  } else if (fg === 'ENTEP') {
    cfEnte = calcolaCFEnte11(progressivo, siglaProv);
    piva   = area === 'IT' ? generaPiva(siglaProv, progressivo + 1) : null;
  } else if (['ENTE','IST','ONP'].includes(fg)) {
    cfEnte = calcolaCFEnte10(pid + '-cf10');
    piva   = null;
  } else {
    cfEnte = generaRappLegale(pid, area).cf;
    piva   = area === 'IT' ? generaPiva(siglaProv, progressivo) : null;
  }

  const rl      = generaRappLegale(pid, area);
  const ragione = rng.choice(fgData.esempi_ragione_sociale || ['Azienda']) + ' ' + pid.slice(-4);
  const natGiur = rng.choice(fgData.nature_giuridiche || ['S.R.L.']);

  const soggGiur = {
    ragione_sociale:        ragione,
    forma_giuridica_codice: fg,
    natura_giuridica:       natGiur,
    codice_fiscale_ente:    cfEnte,
    partita_iva:            piva,
    rappresentante_legale:  rl,
  };

  const profilo = {
    profilo_id:         pid,
    macro_categoria:    'BUSINESS',
    tipo_persona:       'GIURIDICA',
    tipo_profilo:       `G-${fg}`,
    soggetto_giuridico: soggGiur,
  };

  if (mode !== 'LIGHT') profilo.indirizzo = sedeLegale;
  return profilo;
}

// ── Task 07 — formatOutput + main ────────────────────────────────────────────
function calcolaDistribuzione(quantita, distribuzioni) {
  if (!distribuzioni || distribuzioni.length === 0)
    throw new Error('distribuzioni non puo essere vuota');
  const tot = distribuzioni.reduce((a, b) => a + b, 0);
  if (!isFinite(tot) || tot <= 0)
    throw new Error(`distribuzione non valida: somma=${tot}`);
  const counts = distribuzioni.map(p => Math.floor(quantita * p / tot));
  counts[counts.length - 1] += quantita - counts.reduce((a, b) => a + b, 0);
  return counts;
}

function formatOutput(profili, formato) {
  if ((formato || 'JSON').toUpperCase() === 'CSV') {
    const cols = [
      'profilo_id','macro_categoria','tipo_persona','tipo_profilo',
      'nome','cognome','codice_fiscale','data_nascita','genere','cittadinanza',
      'stato_nascita','comune_nascita','telefono',
      'ragione_sociale','forma_giuridica','cf_ente','partita_iva',
      'indirizzo_toponimo','indirizzo_via','indirizzo_civico',
      'indirizzo_cap','indirizzo_citta','indirizzo_stato',
    ];
    const rows = [cols.join(',')];
    for (const p of profili) {
      const a   = p.anagrafica || {};
      const sg  = p.soggetto_giuridico || {};
      const ind = p.indirizzo || {};
      const con = p.contatti || {};
      const cell = v => { const s = String(v == null ? '' : v); return s.includes(',') ? `"${s}"` : s; };
      rows.push([
        p.profilo_id, p.macro_categoria, p.tipo_persona, p.tipo_profilo || '',
        a.nome || '', a.cognome || '', a.codice_fiscale || '',
        a.data_nascita || '', a.genere || '', a.cittadinanza || '',
        a.stato_nascita || '', a.comune_nascita || '', con.telefono || '',
        sg.ragione_sociale || '', sg.forma_giuridica_codice || '',
        sg.codice_fiscale_ente || '', sg.partita_iva || '',
        ind.toponimo || '', ind.via || '', ind.civico || '',
        ind.cap || '', ind.citta || '', ind.stato || '',
      ].map(cell).join(','));
    }
    return rows.join('\n');
  }
  return JSON.stringify(profili, null, 2);
}

function main() {
  const args      = parseArgs(process.argv);
  const categorie = (args.categorie || 'PRIVATO').toUpperCase().split(',');
  const nazRaw    = (args.nazionalita || 'ITA').toUpperCase().split(',');
  const distRaw   = args.distribuzione ? args.distribuzione.split(',').map(Number) : null;
  const quantita  = parseInt(args.quantita || '10', 10);
  const formato   = (args.formato || 'JSON').toUpperCase();
  const fgList    = args['forme-giuridiche'] ? args['forme-giuridiche'].toUpperCase().split(',') : ['SDC'];
  const mode      = (args.profilo || 'FULL').toUpperCase();
  const outFile   = args.output;

  const AREA_MAP = { 'ITA': 'IT', 'UE': 'UE', 'EXTRA-UE': 'EXTRA-UE', 'IT': 'IT' };
  const dist     = calcolaDistribuzione(quantita, distRaw || nazRaw.map(() => 1));

  const profili = [];
  for (let ni = 0; ni < nazRaw.length; ni++) {
    const area  = AREA_MAP[nazRaw[ni]] || 'IT';
    const count = dist[ni];
    for (const cat of categorie) {
      if (cat === 'BUSINESS') {
        for (const fg of fgList) {
          for (let i = 1; i <= count; i++) {
            const pid = `B-${fg}-${nazRaw[ni]}-${String(i).padStart(3,'0')}`;
            profili.push(generaProfiloBusiness(pid, area, fg, mode, makePRNG(pid)));
          }
        }
      } else {
        const pre = cat === 'AUTORE' ? 'A' : cat === 'EDITORE' ? 'E' : 'P';
        for (let i = 1; i <= count; i++) {
          const pid = `${pre}-${nazRaw[ni]}-${String(i).padStart(3,'0')}`;
          profili.push(generaProfiloPrivato(pid, area, mode, makePRNG(pid)));
        }
      }
    }
  }

  const out = formatOutput(profili, formato);
  if (outFile) fs.writeFileSync(outFile, out, 'utf8');
  else process.stdout.write(out + '\n');
}

if (require.main === module) main();
module.exports = {
  loadRef, parseArgs, makePRNG,
  normalizza, codiceCognome, codiceNome, checksumCF, calcolaCF,
  checksumPiva, validaPiva, generaPiva, calcolaCFEnte11, calcolaCFEnte10,
  _pickNomeCognome, _statoRandom, generaIndirizzoIT, generaIndirizzoEstero,
  validaCF, dateToExcelSerial, generaProfiloPrivato,
  generaRappLegale, generaProfiloBusiness,
  calcolaDistribuzione, formatOutput,
};
