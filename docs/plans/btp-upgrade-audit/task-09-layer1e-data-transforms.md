# Task 09 — Layer 1-E: Pre-location Trasformazioni Dati (grep)

**Stato:** [PENDING]
**File:** `skills/siae-btp-upgrade-audit/SKILL.md` (sezione Phase 1, Layer 1-E)
**Dipende da:** Task 02, Task 03

---

## Obiettivo

Aggiungere un passaggio bash prima di Layer 2 che individua i file JS
con trasformazioni dati (`.reduce`, `.filter`, `.map`, `.sort`, `Math.*`,
`parseInt`, `parseFloat`, `toFixed`, `DateFormat.*`).

Questo serve a:
1. Passare al Layer 2 la lista dei file che **probabilmente** contengono `data_transforms`
2. Aumentare la completezza del fingerprint senza richiedere un'invocazione Claude aggiuntiva

Il Layer 2 usa queste segnalazioni come **hint**: sa su quali metodi concentrarsi
per popolare `data_transforms`. Non è un'esclusione — Layer 2 popola `data_transforms`
per tutti i metodi, ma la segnalazione riduce i falsi negativi.

---

## Step 1 — Verifica prerequisito

```bash
grep -c "odata_v2_calls\|method_signatures\|xmlview_bindings" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `3` o più

---

## Step 2 — Aggiungi Layer 1-E nella skill

Aggiungere **dopo** la sezione Layer 1-C (component_models) e **prima** di Layer 1-D (CAP CDS),
la seguente sezione:

```markdown
### Layer 1-E: Pre-location Trasformazioni Dati

Eseguire su tutti i file JS del controller per segnalare al Layer 2
i file che contengono potenziali trasformazioni dati da tracciare.

```bash
# Per ogni file JS del controller già recuperato (SHA noti da Layer 1-A):
echo "$JS_CONTENT" | grep -n \
  -e "\.reduce\s*(" \
  -e "\.filter\s*(" \
  -e "\.map\s*(" \
  -e "\.sort\s*(" \
  -e "Math\." \
  -e "parseInt\s*(" \
  -e "parseFloat\s*(" \
  -e "\.toFixed\s*(" \
  -e "DateFormat\." \
  | sort \
  | while IFS=: read -r LINE REST; do
      VERBATIM=$(echo "$REST" | sed 's/^[[:space:]]*//' | cut -c1-120)
      printf "  - file: \"%s\"\n    line: %s\n    hint: \"%s\"\n" \
        "<JS_FILE_PATH>" "${LINE}" "${VERBATIM}"
    done
```

Output (segnalazione per Layer 2):
```yaml
data_transforms_hints:            # solo per Layer 2 — non incluso nel fingerprint finale
  - file: "webapp/controller/App.controller.js"
    line: 45
    hint: "aData.filter(function(o) { return o.stato === 'A'; })"
  - file: "webapp/controller/App.controller.js"
    line: 89
    hint: "Math.round(fImporto * 100) / 100"
```

**Nota:** `data_transforms_hints` è una struttura di supporto usata solo per
guidare Layer 2. NON viene inclusa nel fingerprint YAML finale.
Il fingerprint finale contiene `data_transforms` (popolato da Layer 2).

Enum `operation` per Layer 2:
- `reduce` → `.reduce(`
- `filter` → `.filter(`
- `map` → `.map(`
- `sort` → `.sort(`
- `arithmetic` → `Math.*`, operatori `* / + -` su variabili numeriche
- `format` → `.toFixed(`, `formatter.*`, `NumberFormat.*`
- `parse` → `parseInt(`, `parseFloat(`, `Number(`
- `date` → `DateFormat.*`, `new Date(`, `.getTime(`, `.toDateString(`

---

### Layer 1-E: Timing Logic Pre-location

Aggiungere nello stesso passaggio il grep per timing logic (setTimeout, debounce, throttle):

```bash
echo "$JS_CONTENT" | grep -n \
  -e "setTimeout\s*(" \
  -e "setInterval\s*(" \
  -e "debounce\s*(" \
  -e "throttle\s*(" \
  | sort \
  | while IFS=: read -r LINE REST; do
      TIMING_TYPE=$(echo "$REST" | grep -oE "setTimeout|setInterval|debounce|throttle" | head -1)
      DELAY=$(echo "$REST" | grep -oE ",\s*[0-9]+" | head -1 | tr -d ', ')
      VERBATIM=$(echo "$REST" | sed 's/^[[:space:]]*//' | cut -c1-120)
      printf "  - file: \"%s\"\n    line: %s\n    type: \"%s\"\n    delay_ms: %s\n    hint: \"%s\"\n" \
        "<JS_FILE_PATH>" "${LINE}" "${TIMING_TYPE}" "${DELAY:-null}" "${VERBATIM}"
    done
```

Output (segnalazione per Layer 2 — `timing_hints`, non nel fingerprint finale):
```yaml
timing_hints:
  - file: "webapp/controller/App.controller.js"
    line: 56
    type: "setTimeout"
    delay_ms: 500
    hint: "setTimeout(function() { this.getModel().create(...); }.bind(this), 500)"
```

**Nota:** `timing_hints` è solo per Layer 2. Il fingerprint finale contiene `timing_annotations`.
```

---

## Step 3 — Istruzioni per Layer 2 (aggiornamento checklist)

Aggiorna la checklist di auto-verifica nel Layer 2 (task-04) aggiungendo:

> Se `data_transforms_hints` contiene righe per questo file → popola
> `data_transforms` per i metodi che contengono quelle righe.
> Se `data_transforms_hints` è vuoto per questo file → `data_transforms: []`
> per tutti i metodi di quel file.

---

## Step 4 — Verifica

```bash
grep -c "data_transforms_hints\|data_transforms\|Layer 1-E" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `3` o più

---

## Step 5 — Commit

```bash
git add skills/siae-btp-upgrade-audit/SKILL.md
git commit -m "feat(skills): add layer1-E data transforms pre-location to btp-upgrade-audit"
```
