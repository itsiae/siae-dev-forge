# Task 05 — Diff Engine: Confronto Fingerprint Old vs New

**Stato:** [PENDING]
**File:** `skills/siae-btp-upgrade-audit/SKILL.md` (sezione Phase 2 + Diff Engine)
**Dipende da:** Task 02, Task 03, Task 04

---

## Obiettivo

Implementare nella skill:
1. **Phase 2 AUDIT**: acquisisce il fingerprint del nuovo branch (stesso protocollo Phase 1)
2. **Diff Engine**: confronta strutturalmente i due fingerprint e classifica le differenze per severity

---

## Step 1 — Verifica prerequisito: Layer 1 + Layer 2 definiti

```bash
grep -c "logic_blocks\|odata_v2_calls\|deprecated_imports" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `3` o più

---

## Step 2 — Sostituisci `[PLACEHOLDER: PHASE 2 — AUDIT]` e `[PLACEHOLDER: DIFF ENGINE]` con:

```markdown
## Phase 2 — AUDIT: Gap Analysis

### Input
- `<old-branch>`: branch vecchio (baseline già generata in Phase 1)
- `<new-branch>`: branch nuovo (feature/upgrade-*)
- `[--app=nome]`: opzionale

### Protocollo

1. Genera fingerprint del nuovo codice eseguendo ESATTAMENTE lo stesso protocollo
   di Phase 1 (Layer 1 + Layer 2) sul branch `<new-branch>`.
2. Chiama la sezione Diff Engine con i due fingerprint.

---

## Diff Engine — Confronto Strutturale

### Gate: Completeness Validation (OBBLIGATORIA prima del diff engine)

Prima di eseguire qualsiasi regola diff su un'app, verifica che il fingerprint sia completo:

```python
# Per ogni file nel fingerprint:
for fp_file in fingerprint.layer2_completeness:
    if fp_file.get("status") == "INCOMPLETE":
        # Non eseguire il diff engine per questo file
        print(f"WARN: {fp_file['file']} — Layer 2 incompleto "
              f"({fp_file['methods_extracted']}/{fp_file['methods_expected']} metodi). "
              f"Rieseguire Layer 2 prima del diff.")
        # Aggiungi nel gap report una riga WARN invece di diff
        continue
```

**Se il completeness_ratio < 1.0:** il diff engine non può garantire CRITICAL assenti.
Il gap report deve includere nella sezione INFO:
```
[W1] File <path> — Layer 2 incompleto (N/M metodi estratti). Risultati diff parziali.
```

---

### Canonicalizzazione Verbatim (OBBLIGATORIA prima di ogni confronto)

Prima di qualsiasi confronto verbatim, applica questa funzione di canonicalizzazione:

```python
def canonicalize(s):
    """Normalizza verbatim per confronto: rimuove differenze di whitespace irrilevanti."""
    if s is None:
        return None
    import re
    s = re.sub(r'\s+', ' ', s)   # collassa whitespace multiplo
    s = s.strip()                  # rimuovi spazi iniziali/finali
    return s
```

**Regola:** due verbatim `a` e `b` sono equivalenti se `canonicalize(a) == canonicalize(b)`.

Esempio: `if(!oData.codiceAutore)` e `if (!oData.codiceAutore)` → **stessi dopo canonicalize → OK**.
Senza canonicalize, questi produrrebbero un falso `LOGIC DIFF`.

---

### Rilevamento Rinominazioni (Rename Detection)

Dopo aver applicato le regole standard per `method_signatures`, se un metodo `X` è marcato
`CRITICAL` (rimosso) E simultaneamente esiste un metodo `Y` in `new` marcato `INFO` (introdotto),
aggiungi nel report:

```
⚠️ POSSIBILE RENAME: <X> → <Y> — richiede verifica manuale
   Criterio: prefisso identico (es. _load*, on*) oppure nomi con edit-distance ≤ 3
```

