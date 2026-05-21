---
name: siae-test-data
description: >
  Genera dataset di profili anagrafici autoconsistenti per il sistema SIAE.
  Usa questa skill quando l'utente vuole generare dati di test per profili
  SIAE, dati anagrafici fittizi ma validi per testing, mock di codici fiscali
  italiani, partite IVA, indirizzi coerenti, profili utilizzatori/autori/editori.
  Attivare anche per: "genera profili di test", "dati anagrafici fittizi",
  "mock CF italiano", "dati SIAE per test", "crea anagrafica di prova",
  "fixture SIAE", "test data utilizzatore", "dataset autori editori",
  "genera CF e P.IVA validi", "mock anagrafica italiana", "test profilo SIAE".
runtime: Claude-native (zero dipendenze locali). Python opzionale per batch >50.
---

# siae-test-data — Generatore profili anagrafici SIAE

Genera dataset autoconsistenti di profili anagrafici per testing del sistema SIAE
(Società Italiana degli Autori ed Editori). **La skill e' Claude-native**: l'algoritmo
di calcolo CF/P.IVA e' eseguito direttamente da Claude leggendo i file di riferimento;
non e' necessario alcun runtime locale (Python, Node, ecc.).

## Quando attivare questa skill

- "Genera N profili SIAE per test"
- "Dammi un CF italiano valido per Mario Rossi nato a Roma il 01/01/1985"
- "Mock di una S.R.L. con CF=P.IVA e rappresentante legale"
- "Profili autori esteri residenti in Italia"
- "Dataset misto con edge case di indirizzo (SNC, bis/ter, km+, bilingue)"
- "Fixture JSON di utilizzatori business per i test di integrazione"

## Come Claude esegue la skill (procedura obbligatoria)

Quando questa skill viene attivata, Claude DEVE seguire questi passi nell'ordine:

### Passo 0 — Verifica scorciatoia Python (opzionale)

Se l'utente ha richiesto un dataset di **piu' di 50 profili** O ha esplicitamente
chiesto "in batch / batch automatico", prova prima questa scorciatoia:

```bash
python3 --version 2>/dev/null && echo OK
```

Se Python 3.8+ e' disponibile, salta al **Passo 6 (Esecuzione Python)**.
Altrimenti continua con la generazione Claude-native (passi 1-5).

### Passo 1 — Flusso interattivo a 6 step

Chiedi all'utente questi 6 step. Usa lo strumento di domande quando possibile;
se l'utente ha gia' specificato tutto nel messaggio iniziale, salta al passo 2.

```
[Step 1] Tipo soggetti      -> PRIVATO / BUSINESS / AUTORE / EDITORE / COMBO (multipla)
[Step 2] Residenza/sede     -> IT / UE / EXTRA_UE / MIX
[Step 3] Forme giuridiche   -> (solo se BUSINESS o EDITORE) DI/ENTEP/ENTE/IST/ONP/COOP/SDC/SDP
[Step 4] Edge case indir.   -> S / N
[Step 5] Quantita per tipo  -> intero >= 1
[Step 6] Formato output     -> JSON / CSV / Markdown / Tutti
```

### Passo 2 — Carica i reference

Leggi questi file (in `siae-test-data/references/`):
- `algoritmi.md` — algoritmi CF + P.IVA + validazioni
- `output_schema.md` — schema JSON canonico del profilo
- `belfiore_comuni.json` — codici Belfiore comuni italiani
- `belfiore_esteri.json` — codici Belfiore stati esteri
- `cap_citta.json` — lookup CAP / citta / provincia
- `forme_giuridiche.json` — vincoli CF/P.IVA per forma giuridica
- `nomi_italiani.json` + `nomi_esteri.json` — pool nomi/cognomi

### Passo 3 — Genera ogni profilo applicando l'algoritmo

Per ciascun profilo richiesto:

