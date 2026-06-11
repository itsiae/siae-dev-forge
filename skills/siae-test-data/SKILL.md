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
runtime: Claude-native (zero dipendenze locali). Python opzionale per batch >5.
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

Se l'utente ha richiesto un dataset di **piu' di 5 profili** O ha esplicitamente
chiesto "in batch / batch automatico", prova prima questa scorciatoia:

```bash
(python3 --version 2>/dev/null || python --version 2>/dev/null || py --version 2>/dev/null) && echo OK
```

> **Windows:** `python3` potrebbe non essere nel PATH; il comando prova in sequenza
> `python3`, `python` e il Python Launcher `py` per garantire il rilevamento corretto.

Se Python 3.8+ e' disponibile:
- Avvia il pre-warming del data_store emettendo il comando sotto **nello stesso turno**
  in cui mostri il primo step del wizard (Passo 1, Step 1). Non aspettare il risultato
  prima della prima `AskUserQuestion`: il warm-up avviene mentre l'utente risponde,
  nascondendo ~480ms di Defender scan su Windows nel tempo di attesa dell'utente.
  ```bash
  cd siae-test-data/scripts && python3 -c "import data_store; [data_store.get(f) for f in ['nomi_italiani.json','nomi_esteri.json','forme_giuridiche.json','cap_citta.json','belfiore_comuni.json','belfiore_esteri.json']]; print('warmed')" 2>/dev/null
  ```
- Dopo aver raccolto tutti i parametri del wizard, salta al **Passo 6 (Esecuzione Python)**.

Altrimenti, se Python non e' disponibile, prova **Node.js**:

```bash
(node --version 2>/dev/null || nodejs --version 2>/dev/null) && node -e "if(parseInt(process.version.slice(1))<10)process.exit(1)" 2>/dev/null && echo NODE_OK
```

> **Windows:** su alcune installazioni il binario e' `nodejs`; il comando prova entrambi.

Se Node.js 10+ e' disponibile (`NODE_OK`):
- **Memorizza il runtime scelto**: scrivi mentalmente `→ RUNTIME: Node.js` — userai
  il **Passo 6-bis** (non il Passo 6) al termine del wizard.
- Avvia il pre-warming emettendo il comando sotto **nello stesso turno** della prima
  `AskUserQuestion` (non attendere il risultato):
  ```bash
  # Eseguire da REPO ROOT (dove risiede skills/)
  node -e "const p=require('path'),f=require('fs'),r=p.join(process.cwd(),'skills','siae-test-data','references');['nomi_italiani.json','nomi_esteri.json','forme_giuridiche.json','cap_citta.json','belfiore_comuni.json','belfiore_esteri.json'].forEach(n=>JSON.parse(f.readFileSync(p.join(r,n))))" 2>/dev/null
  ```
- Dopo aver raccolto tutti i parametri del wizard, salta al **Passo 6-bis (Esecuzione Node.js)**.

Altrimenti (ne' Python ne' Node.js disponibili — path Claude-native, passi 1-5):
- Se N > 10: avvisa l'utente — "Generazione Claude-native per N={N} profili senza runtime
  locale richiede ~{N×12}s. Installa Python 3.8+ o Node.js 10+ per ridurre a <2s."
- Emetti tutte le **Read del Passo 2** nello stesso turno della prima `AskUserQuestion`
  (Step 1 del wizard). I file saranno gia' in contesto quando l'utente risponde,
  eliminando i 3.2s di caricamento dal percorso critico su Windows VPN.
- Al Passo 2 salta le Read gia' emesse al Passo 0.

### Passo 1 — Flusso interattivo a 7 step

Usa `AskUserQuestion` per raccogliere le scelte seguenti. Se l'utente ha gia'
specificato tutto nel messaggio iniziale, salta direttamente al passo 2.
Presenta tutti gli step con opzioni predeterminate; accetta testo libero solo
dove indicato esplicitamente.

```
[Step 1] Tipo soggetti      -> multiselect: PRIVATO / BUSINESS / AUTORE / EDITORE / COMBO
[Step 2] Nazionalita'       -> multiselect: ITA / UE / EXTRA-UE
[Step 2b] % distribuzione   -> (condizionale: solo se >=2 nazionalita' selezionate)
                               preset + opzione libera — vedi tabella sotto
[Step 3] Forme giuridiche   -> (condizionale: solo se BUSINESS o EDITORE)
                               DI / ENTEP / ENTE / IST / ONP / COOP / SDC / SDP
[Step 4] Profilo dati       -> FULL (con indirizzo e telefono)
                               LIGHT (solo anagrafica: CF/P.IVA, nomi, date, residenza citta')
[Step 5] Edge case indir.   -> S / N  (solo se Step 4 = FULL)
[Step 6] Quantita'          -> fascia preset: 5 / 10 / 25 / 50 / 100 / 500
[Step 7] Formato output     -> JSON / CSV / Markdown / Tutti
```

