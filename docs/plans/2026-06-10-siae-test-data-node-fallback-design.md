# Design: siae-test-data Node.js Fallback

**Data:** 2026-06-10
**Branch:** fix/test-data-upgrade
**SP:** 6.5 Umano / 3.5 Augmented
**Complessità:** Media
**Tipo:** Feature (nuovo fallback runtime)

---

## Contesto

Su macchine Windows senza Python (es. PC collega SIAE), la skill siae-test-data cade
sul percorso Claude-native iterativo: 50 profili = ~10 minuti (1 LLM round-trip per
profilo). Il fix aggiunge Node.js come secondo fallback: disponibile sulla maggioranza
delle macchine developer Windows (npm/nvm), riduce il tempo a <2s per N=50.

Detection order Passo 0:
1. `python3/python/py` → `generate_profiles.py` (invariato)
2. `node/nodejs` → `generate_profiles.js` (nuovo)
3. Nessun runtime → Claude-native + warning latenza per N>10

---

## Decisioni architetturali (ADR)

| Decisione | Scelta | Alternativa scartata | Motivo |
|---|---|---|---|
| Struttura file | Single-file CJS | Multi-file JS | Fallback minimale, no npm install |
| PRNG | Mulberry32 inline (~8 righe) | crypto.randomInt | Seedato, zero deps, ~2× più veloce di Math.random |
| Module format | CommonJS (require) | ESM (import) | Node 10+, no package.json richiesto |
| Test runner | pytest integrazione | Jest | Riusa infrastruttura esistente, CI invariata |
| Determinismo | Per-runtime (a) | Cross-runtime identico (b) | Mulberry32 ≠ Mersenne Twister; non possibile cross-runtime senza hardcoding |
| Edge case indirizzo | Fuori scope v1 | Inclusi | 14 pattern edge = +1.5SP; aggiungibili in v2 |

---

## File prodotti

| File | Tipo | Descrizione |
|---|---|---|
| `scripts/generate_profiles.js` | Nuovo | Script Node.js CJS, ~650 righe, zero deps |
| `tests/test_node_fallback.py` | Nuovo | 7 test integrazione pytest |
| `SKILL.md` | Modifica | Passo 0: Python → Node → Claude-native + detection command |

---

## Struttura interna `generate_profiles.js`

```
parseArgs()         — process.argv parser minimale (no deps)
loadRef(name)       — fs.readFileSync + JSON.parse
                      path.join(__dirname, '../references/', name)
mulberry32(seed)    — PRNG seedato da stringa hash (djb2 + Mulberry32), ~12 righe
cfUtils
  normalizza(s)     — upper + accenti + regex [^A-Z]
  codiceCognome(s)  — consonanti + vocali + padding X
  codiceNome(s)     — regola 4 consonanti (1,3,4) o standard
  codiceData(d, g)  — anno+mese(ABCDEHLMPRST)+giorno(+40 se F)
  checksum(cf15)    — CHECKSUM_DISPARI/PARI table, somma mod 26 → A-Z
  calcolaCF(nome, cognome, data, genere, belfiore) → 16 char
  calcolaCFEnte11(progressivo, codProv) → 11 cifre numeriche
    [ Solo ENTEP: CF numerico 11 cifre con codice provincia ISTAT ]
  calcolaCFEnte10(progressivo) → 10 cifre numeriche
    [ ENTE, IST, ONP ]
pivaUtils
  checksumPiva(piva10)  — Luhn-AdE (pari×2, >9 →-9)
  generaPiva(sigla, progressivo) → 11 cifre
  [ Per SDC/SDP/COOP: CF = PIVA → usa generaPiva ]
addressUtils
  generaIndirizzoIT(citta, rng)   — lookup cap_citta.json
  generaIndirizzoEstero(stato, rng)
profileGen
  generaRappLegale(area, formGiur, rng) → {nome, cognome, cf, data_nascita, ...}
    [ ITA: belfiore_comuni.json; UE/EXTRA-UE: belfiore_esteri.json Z-xxx ]
  generaProfilo(opts) → oggetto schema-compatibile
formatOutput(profili, formato)    — JSON / CSV (FULL/LIGHT headers) / Markdown
main()                            — distribuzione nazionalità, loop, skip_validation
```