1. **Costruisci il `profilo_id`** secondo la convenzione (`P-IT-001`, `B-SDC-IT-001`, ...).
2. **Scegli i dati anagrafici** dal pool nomi della cittadinanza, una data di
   nascita tra 1950-2005, comune di nascita coerente con la cittadinanza.
3. **Calcola il CF** seguendo `algoritmi.md` sezione 1 (passi 1-7):
   - codice cognome (3 char)
   - codice nome (3 char, regola consonanti >=4)
   - anno (2 cifre) + mese (lettera A-T) + giorno (con +40 se F)
   - codice Belfiore (lookup)
   - checksum: somma `DISPARI`+`PARI` mod 26 -> A-Z
4. **Se persona giuridica**, calcola P.IVA seguendo `algoritmi.md` sezione 2 e
   applica i vincoli di `forme_giuridiche.json` (CF=P.IVA per SDC/SDP/COOP, ecc.).
5. **Genera l'indirizzo** scegliendo da `cap_citta.json`. Se edge case attivo
   (S al Step 4), applica un pattern dalla sezione 7 di `algoritmi.md` con
   probabilita' ~50%.
6. **Genera il telefono** in formato E.164 (`+39 3XX YYYYYYY` per IT,
   prefisso paese da `belfiore_esteri.json` per altri).
7. **Calcola `data_nascita_serial`** (giorni dal 1899-12-30, vedi sezione 3
   di `algoritmi.md`).

### Passo 4 — Auto-validazione obbligatoria

Prima di restituire il dataset, esegui mentalmente questi check su OGNI profilo
(vedi `algoritmi.md` per i dettagli):

- ✅ CF persona fisica: ricalcola il checksum e verifica che coincida
- ✅ P.IVA: ricalcola il checksum Luhn-AdE
- ✅ Vincolo CF=P.IVA per SDC/SDP/COOP (sede italiana)
- ✅ Sede estera: VAT Number presente, P.IVA italiana assente
- ✅ CAP appartenente al `cap_pool` della citta in `cap_citta.json`
- ✅ Provincia coerente con citta (`cap_citta.json`)
- ✅ Codice Belfiore nel CF coerente con stato/comune di nascita
- ✅ Telefono formato `+<prefisso> <cifre>`
- ✅ Data nascita: `data_nascita_serial` corrisponde alla data ISO

**Se un check fallisce**: rigenera il campo (cambia il seed mentale) invece di
restituire dati invalidi. Non emettere mai un profilo non validato.

### Passo 5 — Restituisci nel formato richiesto

- **JSON**: array di oggetti come definito in `output_schema.md`
- **CSV**: una riga per profilo (intestazioni: profilo_id, macro_categoria, ...)
- **Markdown**: tabella `| ID | Categoria | Tipo | Nome / Ragione Sociale | CF | P.IVA | Indirizzo | Edge |`
- **Tutti**: produci tutte e tre le rappresentazioni in sezioni separate

Restituisci il risultato inline nella conversazione, OPPURE scrivilo in un file
se l'utente specifica un path di output.

### Passo 6 — Scorciatoia Python (solo se Passo 0 ha rilevato Python 3.8+)

```bash
cd siae-test-data/scripts
python3 generate_profiles.py \
  --categorie <CSV> \
  --residenza <IT|UE|EXTRA_UE|MIX> \
  --forme-giuridiche <CSV> \
  [--edge-case] \
  --quantita <N> \
  --formato <JSON|CSV|MARKDOWN|ALL> \
  --strict \
  --output <path>
```

Lo script Python e' uno strumento ausiliario opzionale, **NON** un requisito.
La fonte di verita' sono i file in `references/`; Python e' solo una scorciatoia.

## Tassonomia coperta

### Macro-categorie
| Categoria | Descrizione |
|---|---|
| `PRIVATO` | Persona fisica utilizzatore |
| `BUSINESS` | Ente o societa licenziataria |
| `AUTORE` | Persona fisica titolare di diritti d'autore |
| `EDITORE` | Soggetto (persona o societa) che pubblica opere |
| `COMBO` | Autore + Editore sulla stessa anagrafica |