#### Tabella preset % distribuzione (Step 2b)

**IMPORTANTE**: lo Step 2b e' **sempre obbligatorio** quando >=2 nazionalita' sono
selezionate, anche se l'utente ha gia' specificato altri parametri nel messaggio
iniziale. Non saltarlo: senza distribuzione esplicita il dataset potrebbe risultare
non rappresentativo.

Mostra le opzioni corrispondenti alla combinazione di nazionalita' selezionate.
Aggiungi sempre l'opzione **Personalizzata** come ultima voce per input libero.

| Combinazione selezionata | Preset proposti |
|---|---|
| ITA + UE | 70% ITA / 30% UE — 60% ITA / 40% UE — 50% ITA / 50% UE — Personalizzata |
| ITA + EXTRA-UE | 70% ITA / 30% EXTRA-UE — 60% ITA / 40% EXTRA-UE — 50% ITA / 50% EXTRA-UE — Personalizzata |
| UE + EXTRA-UE | 70% UE / 30% EXTRA-UE — 60% UE / 40% EXTRA-UE — 50% UE / 50% EXTRA-UE — Personalizzata |
| ITA + UE + EXTRA-UE | 70% ITA / 20% UE / 10% EXTRA-UE — 60% ITA / 30% UE / 10% EXTRA-UE — 50% ITA / 30% UE / 20% EXTRA-UE — Equa (~33%/33%/34%) — Personalizzata |

Se l'utente sceglie **Personalizzata**, chiedi le percentuali come testo libero.
Prima di processare, **normalizza il formato** accettando:
- `"33%, 33%, 34%"` → rimuovi `%` e spazi → `[33, 33, 34]`
- `"33,33,34"` → split su `,` → `[33, 33, 34]`
- `"un terzo ciascuno"` / `"equa"` → distribuzione equa automatica (vedi preset Equa)
- `"70 20 10"` → split su spazio → `[70, 20, 10]`

Dopo la normalizzazione, verifica che la somma sia 100. Se differisce per errore
di arrotondamento (±1%), aggiusta autonomamente l'ultima percentuale senza chiedere
conferma. Se la differenza supera il ±1%, segnala all'utente e chiedi di correggere.

### Passo 2 — Carica i reference

> **Skip se pre-caricati al Passo 0** (path Claude-native con Read emesse insieme
> al primo AskUserQuestion): i file sono gia' in contesto, non ri-leggere.

**Leggi tutti i file seguenti in un singolo batch parallelo** (emetti tutte le
Read tool call nello stesso turno di risposta — non sequenzialmente una alla volta):

Leggi questi file (in `siae-test-data/references/`):
- `algoritmi.md` — algoritmi CF + P.IVA + validazioni
- `output_schema.md` — schema JSON canonico del profilo
- `belfiore_comuni.json` — codici Belfiore comuni italiani
- `belfiore_esteri.json` — codici Belfiore stati esteri
- `cap_citta.json` — lookup CAP / citta / provincia
- `forme_giuridiche.json` — vincoli CF/P.IVA per forma giuridica
- `nomi_italiani.json` + `nomi_esteri.json` — pool nomi/cognomi

### Passo 3 — Genera ogni profilo applicando l'algoritmo

#### Pre-generazione — Calcola la distribuzione per nazionalita'

**Esegui PRIMA di iniziare il loop sui profili.** Se Step 2 ha >=2 nazionalita':

