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
    "note": "",
    "generated_at_epoch": 1750000000
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
    "note": "",
    "generated_at_epoch": 1750000000
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

In modalita' LIGHT viene omesso anche il nodo `contatti` top-level (incluso `telefono`).

Per profili **BUSINESS / EDITORE** in modalita' LIGHT, ometti anche
`rappresentante_legale.contatti` (il nodo `{"telefono": "..."}` annidato nel
blocco rappresentante legale). Il blocco `rappresentante_legale` resta presente
con tutti gli altri campi (nome, cognome, cf, data_nascita, genere, cittadinanza,
stato_nascita, comune_nascita); solo il sotto-nodo `contatti` viene rimosso.

---

## D. Convenzioni profilo_id

Pattern: `<categoria>-<id_tag>-<forma?>-<area>-<NNN>`

| Categoria | Esempio (con id_tag) | Forma | Area |
|-----------|---------------------|-------|------|
| PRIVATO | `P-83421-IT-001` | — | IT, UE, EXTRA-UE |
| AUTORE | `A-83421-IT-001` | — | IT, UE, EXTRA-UE |
| BUSINESS | `B-SDC-83421-IT-001` | SDC | IT, UE, EXTRA-UE |
| EDITORE | `E-COOP-83421-IT-001` | COOP | IT |
| COMBO | `AE-83421-IT-001` | — | IT (autore+editore stessa persona) |

L'`<id_tag>` è un tag a 5 cifre auto-generato dall'epoch Unix % 100.000 ad ogni
run (o specificato esplicitamente con `--id-tag`). Cambia il seed del PRNG →
nomi diversi tra run successive. L'`<NNN>` è un progressivo 3 cifre zero-padded.

**Backward compat:** Il `profilo_id` è usato come seed PRNG — stesso ID → stesso output.

---

## E. Formati di output supportati

- **JSON**: array di oggetti come sopra
- **CSV**: una riga per profilo, colonne piatte (vedi `to_csv` in `generate_profiles.py`)
- **Markdown FULL**: tabella con ID/categoria/tipo/nome/CF/PIVA/indirizzo/edge
- **Markdown LIGHT**: tabella con ID/categoria/tipo/nome/CF/PIVA/nazionalita'

---

## Changelog

### 2026-06-23
- `meta.generated_at_epoch` (int): timestamp Unix della run di `genera_dataset()`.
  Usato per audit e per verificare l'unicità cross-run dei profili generati.
  Valore `0` indica profili generati direttamente via `genera_profilo()` (path di test diretto).
- `profilo_id`: aggiunto segmento `<id_tag>` (5 cifre epoch) per garantire unicità
  dei nomi tra run successive. Flag CLI `--id-tag` per replay deterministico.