### Tipologie persona fisica
| Tipo | Residenza | CF |
|---|---|---|
| `P-IT` | Italiano in IT | 16 char calcolato |
| `P-EU-RES` | Straniero UE residente IT | 16 char con Z-xxx |
| `P-EU-NORES` | Straniero UE non residente | CF opzionale |
| `P-EXT-RES` | Straniero extra-UE residente IT | 16 char con Z-xxx |
| `P-EXT-NORES` | Straniero extra-UE non residente | CF opzionale |

### Tipologie persona giuridica
| Codice | Forma | CF | P.IVA | Vincolo |
|---|---|---|---|---|
| `DI` | Ditta Individuale | 16 char (titolare) | 11 cifre | CF ≠ P.IVA |
| `ENTEP` | Ente Privato | 11 cifre num. | 11 cifre obb. | indipendenti |
| `ENTE` | Ente Pubblico | 10 cifre num. | opzionale | indipendenti |
| `IST` | Istituzione | 10 cifre num. | opzionale | indipendenti |
| `ONP` | Non Profit | 10 cifre num. | opzionale | indipendenti |
| `COOP` | Cooperativa | 11 cifre | 11 cifre obb. | **CF = P.IVA** |
| `SDC` | Societa Capitali | 11 cifre | 11 cifre obb. | **CF = P.IVA** |
| `SDP` | Societa Persone | 11 cifre | 11 cifre obb. | **CF = P.IVA** |

### Edge case indirizzo coperti (14 pattern)
SNC, alfanumerico con barra (10/A), bis, ter, km progressivo +, km con virgola,
range doppio (110-112), bilingue IT/DE, interno, scala+piano, zona industriale +
lotto, frazione, autostrada+km, contrada+SNC.
Dettagli completi in `algoritmi.md` sezione 7.

## Determinismo

Lo stesso `profilo_id` deve produrre lo stesso output. Quando Claude genera
mentalmente, ancori la generazione al profilo_id (es. uso `profilo_id` come
seed mentale per scelte di pool).

## File della skill

```
siae-test-data/
├── SKILL.md
├── references/                 (Single source of truth — Claude-native)
│   ├── algoritmi.md            ← algoritmi CF/P.IVA + validazioni
│   ├── output_schema.md        ← schema JSON canonico
│   ├── belfiore_comuni.json
│   ├── belfiore_esteri.json
│   ├── cap_citta.json
│   ├── forme_giuridiche.json
│   ├── nomi_italiani.json
│   └── nomi_esteri.json
└── scripts/                    (Scorciatoia Python — opzionale, batch >50)
    ├── generate_profiles.py
    ├── cf_calculator.py
    ├── piva_calculator.py
    ├── address_generator.py
    └── validators.py
```

## Test di accettazione coperti

| Test | Input | Verifica |
|---|---|---|
| T01 | 1 PRIVATO italiano | CF valido, CAP coerente, serial corretto |
| T02 | 1 PRIVATO straniero residente IT | CF con Z-xxx, indirizzo italiano |
| T03 | 1 BUSINESS SDC italiana | CF=P.IVA 11 cifre, rapp. legale con CF proprio |
| T04 | 1 BUSINESS ENTE pubblico | CF 10 cifre, P.IVA opzionale |
| T05 | 1 BUSINESS DI estera | VAT Number, nessuna P.IVA italiana |
| T06 | 3 AUTORI italiani | 3 CF diversi tutti validi |
| T07 | Edge SNC | Civico="SNC" |
| T08 | Edge km progressivo | Civico="km 12+500" |
| T09 | BUSINESS con Gruppo IVA | flag + numero gruppo |
| T10 | COMBO (autore+editore) | Stesso soggetto, 2 ruoli |

Verificati: 10/10 PASS (sia via Python script che via esecuzione manuale Claude
sul caso di riferimento Mario Rossi -> `RSSMRA85A01H501Z`).
