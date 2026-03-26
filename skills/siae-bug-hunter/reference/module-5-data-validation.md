# M5 — Data Validation & Boundary Bug Detector

## Regola Fondamentale

Un gap di validazione è un bug se:
1. Il dato invalido è effettivamente **inviabile** dall'utente (non bloccato da HTML5 native o disabilitato)
2. L'errore che ne segue è **visibile o silente ma dannoso** (500 grezzo, dato corrotto, "null" renderizzato)

---

## A — Required vs Optional Mismatch FE↔BE

**Grep FE:**
```
required:\s*true|Validators\.required|z\.string\(\)\.min\(1\)|yup\.\w+\(\)\.required
```

**Grep BE:**
```
@NotNull|@NotBlank|@NotEmpty|nullable\s*=\s*false
```

**Conferma bug:**
- Campo `required: true` nel FE → `@NotNull` mancante nel BE → BE accetta null → dato corrotto nel DB
- Campo `@NotNull` nel BE → opzionale nel FE → utente può inviare senza → riceve 400 grezzo senza spiegazione

**Trigger:** Submit del form con campo vuoto (primo caso) o omissione di campo in edit form (secondo caso).

**Falsificatori:** Campo nascosto con default hardcoded lato FE, trigger server-side che imposta il default.

---

## B — Regex Mismatch FE↔BE (email, CF, IBAN, telefono)

**Grep FE:**
```
pattern:\s*['"][^'"]+['"]|z\.string\(\)\.regex\(|yup\.string\(\)\.matches\(
```

**Grep BE:**
```
@Email|@Pattern\(regexp\s*=\s*"[^"]+"\)|Pattern\.compile\(
```

**Conferma bug:**
1. Estrai regex esatta da FE e da BE
2. Costruisci una stringa che passa la regex FE ma NON la regex BE (o viceversa)
3. Se tale stringa esiste → bug

**Casi comuni:**
- FE: `/^[\w.\-]+@[\w.\-]+\.\w+$/` → accetta `user@localhost` (no TLD)
- BE: `@Email` RFC 5321 → rifiuta `user@localhost` → 400 inatteso
- FE accetta dash nel username → BE pattern non include `\-` → 400

**Trigger:** Utente inserisce email con sottodominio o carattere speciale accettato da FE → BE rifiuta.

---

## B1 — Codici Identificativi SIAE (ISWC, ISRC, EAN-13, Codice Fiscale)

Estensione della categoria B per i codici di dominio SIAE. Un mismatch di regex su questi campi
produce dati non riconciliabili con i cataloghi ufficiali.

**Pattern attesi (fonte di verità: `siae-security §3.2` — allineato al catalogo SIAE ufficiale):**

| Codice | Formato canonico | Regex di riferimento |
|---|---|---|
| ISWC | `T-NNN.NNN.NNN-C` (T + 3 gruppi da 3 cifre separati da punti + 1 cifra check) | `T-\d{3}\.\d{3}\.\d{3}-\d` |
| ISRC | `CC-XXX-YY-NNNNN` (2 lett. paese + 3 alnum + 2 cifre anno + 5 cifre) | `[A-Z]{2}-[A-Z0-9]{3}-\d{2}-\d{5}` |
| EAN-13 | 13 cifre | `\d{13}` |
| CF (Codice Fiscale) | 16 char alfanumerici pattern standard | `[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]` |

**Grep FE:**
```
iswc|isrc|ean|codiceFiscale|codice_fiscale|fiscalCode
```
Poi estrai la regex o la validazione associata al campo.

**Grep BE:**
```
@Pattern.*ISWC\|@Pattern.*ISRC\|iswcPattern\|isrcPattern\|ISWC_REGEX\|ISRC_REGEX
```

**Conferma bug:**
1. Estrai la regex usata in FE per il campo ISWC/ISRC/CF
2. Estrai la regex usata in BE (o la costante di validazione)
3. Costruisci una stringa che passa una regex ma non l'altra
4. Se tale stringa esiste → bug (es: FE accetta ISWC senza trattini, BE li richiede)

**Casi comuni:**
- FE accetta ISRC senza separatori (`GBAYE9200074`), BE richiede formato con trattini (`GB-AYE-92-00074`)
- FE accetta CF maiuscolo/minuscolo, BE valida solo uppercase
- FE manca validazione ISWC → BE salva stringa arbitraria nel catalogo

**Trigger:** Operatore inserisce codice ISWC in formato alternativo (senza trattini) → FE accetta → BE salva valore non normalizzato → riconciliazione con catalogo SIAE fallisce silenziosamente.

**Falsificatori:** normalizzazione lato BFF che converte il formato prima della validazione BE.

---

## C — Enum BE non Mappato nel FE

**Grep BE:**
```
enum\s+\w+\s*\{|@Enumerated|allowableValues\s*=|OpenAPI.*enum
```

**Grep FE:**
```
options:\s*\[|:options="\[|<option\s+value=|radioOptions|selectItems
```

**Conferma bug:**
1. Estrai tutti i valori dell'enum BE
2. Estrai tutte le opzioni del select/radio FE
3. Se un valore BE non è presente nel FE: non selezionabile dall'utente
4. Se API risponde con quel valore: UI non sa come renderizzarlo → blank o errore

**Trigger:** Admin aggiunge nuovo stato via API → FE mostra stringa vuota o non aggiorna il badge.