1. **Ordina i gruppi per percentuale DECRESCENTE** (il gruppo con % minore sarà l'ultimo).
   Invariante: il gruppo con % minore deve essere sempre l'ultimo perche' riceve il
   residuo; se fosse in posizione intermedia, il suo `floor(N × p/100)` potrebbe
   essere 0 su dataset piccoli (es. N=5, p=10% → floor=0), svuotando il gruppo.
2. Calcola i conteggi con l'algoritmo floor + residuo:
   - Per ogni gruppo NON-ultimo: `count_i = floor(N × p_i / 100)`
   - Per l'ultimo gruppo: `count_ultimo = N − sum(tutti gli altri count_i)`
3. Verifica: `sum(tutti i count_i) == N` (sempre vero per costruzione).

Esempio: N=5, gruppi [ITA 70%, UE 20%, EXTRA-UE 10%] già in ordine decrescente:
- `count_ITA = floor(5 × 70/100) = floor(3.5) = 3`
- `count_UE = floor(5 × 20/100) = floor(1.0) = 1`
- `count_EXTRA-UE = 5 − 3 − 1 = 1` (residuo)
- Risultato: 3 ITA + 1 UE + 1 EXTRA-UE = 5 ✓

Se una sola nazionalita' e' selezionata, tutti gli N profili appartengono a quel gruppo.

**Genera tutti i profili in un unico blocco di output**: calcola TUTTO il dataset
e restituiscilo in una sola risposta invece di emettere ogni profilo in round-trip
separati. Su Windows ogni round-trip al modello costa 300-800ms extra.

#### Loop — Per ciascun profilo (itera gruppo per gruppo: prima tutti N_ITA, poi N_UE, poi N_EXTRA-UE)

1. **Costruisci il `profilo_id`** secondo la convenzione (`P-IT-001`, `B-SDC-IT-001`, ...).
2. **Scegli i dati anagrafici** dal pool nomi della cittadinanza del gruppo corrente,
   una data di nascita tra 1950-2005, comune di nascita coerente con la cittadinanza.
3. **Calcola il CF** seguendo `algoritmi.md` sezione 1 (passi 1-7):
   - codice cognome (3 char)
   - codice nome (3 char, regola consonanti >=4)
   - anno (2 cifre) + mese (lettera A-T) + giorno (con +40 se F)
   - codice Belfiore (lookup)
   - checksum: somma `DISPARI`+`PARI` mod 26 -> A-Z
4. **Se persona giuridica**, calcola P.IVA seguendo `algoritmi.md` sezione 2 e
   applica i vincoli di `forme_giuridiche.json` (CF=P.IVA per SDC/SDP/COOP, ecc.).
   Genera il **rappresentante legale** con questi campi obbligatori:
   - `nome`, `cognome`, `genere` (M/F)
   - `data_nascita` in formato `AAAA-MM-GG` — deve essere **coerente con il CF**: anno da char 7-8, mese dalla tabella A-T (char 9), giorno da char 10-11 con la regola del genere: se genere=M il giorno e' il valore diretto; se genere=F il giorno e' `valore_char - 40` (es. cifre_giorno="47", intero 47 → giorno = 47 − 40 = 7, data giorno="07")
   - `comune_nascita` / `stato_nascita` — per soggetti italiani: comune italiano; per UE/EXTRA-UE: nome dello stato di nascita
   - `cf` — calcola il CF del rappresentante seguendo l'algoritmo sezione 1:
     * Rappresentanti nati in Italia: usa codice Belfiore del comune (`belfiore_comuni.json`)
     * Rappresentanti nati all'estero (UE o EXTRA-UE): usa codice Belfiore dello stato (`belfiore_esteri.json`, formato Z-xxx)
     * Il CF e' obbligatorio per TUTTI i rappresentanti legali, indipendentemente dalla nazionalita' dell'ente
5. **Genera l'indirizzo** (solo se profilo FULL): scegli da `cap_citta.json`.
   Se edge case attivo (S al Step 5), applica un pattern dalla sezione 7 di
   `algoritmi.md` con probabilita' ~50%.
   Se profilo LIGHT: ometti completamente i campi indirizzo (`via`, `civico`,
   `cap`, `citta`, `provincia`, `stato`, `tipo`, `edge_case`). Popola solo
   `nazione_residenza` e `nazione_residenza_code` (vedi schema LIGHT in `output_schema.md`).
6. **Genera il telefono** (solo se profilo FULL) in formato E.164
   (`+39 3XX YYYYYYY` per IT, prefisso paese da `belfiore_esteri.json` per altri).
   Se profilo LIGHT: ometti il nodo `contatti` a livello top-level (incluso `telefono`).
   Per profili BUSINESS/EDITORE in LIGHT: ometti anche `rappresentante_legale.contatti`
   (vedi sezione C di `output_schema.md`).
7. **Calcola `data_nascita_serial`** (giorni dal 1899-12-30, vedi sezione 3
   di `algoritmi.md`).

### Passo 4 — Auto-validazione obbligatoria

Prima di restituire il dataset, esegui mentalmente questi check su OGNI profilo
(vedi `algoritmi.md` per i dettagli):

- ✅ CF persona fisica: ricalcola il checksum e verifica che coincida
- ✅ P.IVA: ricalcola il checksum Luhn-AdE
- ✅ Vincolo CF=P.IVA per SDC/SDP/COOP (sede italiana)
- ✅ Sede estera: VAT Number presente, P.IVA italiana assente
- ✅ Codice Belfiore nel CF coerente con stato/comune di nascita
- ✅ Data nascita: `data_nascita_serial` corrisponde alla data ISO
- ✅ (solo FULL) CAP appartenente al `cap_pool` della citta in `cap_citta.json`
- ✅ (solo FULL) Provincia coerente con citta (`cap_citta.json`)
- ✅ (solo FULL) Telefono formato `+<prefisso> <cifre>`
- ✅ Distribuzione nazionalita': conteggio per ciascun gruppo corrisponde alle % richieste (±1 per arrotondamento)
- ✅ Rappresentante legale: CF calcolato e presente per TUTTI i profili (ITA, UE, EXTRA-UE)
- ✅ Rappresentante legale: `data_nascita` AAAA-MM-GG decodificata dal CF — anno (char 7-8) e mese (char 9, tabella A-T) devono coincidere; per il giorno (char 10-11): se genere=F sottrarre 40 prima del confronto (es. CF "62" → giorno 22), se genere=M il valore deve essere il giorno diretto
- ✅ Rappresentante legale: `stato_nascita` coerente con il codice Belfiore usato nel CF (Z-xxx per esteri, comune italiano per nati in IT)

**Se un check fallisce**: rigenera il campo (cambia il seed mentale) invece di
restituire dati invalidi. Non emettere mai un profilo non validato.

### Passo 5 — Restituisci nel formato richiesto

- **JSON**: array di oggetti come definito in `output_schema.md`. In modalita' LIGHT
  ometti `indirizzo` (oggetto completo) e il nodo `contatti` a livello top-level
  (incluso `telefono`). Per BUSINESS/EDITORE ometti anche `rappresentante_legale.contatti`.
- **CSV**: una riga per profilo. Intestazioni FULL: `profilo_id, macro_categoria, tipo, nome, cf, piva, via, civico, cap, citta, provincia, telefono, ...`
  Intestazioni LIGHT: le stesse ma senza `via`, `civico`, `cap`, `citta`, `provincia`, `telefono`.
- **Markdown**: tabella FULL: `| ID | Categoria | Tipo | Nome / Ragione Sociale | CF | P.IVA | Indirizzo | Edge |`
  Tabella LIGHT: `| ID | Categoria | Tipo | Nome / Ragione Sociale | CF | P.IVA | Nazionalita' |`
- **Tutti**: produci tutte e tre le rappresentazioni in sezioni separate.

Includi sempre un header informativo prima del dataset con il riepilogo dei parametri scelti:
```
# Dataset generato
# Tipo: <categorie> | Nazionalita': <nazionalita'> [<% distribuzione>]
# Profili: <N> | Modalita': FULL/LIGHT | Edge case: S/N
```

Restituisci il risultato inline nella conversazione, OPPURE scrivilo in un file
se l'utente specifica un path di output.

### Passo 6-bis — Scorciatoia Node.js (solo se Passo 0 ha rilevato NODE_OK)

```bash
cd siae-test-data/scripts
node generate_profiles.js \
  --categorie <CSV> \
  --nazionalita <ITA|UE|EXTRA-UE|ITA,UE|ITA,EXTRA-UE|UE,EXTRA-UE|ITA,UE,EXTRA-UE> \
  --distribuzione "<pct_ITA>,<pct_UE>,<pct_EXTRA-UE>" \
  --forme-giuridiche <CSV> \
  --profilo <FULL|LIGHT> \
  --quantita <5|10|25|50|100|500> \
  --formato <JSON|CSV> \
  --output <path>
```

Python ha priorita' se disponibile. Edge case indirizzo (14 pattern) e formato Markdown
non sono supportati nella versione Node.js — usare il path Claude-native se richiesti.

### Passo 6 — Scorciatoia Python (solo se Passo 0 ha rilevato Python 3.8+)

```bash
cd siae-test-data/scripts
python3 generate_profiles.py \
  --categorie <CSV> \
  --nazionalita <ITA|UE|EXTRA-UE|ITA,UE|ITA,EXTRA-UE|UE,EXTRA-UE|ITA,UE,EXTRA-UE> \
  --distribuzione "<pct_ITA>,<pct_UE>,<pct_EXTRA-UE>" \  # opzionale; default equa
  --forme-giuridiche <CSV> \
  --profilo <FULL|LIGHT> \
  [--edge-case] \                                         # ignorato se LIGHT
  --quantita <5|10|25|50|100|500> \
  --formato <JSON|CSV|MARKDOWN|ALL> \
  --strict \
  [--skip-validation] \                                    # performance: salta validazione post-generazione
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
| T01 | 1 PRIVATO italiano, FULL | CF valido, CAP coerente, serial corretto, telefono presente |
| T02 | 1 PRIVATO straniero UE residente IT, FULL | CF con Z-xxx, indirizzo italiano, telefono presente |
| T03 | 1 BUSINESS SDC italiana, FULL | CF=P.IVA 11 cifre, rapp. legale con CF proprio |
| T04 | 1 BUSINESS ENTE pubblico, FULL | CF 10 cifre, P.IVA opzionale |
| T05 | 1 BUSINESS DI estera, FULL | VAT Number, nessuna P.IVA italiana |
| T06 | 3 AUTORI italiani, FULL | 3 CF diversi tutti validi |
| T07 | Edge SNC, FULL | Civico="SNC" |
| T08 | Edge km progressivo, FULL | Civico="km 12+500" |
| T09 | BUSINESS con Gruppo IVA, FULL | flag + numero gruppo |
| T10 | COMBO (autore+editore), FULL | Stesso soggetto, 2 ruoli |
| T11 | 10 PRIVATI, ITA+UE 70/30, LIGHT | 7 ITA + 3 UE; campi indirizzo e telefono assenti |
| T12 | 25 PRIVATI, ITA+UE+EXTRA-UE equa, LIGHT | ~8 ITA / ~8 UE / ~9 EXTRA-UE; somma =25; nessun campo indirizzo/telefono |
| T13 | 50 PRIVATI, solo EXTRA-UE, FULL | 50 profili tutti EXTRA-UE con indirizzo e telefono validi |
| T14 | 100 PRIVATI, ITA+EXTRA-UE 60/40, LIGHT | 60 ITA + 40 EXTRA-UE; header riepilogo presente; nessun campo indirizzo/telefono |
| T15 | Personalizzata 55/25/20, totale 10 | Arrotondamento: 5 ITA / 3 UE / 2 EXTRA-UE (somma =10) |
| T16 | 1 BUSINESS SDC-IT LIGHT | Rep. legale: CF presente, data_nascita AAAA-MM-GG decodibile dal CF, stato_nascita=Italia |
| T17 | 1 BUSINESS SDC-DE LIGHT | Rep. legale: CF calcolato con Belfiore Z112 (Germania), data_nascita coerente con CF |
| T18 | 1 BUSINESS SDC-US LIGHT | Rep. legale: CF calcolato con Belfiore Z404 (USA), data_nascita coerente con CF |
| T19 | Mix 5 BUSINESS ITA+UE+EXTRA-UE LIGHT | Tutti i rep. legali hanno CF valido; data_nascita == data decodificata dal CF per ogni rep. |
| T20 | Personalizzata formato "33%, 33%, 34%"; N=10; ITA+UE+EXTRA-UE | Normalizzazione: [33,33,34]; somma=100; 3 ITA + 3 UE + 4 EXTRA-UE (floor+residuo) |
| T21 | Personalizzata formato "70 20 10" (spazio-separato); N=5; ITA+UE+EXTRA-UE | Normalizzazione: [70,20,10]; 3 ITA + 1 UE + 1 EXTRA-UE |
| T22 | Personalizzata formato "40,40,20" (comma-puro senza %); N=10; ITA+UE+EXTRA-UE | Normalizzazione: [40,40,20]; 4 ITA + 4 UE + 2 EXTRA-UE (floor+residuo) |

Verificati: T01-T10 PASS (sia via Python script che via esecuzione manuale Claude
sul caso di riferimento Mario Rossi -> `RSSMRA85A01H501Z`).
T11-T15: nuovi casi per le feature di distribuzione nazionalita' e profilo LIGHT.
T16-T22: nuovi casi per rappresentante legale CF+data_nascita e normalizzazione formato Personalizzata (tutti e 4 i formati coperti: %, comma-puro, spazio, linguaggio naturale).
