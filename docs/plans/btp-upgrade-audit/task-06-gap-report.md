# Task 06 — Gap Report Generator

**Stato:** [PENDING]
**File:** `skills/siae-btp-upgrade-audit/SKILL.md` (sezione Gap Report)
**Dipende da:** Task 05

---

## Obiettivo

Aggiungere alla skill il protocollo di generazione del gap report finale per app,
con sezioni CRITICAL / HIGH / LOGIC DIFF / INFO / OK e il formato markdown definitivo.

---

## Step 1 — Verifica prerequisito: diff engine definito

```bash
grep -c "LOGIC DIFF\|Tabella Severity" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `2` o più

---

## Step 2 — Sostituisci `[PLACEHOLDER: GAP REPORT]` con la sezione seguente

```markdown
## Gap Report — Generazione Output

Dopo aver eseguito il Diff Engine, genera un file markdown per app con questo formato:

### Template: `gap-report/<app-name>.md`

```markdown
# Gap Analysis: <app-name>
**Branch baseline:** <old-branch>
**Branch nuovo:** <new-branch>
**Generato:** <data>
**Items verificati:** <N_OK>/<N_TOT>

---

## CRITICAL (<N>)

<!-- Un entry per ogni item con severity CRITICAL -->
- **[C<N>]** `<sezione>` — `<field>`: `<verbatim_old>` → NON TROVATO nel nuovo codice
  - File baseline: `<file>:<line>`

## HIGH (<N>)

<!-- Un entry per ogni item con severity HIGH -->
- **[H<N>]** `<sezione>` — `<field>`: verbatim cambiato
  - OLD: `<verbatim_old>`
  - NEW: `<verbatim_new>`
  - File baseline: `<file>:<line>`

## LOGIC DIFF (<N>)

<!-- Un entry per ogni condizione o side_effect modificato/rimosso -->
### <metodo> — <tipo_diff>

**OLD (<old-branch>, riga <line>):**
```
<verbatim_old>
```

**NEW (<new-branch>, riga <line> | NON TROVATO):**
```
<verbatim_new OR "NON TROVATO">
```

⚠️ DIFFERENZA STRUTTURALE RILEVATA — REVISIONE UMANA RICHIESTA

## INFO (<N>)

- **[I<N>]** `<sezione>` — `<descrizione verbatim>` (introdotto nel nuovo codice o rimosso)

## OK (<N_OK>/<N_TOT> items verificati)

Tutte le funzionalità seguenti sono presenti e identiche nel nuovo codice:
- `method_signatures`: <N> metodi verificati
- `odata_v2_calls`: <N> chiamate verificate
- `navigation_targets`: <N> target verificati
- `routing_config`: <N> routes verificate
- `error_handlers`: <N> handler verificati
- `logic_blocks.conditions`: <N> condizioni verificate
- `logic_blocks.side_effects`: <N> side effect verificati
- `external_calls`: <N> chiamate esterne verificate
```

### Riepilogo multi-app

Dopo aver generato tutti i report singoli, genera `gap-report/SUMMARY.md`:

```markdown
# Gap Analysis Summary
**Branch baseline:** <old-branch>
**Branch nuovo:** <new-branch>
**Generato:** <data>
**App analizzate:** <N>

| App | CRITICAL | HIGH | LOGIC DIFF | INFO | OK% |
|-----|----------|------|------------|------|-----|
| appavvisi | 0 | 1 | 2 | 3 | 87% |
| appcausali | 2 | 0 | 1 | 0 | 75% |
| ... | ... | ... | ... | ... | ... |

## App che richiedono attenzione immediata (CRITICAL > 0)
- appXXX: N critical issues
```

### Regola: cosa NON scrivere nel report

Il report NON deve contenere:
- Valutazioni soggettive ("questo sembra un bug")
- Suggerimenti di fix ("dovresti aggiungere...")
- Interpretazioni del comportamento ("probabilmente questo causa...")
- Qualsiasi testo non derivato direttamente dai fingerprint

Il report presenta SOLO: old verbatim, new verbatim (o NON TROVATO), severity oggettiva.
```

---

## Step 3 — Verifica che il template del report sia presente

```bash
grep -c "gap-report\|SUMMARY.md\|NON TROVATO" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `3` o più

---

## Step 4 — Placeholder scan finale sull'intera skill

```bash
grep -n "TBD\|TODO\|da definire\|da decidere\|PLACEHOLDER\|\.\.\." \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md \
  | grep -v "^#\|<!--"
```

Output atteso: nessun output (zero placeholder rimasti)

---

## Step 5 — Commit

```bash
git add skills/siae-btp-upgrade-audit/SKILL.md
git commit -m "feat(skills): add gap report generator to btp-upgrade-audit"
```