Criteri "simile":
- Prefisso identico: `_loadData` e `_loadDataV4` → stesso prefisso `_loadData`
- Edit-distance ≤ 3: `onSave` e `onSaveNew` → differenza di 3 caratteri

**Importante:** il CRITICAL rimane CRITICAL fino a conferma umana. Il Rename Detection
è un suggerimento, non una risoluzione automatica.

---

### Regole di confronto (in ordine di esecuzione)

Per ogni sezione del fingerprint, applica le regole seguenti.
Il confronto è SEMPRE old vs new. Non valutare "è equivalente?" — solo "è canonicamente identico?".

#### deprecated_imports
- Per ogni entry in `old.deprecated_imports`: cerca la stessa `api` in `new.deprecated_imports`
  - Trovata → `OK`
  - Non trovata → `INFO: import rimosso (potenzialmente risolto o perso)`

#### odata_v2_calls
- Per ogni entry in `old.odata_v2_calls`: cerca entry con stessa `entity` + stesso `operation` in `new`
  - Trovata, `verbatim` identico → `OK`
  - Trovata, `verbatim` diverso → `HIGH: OData call modificata — verbatim changed`
  - Non trovata → `CRITICAL: OData call rimossa`
- Per ogni entry in `new.odata_v2_calls` NON presente in `old`: `INFO: nuova OData call introdotta`

#### method_signatures
- Per ogni `name` in `old.method_signatures`: cerca in `new`
  - Trovato → `OK`
  - Non trovato → `CRITICAL: metodo rimosso`
- Per ogni `name` in `new.method_signatures` NON in `old`: `INFO: nuovo metodo introdotto`

#### navigation_targets
- Per ogni `target` in `old.navigation_targets`: cerca in `new`
  - Trovato, `verbatim` identico → `OK`
  - Trovato, `verbatim` diverso → `HIGH: navigation target modificato`
  - Non trovato → `CRITICAL: navigation target rimosso`

#### routing_config
- `old.routing_config.routes` vs `new.routing_config.routes`
  - Route in old ma non in new → `CRITICAL: route rimossa`
  - Route in new ma non in old → `INFO: nuova route aggiunta`

#### error_handlers
- Per ogni metodo con `present: true` in `old.error_handlers`:
  - Stessa entry con `present: true` in new → `OK`
  - Entry con `present: false` in new → `CRITICAL: error handler rimosso dal metodo <nome>`
  - Entry assente in new → `CRITICAL: error handler non trovato nel nuovo codice`

#### logic_blocks — conditions
- Per ogni metodo in `old.logic_blocks`:
  - Per ogni condition `verbatim` in `old`:
    - Trovata in `new` con stesso `verbatim` (canonicalizzato) E stesso `nesting_depth` → `OK`
    - Trovata con `verbatim` identico ma `nesting_depth` diverso → `CRITICAL: livello annidamento modificato — semantica condizione cambiata`
    - Non trovata → `LOGIC DIFF: condizione rimossa — revisione umana richiesta`
    - Trovata con `verbatim` diverso → `LOGIC DIFF: condizione modificata — revisione umana richiesta`
  - Per ogni elemento in `old.condition.branch_true[]` (confronto ORDINATO — non come set):
    - Elemento all'indice `i` uguale in `new.branch_true[i]` (canonicalizzato) → `OK`
    - Elemento non trovato allo stesso indice → `LOGIC DIFF: azione nel ramo true modificata o riordinata — revisione umana richiesta`
    - Lista di lunghezza diversa → `LOGIC DIFF: numero azioni nel ramo true modificato`
  - Per ogni elemento in `old.condition.branch_false[]` (confronto ORDINATO):
    - Stessa regola di branch_true
  - Per ogni condition `nested[]` in `old`:
    - Trovata condizione annidata identica (per `verbatim` + `nesting_depth`) in `new` → `OK`
    - Non trovata → `LOGIC DIFF: condizione annidata rimossa — revisione umana richiesta`
    - Trovata ma `verbatim` diverso → `LOGIC DIFF: condizione annidata modificata`

