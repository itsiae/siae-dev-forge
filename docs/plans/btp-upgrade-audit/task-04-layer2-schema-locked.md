# Task 04 — Layer 2: Schema-Locked (error_handlers + logic_blocks + external_calls)

**Stato:** [PENDING]
**File:** `skills/siae-btp-upgrade-audit/SKILL.md` (sezione Phase 1, Layer 2)
**Dipende da:** Task 02, Task 03

---

## Obiettivo

Implementare nella skill il protocollo Layer 2: Claude legge il codice JS e popola
`error_handlers`, `logic_blocks` (condizioni + side_effects), e `external_calls`
usando esclusivamente valori verbatim, enum o boolean. Zero campi liberi.

---

## Step 1 — Verifica prerequisito Task 02 e 03

```bash
grep -c "odata_v2_calls\|method_signatures" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `2` o più

---

## Step 2 — Sostituisci il placeholder `[PLACEHOLDER: PHASE 1 — Layer 2]` con la sezione seguente

Se il placeholder non esiste, aggiungi dopo la sezione Layer 1-B.

La sezione da aggiungere è:

```markdown
### Layer 2 — Schema-Locked (Claude come estrattore)

#### Regola di Atomicità — OBBLIGATORIA

<EXTREMELY-IMPORTANT>
Unità di elaborazione Layer 2: **un file controller alla volta**.
Per ogni file, estrai TUTTI i metodi in UN'UNICA invocazione Claude.
NON processare un metodo per volta. NON spezzare un file in più chiamate.
NON concatenare più file in una sola chiamata.

Flusso corretto:
  per ogni file JS del controller:
    → UNA invocazione Claude con il contenuto COMPLETO del file
    → estrae TUTTI i method_signatures trovati in quel file
    → produce il blocco YAML completo per quel file in un solo output
</EXTREMELY-IMPORTANT>

<EXTREMELY-IMPORTANT>
REGOLA ASSOLUTA DI DETERMINISTMO — NESSUNA ECCEZIONE:

Ogni campo che compili deve essere UNO di questi tipi:
- string: estratto VERBATIM dal codice (copia carattere per carattere, max 120 char)
- boolean: true | false
- integer: numero intero
- enum: uno dei valori nella lista definita
- null: se non trovato (MAI scrivere "probabilmente", "sembra", "potrebbe")

Se un valore non è estraibile verbatim dal codice → scrivi null.
Se non sei sicuro → scrivi null.
MAI parafrasare, MAI descrivere, MAI interpretare.
</EXTREMELY-IMPORTANT>

Per ogni metodo presente in `method_signatures`, leggi il contenuto del controller
e popola la seguente struttura:

#### error_handlers
```yaml
error_handlers:
  - method: "<nome_metodo>"       # verbatim da method_signatures
    present: true | false         # boolean: c'è almeno un handler?
    type: "<enum>"                # enum: catch | attachRequestFailed | onerror | fnError | null
    verbatim: "<riga_esatta>"     # verbatim: la riga esatta dell'handler (max 120 char) | null
    file: "<path>"                # verbatim: path del file
    line: <N>                     # integer: numero riga
```

Regola: se `present: false` → tutti gli altri campi sono `null`.

#### logic_blocks
```yaml
logic_blocks:
  - method: "<nome_metodo>"
    inputs: ["<param1>", "<param2>"]   # lista verbatim dei parametri dalla firma

    conditions:
      - line: <N>
        verbatim: "<if_condition>"     # verbatim: tutto il testo dell'if (max 120 char)
        nesting_depth: 0               # v1.3: integer — 0=top-level, 1=inside one if, 2=inside two if (max 2)
        branch_true:                   # lista verbatim di TUTTE le azioni nel ramo true (max 120 char ciascuna)
          - "<azione_1>"
          - "<azione_2>"
        branch_false:                  # lista verbatim di TUTTE le azioni nel ramo false | [] se assente
          - "<azione_1>"
        nested:                        # condizioni annidate (max depth 2) | [] se assenti
          - line: <N>
            verbatim: "<if_annidato>"
            nesting_depth: 1           # sempre 1 se è dentro una condition di depth 0
            branch_true:
              - "<azione>"
            branch_false: []

    side_effects:
      - type: "<enum>"                 # enum: MessageBox.error | MessageBox.success | MessageBox.warning | navigation | OData.write | OData.read | BusyIndicator | Fragment | null
        verbatim: "<riga_esatta>"      # verbatim: riga esatta (max 120 char)

    timing_annotations:                # v1.3 — delay/debounce logic nel metodo
      - line: <N>
        # enum: setTimeout | setInterval | debounce | throttle
        type: "<enum>"
        delay_ms: <N> | null          # intero (ms) se estratto verbatim, null se non determinabile
        verbatim: "<riga_esatta>"

    data_transforms:                   # v1.2 — trasformazioni dati rilevate nel metodo
      - line: <N>
        # enum: reduce | filter | map | sort | arithmetic | format | parse | date
        operation: "<enum>"
        verbatim: "<riga_esatta>"      # verbatim: riga esatta (max 120 char)

    return_values:
      - verbatim: "<return_statement>" # verbatim: es "return false" | null se void
```