---

## Algoritmi CF enti (BLOCK-2)

| Forma | CF | P.IVA | Vincolo |
|---|---|---|---|
| SDC, SDP, COOP | generaPiva(sigla, rng) | = CF | CF = P.IVA obbligatorio |
| ENTEP | calcolaCFEnte11(prog, prov) | generaPiva() indipendente | CF 11 cifre num |
| ENTE, IST, ONP | calcolaCFEnte10(prog) | generaPiva() opzionale | CF 10 cifre num |
| DI | calcolaCF persona fisica del titolare | generaPiva() | CF 16 char ≠ P.IVA |

Tutti i CF ente usano un progressivo derivato da `rng.nextInt(1000000, 9999999)`.

---

## SKILL.md Passo 0 — detection commands

```bash
# Passo 0a — Python
(python3 --version 2>/dev/null || python --version 2>/dev/null || py --version 2>/dev/null) && echo PYTHON_OK
# Passo 0b — Node.js (solo se Python non trovato)
(node --version 2>/dev/null || nodejs --version 2>/dev/null) && echo NODE_OK
```

Pre-warming Node.js (emesso nello stesso turno del primo AskUserQuestion):
```bash
node -e "const p=require('path'),fs=require('fs');['nomi_italiani.json','nomi_esteri.json','forme_giuridiche.json','cap_citta.json','belfiore_comuni.json','belfiore_esteri.json'].forEach(f=>JSON.parse(fs.readFileSync(path.join(__dirname||'.',f))))" 2>/dev/null
```
> Nota: `__dirname` non è disponibile nei one-liner `-e`; il pre-warming Node.js usa
> il path relativo al CWD corrente (operatore deve fare `cd siae-test-data/references`
> oppure il comando è adattato al CWD). Questo è accettabile perché il vantaggio
> principale (Defender scan) si ottiene anche con un path assoluto esplicito.

---

## Test di accettazione (`test_node_fallback.py`)

| Test | Verifica |
|---|---|
| `test_node_available` | `node --version` exit 0 (pytest.skip se assente) |
| `test_node_1_privato_json` | 1 profilo JSON, CF 16 char, checksum valido |
| `test_node_cf_mario_rossi_diretto` | Chiama con `--nome Mario --cognome Rossi --data 1985-01-01 --genere M --belfiore H501` → CF=`RSSMRA85A01H501Z` (algoritmo, non PRNG) |
| `test_node_distribuzione_ita_ue` | N=10, 70/30 ITA+UE → 7 ITA + 3 UE nel JSON |
| `test_node_business_sdc_ita_rapp_legale` | 1 SDC italiana: CF=P.IVA, rapp. legale con CF 16 char |
| `test_node_business_sdc_extra_ue_rapp_legale` | 1 SDC con rapp. legale EXTRA-UE: CF usa Belfiore Z-xxx |
| `test_node_bench_50_profili` | N=50 PRIVATO ITA, elapsed < 2.0s |

---

## Criteri di accettazione

- [ ] `node generate_profiles.js --categorie PRIVATO --nazionalita ITA --quantita 1 --formato JSON` produce JSON valido
- [ ] CF Mario Rossi da input diretto = `RSSMRA85A01H501Z` (algoritmo invariato)
- [ ] N=50 profili su macOS in <2.0s (test benchmark)
- [ ] BUSINESS SDC: CF = P.IVA (vincolo rispettato in Node.js)
- [ ] BUSINESS SDC EXTRA-UE: rappresentante legale con CF contenente Belfiore Z-xxx
- [ ] Tutti i 7 `test_node_fallback` PASS (con Node disponibile; skip automatico se assente)
- [ ] SKILL.md Passo 0: Python ha priorità su Node; avviso latenza se né Python né Node

## Limitazioni v1 (fuori scope)

- Edge case indirizzo (14 pattern SNC/km/bilingue/ecc.) → indirizzo standard only
- Formato CSV: intestazioni FULL only (LIGHT CSV in v2)
- Formato Markdown: non implementato in v1 (fallback a JSON se richiesto)