**REGOLA ORDERING:** Il confronto di `branch_true[]` e `branch_false[]` è ORDINATO (lista, non set).
Due liste `[A, B]` e `[B, A]` → `LOGIC DIFF: ordine delle azioni modificato — verificare race condition`.

#### logic_blocks — data_transforms (NUOVO v1.2)
- Per ogni entry in `old.logic_blocks[method].data_transforms`:
  - Trovata in `new` con stessa `operation` + `verbatim` canonicalizzato → `OK`
  - Trovata con stessa `operation` ma `verbatim` diverso → `LOGIC DIFF: trasformazione dati modificata — verificare logica di mapping/calcolo`
  - Non trovata → `LOGIC DIFF: trasformazione dati rimossa — possibile perdita di mapping/calcolo`
- Per ogni entry in `new.data_transforms` NON in `old`: `INFO: nuova trasformazione dati introdotta`

#### logic_blocks — side_effects
- Per ogni `type` + `verbatim` in `old.logic_blocks[method].side_effects`:
  - Trovato identico in `new` → `OK`
  - Trovato `type` identico ma `verbatim` diverso → `LOGIC DIFF: side effect modificato`
  - Non trovato → `LOGIC DIFF: side effect rimosso`

#### external_calls
- Per ogni entry in `old.external_calls` (per `endpoint`):
  - Trovata in `new` con stesso `endpoint` e `type` → `OK`
  - Trovata con `type` diverso → `HIGH: chiamata esterna cambiata tipo`
  - Non trovata → `CRITICAL: chiamata esterna rimossa`
- Per ogni entry trovata (stesso `endpoint`), confronta callbacks (v1.2):
  - `old.callbacks.style` vs `new.callbacks.style`:
    - Identici → OK
    - Diversi (es. `object_config` → `promise`) → `HIGH: stile callback OData cambiato — verificare mappatura success/error`
  - `old.callbacks.success_signature` vs `new.callbacks.success_signature`:
    - Identici (canonicalizzati) → OK
    - Diversi → `LOGIC DIFF: signature callback success modificata — parametri cambiati`
    - OLD ha signature, NEW è null → `CRITICAL: callback success rimossa`
  - `old.callbacks.error_signature` vs `new.callbacks.error_signature`:
    - Identici → OK
    - OLD ha signature, NEW è null → `CRITICAL: callback error rimossa — gestione errori OData persa`
  - Per ogni elemento in `old.callbacks.success[]` (confronto ORDINATO):
    - Trovato allo stesso indice in `new.callbacks.success[]` → `OK`
    - Non trovato → `CRITICAL: azione nel callback success rimossa — potenziale perdita di logica post-OData`
  - Per ogni elemento in `old.callbacks.error[]` (confronto ORDINATO):
    - Trovato allo stesso indice in `new.callbacks.error[]` → `OK`
    - Non trovato → `CRITICAL: azione nel callback error rimossa — gestione errore OData persa`

#### timing_annotations (v1.3)
- Per ogni entry in `old.timing_annotations[method]`:
  - Trovata in `new` con stesso `type` e `delay_ms` → `OK`
  - Trovata con `type` identico ma `delay_ms` diverso → `LOGIC DIFF: delay modificato — verificare debounce/race condition`
  - Non trovata → `LOGIC DIFF: timing logic rimossa — possibile race condition o double-submit`

#### eventbus_calls (v1.3)
- Per ogni `subscribe` in `old.eventbus_calls`:
  - Trovato in `new` con stesso `channel` + `event` → `OK`
  - Non trovato → `CRITICAL: subscriber EventBus rimosso — sincronizzazione inter-controller persa`
- Per ogni `publish` in `old.eventbus_calls`:
  - Trovato in `new` con stesso `channel` + `event` → `OK`
  - Non trovato → `CRITICAL: publisher EventBus rimosso — evento non più emesso`
- Per ogni `publish/subscribe` in `new` NON in `old`: `INFO: nuovo evento EventBus introdotto`