Regola: se un metodo non ha `if`/`else` → `conditions: []`
Regola: se un metodo non fa side effect → `side_effects: []`
Regola: se un metodo non ha trasformazioni dati → `data_transforms: []`
Regola: `branch_true`/`branch_false` sono sempre liste (anche se contengono un solo elemento)
Regola: `nested` max depth 2 — non scendere oltre il secondo livello di if annidato

#### external_calls
```yaml
external_calls:
  - method: "<nome_metodo>"
    type: "<enum>"                 # enum: callFunction | read | create | update | remove | batch
    endpoint: "<stringa>"          # verbatim: il path dell'endpoint (es. "/FunctionImport")
    verbatim: "<riga_esatta>"      # verbatim: la riga della chiamata (max 120 char)
    file: "<path>"
    line: <N>
    callbacks:                     # v1.2 — handler success/error della callback OData
      success_signature: "<params>"  # v1.3: verbatim parametri della callback success | null
      success:                     # lista verbatim delle azioni nel handler success | [] se assente
        - "<azione_1>"
        - "<azione_2>"
      error_signature: "<params>"    # v1.3: verbatim parametri della callback error | null
      error:                       # lista verbatim delle azioni nel handler error | [] se assente
        - "<azione_1>"
      style: "object_config"       # v1.3 enum: object_config | promise | async_await
```

#### Validazione Completeness (OBBLIGATORIA prima di salvare il YAML)

Prima di produrre il fingerprint finale, esegui questa verifica di completeness:

```python
# Conta i metodi trovati da grep (Layer 1-B) per questo file
GREP_METHOD_COUNT = <N>  # da method_signatures Layer 1-B per questo file

# Conta i metodi estratti da Layer 2
LAYER2_METHOD_COUNT = len(logic_blocks)  # metodi nel fingerprint Layer 2

completeness_ratio = LAYER2_METHOD_COUNT / GREP_METHOD_COUNT if GREP_METHOD_COUNT > 0 else 1.0

if completeness_ratio < 1.0:
    # BLOCCA — Layer 2 ha tronco l'output
    # Aggiungi al fingerprint:
    layer2_completeness = {
        "file": "<FILE_PATH>",
        "methods_expected": GREP_METHOD_COUNT,
        "methods_extracted": LAYER2_METHOD_COUNT,
        "completeness_ratio": completeness_ratio,
        "status": "INCOMPLETE"  # WARNING nel gap report
    }
    # Ripeti l'estrazione Layer 2 su questo file prima di procedere
```

Se `completeness_ratio < 1.0` dopo 2 tentativi: spezza il file in metà e processa in 2 invocazioni separate.

#### Checklist di auto-verifica prima di salvare il YAML

Prima di produrre il fingerprint finale, verifica ogni campo:
- [ ] Nessun campo di tipo stringa contiene una mia parafrasi
- [ ] Ogni `verbatim` è copiato direttamente dal codice sorgente
- [ ] Ogni campo `null` è davvero non trovato nel codice
- [ ] Nessun campo enum contiene un valore non nella lista definita
- [ ] I `line` numbers corrispondono alle righe reali del file
- [ ] `branch_true`/`branch_false` sono liste (non stringhe singole)
- [ ] `nesting_depth` è 0 per condizioni top-level, 1+ per annidate
- [ ] `timing_annotations` è popolato se Layer 1-E ha trovato setTimeout/debounce nel file
- [ ] `data_transforms` è popolato se Layer 1-E ha trovato match nel file
- [ ] `callbacks.success_signature`/`error_signature` sono verbatim dei parametri (es. `"function(oData, oResponse)"`)
- [ ] `completeness_ratio` è 1.0 (tutti i metodi estratti)

Se anche UN campo fallisce la checklist → azzeralo a `null`.
```

---

## Step 3 — Verifica che la sezione Layer 2 sia presente

```bash
grep -c "error_handlers\|logic_blocks\|external_calls" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `3` o più

```bash
grep -c "VERBATIM\|null.*non trovato\|enum:" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `3` o più

---

## Step 4 — Commit

```bash
git add skills/siae-btp-upgrade-audit/SKILL.md
git commit -m "feat(skills): add layer2 schema-locked extraction protocol to btp-upgrade-audit"
```
