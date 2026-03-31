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
    - Trovata identica in `new` (stesso metodo, stesso verbatim) → `OK`
    - Non trovata → `LOGIC DIFF: condizione rimossa — revisione umana richiesta`
    - Trovata ma `verbatim` diverso → `LOGIC DIFF: condizione modificata — revisione umana richiesta`
  - Per ogni elemento in `old.condition.branch_true[]`:
    - Trovato (canonicalizzato) in `new.condition.branch_true[]` per la stessa condizione → `OK`
    - Non trovato → `LOGIC DIFF: azione nel ramo true rimossa — revisione umana richiesta`
  - Per ogni elemento in `old.condition.branch_false[]`:
    - Trovato (canonicalizzato) in `new.condition.branch_false[]` → `OK`
    - Non trovato → `LOGIC DIFF: azione nel ramo false rimossa — revisione umana richiesta`
  - Per ogni condition `nested[]` in `old`:
    - Trovata condizione annidata identica (per `verbatim` canonicalizzato) in `new` → `OK`
    - Non trovata → `LOGIC DIFF: condizione annidata rimossa — revisione umana richiesta`
    - Trovata ma `verbatim` diverso → `LOGIC DIFF: condizione annidata modificata`

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
- Per ogni entry trovata (stesso `endpoint`), confronta callbacks (NUOVO v1.2):
  - Per ogni elemento in `old.callbacks.success[]`:
    - Trovato (canonicalizzato) in `new.callbacks.success[]` → `OK`
    - Non trovato → `CRITICAL: azione nel callback success rimossa — potenziale perdita di logica post-OData`
  - Per ogni elemento in `old.callbacks.error[]`:
    - Trovato (canonicalizzato) in `new.callbacks.error[]` → `OK`
    - Non trovato → `CRITICAL: azione nel callback error rimossa — gestione errore OData persa`

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