#### model_lifecycle_handlers (v1.3)
- Per ogni entry in `old.model_lifecycle_handlers`:
  - Trovata con stesso `event` + `verbatim` canonicalizzato → `OK`
  - Trovata con `event` identico ma `verbatim` diverso → `HIGH: init hook modificato`
  - Non trovata → `CRITICAL: init hook rimosso — possibile app che non carica dati al boot`

#### fragment_loads (v1.3)
- Per ogni entry in `old.fragment_loads`:
  - Trovata con stesso `style` + `name` → `OK`
  - Trovata con `name` diverso → `HIGH: fragment path cambiato — layout/logica diversa`
  - Non trovata → `CRITICAL: fragment rimosso`

#### dialog_lifecycle (v1.3)
- Per ogni entry in `old.dialog_lifecycle`:
  - Trovata con stesso `event` + `verbatim` canonicalizzato → `OK`
  - Non trovata → `CRITICAL: side-effect post-dialog perso`

#### model_bindings (v1.3)
- Per ogni entry in `old.model_bindings`:
  - `binding_type` identico → `OK`
  - `binding_type` cambiato da `getModel` a `component_property` → `HIGH: pattern binding model modificato`
  - `getModel("X")` vs `getModel("Y")` (nomi diversi) → `CRITICAL: nome model OData cambiato`

#### external_formatters (v1.3)
- Per ogni entry in `old.external_formatters`:
  - `formatter_path` identico → `OK`
  - `formatter_path` diverso → `HIGH: path formatter esterno cambiato`
  - Non trovato → `HIGH: import formatter esterno rimosso`

#### xmlview_bindings
- Per ogni entry `type=formatter` in `old.xmlview_bindings`:
  - Trovata (stessa `verbatim` canonicalizzata) → `OK`
  - Non trovata → `HIGH: formatter rimosso da XMLView — logica display potenzialmente persa`
- Per ogni entry `type=press|change|selectionChange` in `old`:
  - Trovata → `OK`
  - Non trovata → `CRITICAL: event handler binding rimosso da XMLView`
- Per ogni `type=fragment` in `old`:
  - Trovato (stesso `fragmentName`) → `OK`
  - Non trovato → `HIGH: fragment include rimosso`

#### component_models
- Per ogni entry in `old.component_models` (per `name`):
  - Trovata con stesso `type` e `verbatim` canonicalizzato → `OK`
  - Trovata con `type` diverso → `CRITICAL: modello registrato con tipo diverso`
  - Trovata con `name` diverso (modello rinominato) → `CRITICAL: nome modello cambiato — tutti i controller che lo usano sono rotti`
  - Non trovata → `CRITICAL: registrazione modello rimossa da Component.js`

#### data_sources
- Per ogni entry in `old.data_sources` (per `name`):
  - Trovata con `uri` identica → `OK`
  - Trovata con `uri` diversa → `CRITICAL: URI servizio OData cambiata — TUTTE le chiamate sono rotte`
  - Non trovata → `CRITICAL: dataSource rimosso da manifest.json`

### Tabella Severity

| Severity | Significato | Richiede azione |
|----------|-------------|-----------------|
| `CRITICAL` | Funzionalità rimossa o non trovata | Blocca la PR |
| `HIGH` | Comportamento modificato ma presente | Review obbligatoria |
| `LOGIC DIFF` | Condizione/side-effect diverso — human review | Review obbligatoria |
| `INFO` | Nuovo codice introdotto o import rimosso | Review consigliata |
| `OK` | Identico | Nessuna azione |
```

---

## Step 3 — Verifica che le sezioni siano presenti

```bash
grep -c "CRITICAL\|LOGIC DIFF\|HIGH\|Phase 2" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `4` o più

---

## Step 4 — Commit

```bash
git add skills/siae-btp-upgrade-audit/SKILL.md
git commit -m "feat(skills): add phase2 and diff engine to btp-upgrade-audit"
```
