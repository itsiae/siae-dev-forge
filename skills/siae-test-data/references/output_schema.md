# Output schema — Struttura JSON canonica del profilo

Ogni profilo generato DEVE rispettare uno di questi due schemi (persona fisica
o persona giuridica). Tutti i campi sono obbligatori salvo dove indicato come
opzionale.

---

## A. Persona fisica (PRIVATO / AUTORE)

```json
{
  "profilo_id": "P-IT-001",
  "macro_categoria": "PRIVATO",
  "ruoli": ["UTILIZZATORE"],
  "tipo_persona": "FISICA",
  "tipo_profilo": "P-IT",
  "anagrafica": {
    "nome": "Mario",
    "cognome": "Rossi",
    "codice_fiscale": "RSSMRA85A01H501Z",
    "data_nascita": "1985-01-01",
    "data_nascita_serial": 31048,
    "genere": "M",
    "cittadinanza": "Italiana",
    "stato_nascita": "Italia",
    "provincia_nascita": "RM",
    "comune_nascita": "Roma"
  },
  "contatti": {
    "telefono": "+39 3331112233"
  },
  "indirizzo": {
    "toponimo": "VIA",
    "via": "Roma",
    "civico": "10",
    "cap": "00184",
    "citta": "Roma",
    "provincia": "RM",
    "stato": "Italia",
    "tipo": "RES",
    "edge_case": null
  },
  "meta": {
    "residenza_it": true,
    "edge_case": null,
    "calcolo_cf": "calcolato",
    "note": ""
  }
}
```

### Valori ammessi
- `macro_categoria`: `PRIVATO` | `AUTORE` | `EDITORE` (se ed. persona fisica)
- `tipo_profilo`: `P-IT` | `P-EU-RES` | `P-EU-NORES` | `P-EXT-RES` | `P-EXT-NORES`
- `genere`: `M` | `F`
- `cittadinanza`: `Italiana` per IT, nome stato esteso per altri
- `provincia_nascita`: sigla 2 char per IT, `—` per esteri
- `comune_nascita`: nome comune per IT, `null` per esteri
- `codice_fiscale`: 16 char per residenti IT; `null` ammesso per stranieri NON residenti
- `tipo` indirizzo: `RES` (residenza) | `DOM` (domicilio)
- `calcolo_cf`: `calcolato` | `calcolato_facoltativo` | `non_inserito`

---

## B. Persona giuridica (BUSINESS / EDITORE societario)

```json
{
  "profilo_id": "B-SDC-IT-001",
  "macro_categoria": "BUSINESS",
  "ruoli": ["UTILIZZATORE"],
  "tipo_persona": "GIURIDICA",
  "tipo_profilo": "G-SDC",
  "soggetto_giuridico": {
    "ragione_sociale": "Tech Solutions S.R.L. 0001",
    "forma_giuridica_codice": "SDC",
    "natura_giuridica": "S.R.L.",
    "codice_fiscale_ente": "12345670582",
    "partita_iva": "12345670582",
    "vat_number": null,
    "gruppo_iva": false,
    "gruppo_iva_numero": null,
    "vincolo_cf_piva": "CF = P.IVA (obbligatorio)"
  },
  "rappresentante_legale": {
    "nome": "Giulia",
    "cognome": "Bianchi",
    "codice_fiscale": "BNCGLI80A41F205X",
    "data_nascita": "1980-01-01",
    "data_nascita_serial": 29222,
    "genere": "F",
    "cittadinanza": "Italiana",
    "stato_nascita": "Italia",
    "provincia_nascita": "MI",
    "comune_nascita": "Milano",
    "contatti": {"telefono": "+39 3501112233"}
  },
  "indirizzo": {
    "toponimo": "VIA",
    "via": "Roma",
    "civico": "10",
    "cap": "00184",
    "citta": "Roma",
    "provincia": "RM",
    "stato": "Italia",
    "tipo": "SEDE_LEGALE",
    "edge_case": null
  },
  "meta": {
    "residenza_it": true,
    "edge_case": null,
    "calcolo_cf": "uguale_piva",
    "note": ""
  }
}
```

### Valori ammessi
- `forma_giuridica_codice`: `DI` | `ENTEP` | `ENTE` | `IST` | `ONP` | `COOP` | `SDC` | `SDP`
- `tipo_profilo`: `G-<codice>` (es. `G-SDC`)
- `tipo` indirizzo: `SEDE_LEGALE` (default) | `SEDE_OPERATIVA`
- `vat_number`: stringa per sede estera (formato `<2lett><cifre>`), `null` per sede IT
- `gruppo_iva`: boolean
- `gruppo_iva_numero`: stringa `GR<5cifre>` se gruppo_iva=true, altrimenti `null`
- `calcolo_cf`: `ente_numerico` | `uguale_piva` | `personale_titolare`
- `vincolo_cf_piva`: stringa descrittiva (vedi `forme_giuridiche.json`)

---

## C. Variante LIGHT — oggetto `indirizzo` ridotto

In modalita' LIGHT i campi `via`, `civico`, `cap`, `citta`, `provincia`, `stato`,
`tipo`, `edge_case` sono omessi. L'oggetto `indirizzo` contiene solo:

```json
"indirizzo": {
  "nazione_residenza": "Italia",
  "nazione_residenza_code": "IT"
}
```

Esempi di `nazione_residenza_code`: `IT`, `DE`, `FR`, `US`, `JP`, ecc. (ISO 3166-1 alpha-2).

In modalita' LIGHT viene omesso anche il nodo `contatti` (incluso `telefono`).

---

## D. Convenzioni profilo_id

Pattern: `<categoria>-<forma?>-<area>-<NNN>`

| Categoria | Esempio | Forma | Area |
|-----------|---------|-------|------|
| PRIVATO | `P-IT-001` | — | IT, UE, EXTRA-UE |
| AUTORE | `A-IT-001` | — | IT, UE, EXTRA-UE |
| BUSINESS | `B-SDC-IT-001` | SDC | IT, UE, EXTRA-UE |
| EDITORE | `E-COOP-IT-001` | COOP | IT |
| COMBO | `AE-IT-001` | — | (autore+editore stessa persona) |

L'`<NNN>` e' un progressivo 3 cifre zero-padded. Il `profilo_id` e' anche usato
come seed per il generatore deterministico: stesso ID -> stesso output.

---

## E. Formati di output supportati

- **JSON**: array di oggetti come sopra
- **CSV**: una riga per profilo, colonne piatte (vedi `to_csv` in `generate_profiles.py`)
- **Markdown FULL**: tabella con ID/categoria/tipo/nome/CF/PIVA/indirizzo/edge
- **Markdown LIGHT**: tabella con ID/categoria/tipo/nome/CF/PIVA/nazionalita'