**Falsificatori:** FE ha handler `default` che mostra il valore raw come fallback.

---

## D — Integer Overflow: Long BE → number JS

**Grep BE:**
```
private\s+Long\s+\w*(id|Id|ID)\|@GeneratedValue.*IDENTITY.*Long\|Long\s+\w*Id
```

**Grep FE:**
```
parseInt\s*\(response\|parseInt\s*\(data\|Number\s*\(.*\.id\)
```

**Conferma bug:**
1. BE usa `Long` per ID (64-bit, max ~9.2 × 10^18)
2. FE usa `parseInt()` o `Number()` senza trattamento speciale
3. `Number.MAX_SAFE_INTEGER` = 2^53 - 1 ≈ 9 × 10^15 → Long > 2^53 viene troncato

**Trigger:** Sistema con molti record (ID > 9.007.199.254.740.992) → FE invia ID troncato → BE non trova il record.

**Falsificatori:** BE serializza ID come string JSON (`@JsonSerialize(using = ToStringSerializer.class)`), FE riceve e usa l'ID come stringa.

---

## E — String Truncation Silente

**Grep BE (DB schema o entity):**
```
@Column\s*\(\s*length\s*=\s*[0-9]+|varchar\s*\(\s*[0-9]+\s*\)
```

**Grep FE:**
```
maxlength\s*=\s*[0-9]+|maxLength:\s*[0-9]+|:maxlength=
```

**Conferma bug:**
1. Estrai `length=N` dalla colonna BE/DB
2. Verifica che il campo FE corrispondente abbia `maxLength=N`
3. Se FE `maxLength` assente o > N → utente può inserire più di N caratteri → BE tronca in silenzio

**Trigger:** Utente scrive un nome prodotto di 110 caratteri (campo varchar(100)) → salvataggio tronca senza avvisare → dati persi.

**Falsificatori:** `@Size(max=N)` in BE che ritorna 400 con messaggio, middleware BE che valida prima di save.

---

## F — Timezone Bug: UTC salvato, locale mostrato senza conversione

**Grep BE:**
```
Instant\.now\(\)\|LocalDateTime\.now\(\)\|new Date\(\)\s*→\s*save
ZonedDateTime\.now\(\)
```

**Grep FE:**
```
new Date\(response\.\w+\)\s*\.toLocale\|moment\(response\.\w+\)\s*\.format
```
Verifica: il FE converte la data in locale dell'utente? O visualizza il valore raw?

**Conferma bug:**
1. BE salva data come UTC (standard)
2. FE visualizza la data senza conversione esplicita al locale del browser
3. La data è usata in un contesto business-critico (scadenza, orario appuntamento, deadline)

**Trigger:** Utente in CET (UTC+2) vede un appuntamento alle 10:00 che in realtà è alle 12:00 locali.

**Falsificatori:** `toLocaleDateString(locale, { timeZone: 'UTC' })`, `moment.tz(date, userTimezone)`, `Intl.DateTimeFormat`.

---

## G — null/undefined Renderizzato come Stringa Letterale

**Grep FE:**
```
{{\s*\w+\.\w+\s*}}\s*(?![\|?])   ← Vue template senza pipe/fallback
{[a-z]+\.[a-z]+}(?!\s*\?\s*\?)   ← React JSX senza optional chain
String\(\w+\)\|\.toString\(\)     ← conversione esplicita senza null-check
```

**Conferma bug:**
1. Template accede a `{{ user.email }}` o `{user.email}` senza fallback
2. BE può rispondere con `email: null` (campo opzionale)
3. Vue/React renderizza `null` → il browser mostra la stringa letterale "null"

**Trigger:** Utente con email non registrata → profilo mostra "null" nel campo email.

**Falsificatori:** `{{ user.email || '' }}`, `{user.email ?? ''}`, `v-if="user.email"`.

---

## H — Stessa Campo, Regex/Validazione Diversa in FE/BE/BFF

Combinazione dei pattern B (regex) e A (required) su più layer:

**Processo:**
1. Identifica il campo in tutti e 3 i layer (FE form, BFF schema, BE DTO)
2. Estrai le regole di validazione da ciascun layer
3. Se le regole differiscono → candidato bug

**Caso comune:** BFF aggrega e applica la propria validazione → BE ha regole diverse → l'utente
riceve un errore dal layer sbagliato con un messaggio non localizzato.

---

## I — Campo Obbligatorio in BE, Opzionale in Alcuni Flussi FE

**Grep BE:**
```
@NotNull\s+private\s+\w+\s+\w+|@NotBlank\s+private\s+String\s+\w+
```

**Grep FE:**
```
v-if\s*=\s*["'].*isCreating|v-show\s*=\s*["'].*mode\s*===|{showField &&
```
Pattern: campo FE con `required: true` solo condizionale (es. solo in create, non in edit).

**Conferma bug:**
1. Campo `@NotNull` in BE DTO (sempre richiesto)
2. In FE il campo è `required` solo in alcune condizioni
3. Esiste un flusso (es. edit) dove il campo non è mostrato/richiesto
4. Il flusso edit invia il DTO al BE senza quel campo → 400 inatteso

**Trigger:** Utente edita il profilo e non vede il campo telefono (condizionale) → submit → "Phone is required" inatteso.

**Falsificatori:** FE invia il valore precedente del campo anche in edit (pre-populated), BE ha `@NotNull` solo in `@Validated(CreateGroup.class)`.
