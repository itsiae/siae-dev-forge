# Design Doc — Superpowers Improvements per siae-dev-forge

> **Data:** 2026-03-22
> **Autore:** Lorenzo (lead AI CC)
> **Story Points:** 5 SP-Umano / 2 SP-Augmented
> **Stato:** APPROVATO

---

## Contesto

Analisi delle PR del progetto Superpowers (un plugin Claude Code analogo) per identificare
improvement portabili in siae-dev-forge. Selezionati 5 improvement ad alto impatto da
implementare come unico feature branch.

**Nota:** L'improvement #866 (sanitize hardcoded paths) è stato verificato durante l'analisi:
grep `/Users/detomasi` su tutto `siae-dev-forge/` ha dato 0 match. Nessun lavoro necessario.

---

## Improvement 1 — Context Awareness (#877)

### Problema
Le skill con fase discovery (brainstorming, tdd, verification, debugging) ri-chiedono
informazioni già presenti nella conversazione corrente (stack, framework, cosa è stato fatto).

### Soluzione
Aggiungere una direttiva "Context-First Rule" in ogni skill target, nella sezione
di discovery/raccolta informazioni.

### Skill target e punto di inserimento

| Skill | Sezione dove inserire |
|-------|----------------------|
| `siae-brainstorming` | Smart Intake (Step 1), prima della tabella "Fonti da leggere" |
| `siae-tdd` | Sezione "Detect Test Framework" o equivalente |
| `siae-verification` | Sezione "IDENTIFICA" (Step 1 del protocollo) |
| `siae-debugging` | Sezione "Raccolta Evidenze" |

### Testo della direttiva (identico per tutte)

```markdown
### Context-First Rule

Prima di leggere file, eseguire comandi, o fare domande all'utente,
verifica se l'informazione e' gia' presente nella conversazione corrente
(messaggi precedenti, output di tool, skill gia' invocate).
Non chiedere cio' che e' gia' stato detto. Non rileggere cio' che e' gia' stato letto.
```

### Criteri di accettazione
- [ ] Direttiva presente in siae-brainstorming/SKILL.md
- [ ] Direttiva presente in siae-tdd/SKILL.md
- [ ] Direttiva presente in siae-verification/SKILL.md
- [ ] Direttiva presente in siae-debugging/SKILL.md

---

## Improvement 2 — Option Zero Gate (#878)

### Problema
Il brainstorming salta da Smart Intake (Step 1-3) direttamente a "Proponi 2-3 approcci"
(Step 4), senza verificare se il problema si risolve senza scrivere codice.

### Soluzione
Inserire uno **Step 3b — Option Zero Gate** tra "Presenta inferenze" (Step 3) e
"Proponi approcci" (Step 4) in `siae-brainstorming/SKILL.md`.

### Testo dello step

```markdown
### Step 3b — Option Zero Gate

Prima di proporre soluzioni che richiedono codice, verifica se il problema
si risolve con una modifica di configurazione, infrastruttura, o processo.

**Checklist Option Zero:**

| # | Verifica | Esempio SIAE |
|---|----------|-------------|
| 1 | AWS Parameter Store / SSM | Cambiare un valore in parameter store risolve? |
| 2 | Terraform variables / tfvars | Basta un tfvar diverso per ambiente? |
| 3 | Feature flag esistente | C'e' gia' un flag che abilita/disabilita questo? |
| 4 | Environment variable | Una env var risolve senza toccare codice? |
| 5 | Ticket DevOps / infra | Basta chiedere al team DevOps un cambio infra? |
| 6 | Servizio/libreria esistente | Un altro repo SIAE fa gia' questo? Riusalo. |
| 7 | Config applicativa | application.yml, .env, config file risolvono? |

**Se Option Zero si applica:**

Presenta la soluzione config/infra, chiedi conferma, e chiudi il brainstorming
senza design doc. Non serve piano implementativo per un cambio config.

Emetti checkpoint:
\```
[BRAINSTORM:OPTION-ZERO] Soluzione senza codice identificata
  Tipo: {config/infra/processo}
  Azione: {descrizione}
  Motivo: {perche' non serve codice}
\```

**Se Option Zero non si applica:**

Documenta brevemente perche' ("Verificato: non esiste parameter store per X,
il comportamento richiede logica nuova") e procedi a Step 4.
```

### Aggiornamenti correlati
- Aggiornare il flowchart graphviz in brainstorming aggiungendo il nodo "Option Zero?"
  tra "need_questions" e "approaches"
- Aggiungere "Option Zero" alla tabella anti-razionalizzazione:
  `"Serve per forza codice nuovo" | "Nel 30% dei casi, una config change basta. Verifica prima."`
- Aggiungere checkpoint strutturato `[BRAINSTORM:OPTION-ZERO]` nella sezione checkpoints

### Criteri di accettazione
- [ ] Step 3b presente in siae-brainstorming/SKILL.md tra Step 3 e Step 4
- [ ] Flowchart graphviz aggiornato con nodo Option Zero
- [ ] Checkpoint strutturato documentato
- [ ] Riga anti-razionalizzazione aggiunta

---

## Improvement 3 — Checkbox Sync (#874)

### Problema
I piani implementativi possono usare due formati per tracciare lo stato dei task:
- **Formato marker:** `[PENDING]` → `[DONE]` (già gestito)
- **Formato checkbox:** `- [ ]` → `- [x]` (NON gestito)

Se un piano usa checkbox markdown, completare un task non aggiorna il file.

### Soluzione
Aggiungere supporto dual-format nelle skill di esecuzione piani.

### File e punto di inserimento

| Skill | Sezione | Modifica |
|-------|---------|----------|
| `siae-executing-plans` | Step 2, dopo punto 5 (riga ~138) | Aggiungere regola dual-format |
| `siae-subagent-development` | Sezione post-task update | Idem |
| `siae-writing-plans` | Template piano | Nota su formato standard |

### Testo da aggiungere (executing-plans e subagent-development)

```markdown
**Aggiornamento stato task — dual format:**

Dopo aver completato un task, aggiorna il marker nel piano:
- Formato marker: `[PENDING]` → `[DONE]` (o `[BLOCKED]`)
- Formato checkbox: `- [ ] Task description` → `- [x] Task description`

Rileva quale formato usa il piano e aggiorna di conseguenza.
Se il piano usa entrambi i formati, aggiorna entrambi.
```

### Testo per writing-plans (nel template)

```markdown
**Formato stato task:** usa `[PENDING]`/`[DONE]`/`[BLOCKED]` come formato primario.
Se il piano contiene checkbox markdown (`- [ ]`), mantienili sincronizzati.
```

### Criteri di accettazione
- [ ] Regola dual-format presente in siae-executing-plans/SKILL.md
- [ ] Regola dual-format presente in siae-subagent-development/SKILL.md
- [ ] Nota formato standard presente in siae-writing-plans/SKILL.md

---

## Improvement 4 — Blind-Review (#865)

### Problema
Il code-reviewer agent riceve contesto completo (diff, piano, file modificati), creando
bias di conferma. Manca un reviewer che parta dalla spec senza sapere cosa è stato toccato.

### Soluzione
Nuova skill `siae-blind-review` — il reviewer riceve SOLO la spec/design doc, deve trovare
il codice autonomamente, e valuta come "auditor ostile".

### Posizionamento — PROGRAMMATICO (non opzionale)

`REQUIRED SUB-SKILL` in `siae-finishing-branch`, come gate obbligatorio prima della PR.
Copre tutti i path di implementazione (subagent, executing-plans, implementazione diretta).

```
Implementation → siae-verification → siae-finishing-branch
                                          ↳ siae-blind-review (REQUIRED)
                                          ↳ PR
```

### Struttura file

```
skills/siae-blind-review/
  SKILL.md
```

### Processo (3 step)

| Step | Azione | Input | Output |
|------|--------|-------|--------|
| 1 | **Carica spec** | Legge SOLO `docs/plans/*-design.md` | Lista requisiti + criteri accettazione |
| 2 | **Trova il codice** | Grep/Glob autonomo partendo dai requisiti. NON legge: git diff, piano implementativo, commit messages, output test | Mappa file trovati → requisiti |
| 3 | **Audit ostile** | Per ogni requisito: il codice lo soddisfa? Feature non richieste (YAGNI)? Gap? | Report PASS/FAIL/DRIFT per requisito |

### Regole chiave

- Il reviewer NON legge: git diff, piano implementativo, commit messages, output di test
- Il reviewer LEGGE SOLO: design doc + codice sorgente trovato autonomamente
- Requisito senza codice → **MISSING**
- Codice senza requisito → **YAGNI**
- Codice che diverge dalla spec → **DRIFT** (con dettaglio)

### Output strutturato

```
BLIND REVIEW REPORT
═══════════════════
Spec: docs/plans/YYYY-MM-DD-<topic>-design.md
Reviewer mode: BLIND (no diff, no plan, no commit history)

| # | Requisito | Codice trovato | Verdetto |
|---|-----------|---------------|----------|
| 1 | ... | src/... | PASS |
| 2 | ... | NON TROVATO | MISSING |
| 3 | — | src/extra.js | YAGNI |

Drift rilevati: N
Missing: M
YAGNI: K
Verdetto finale: PASS / FAIL (se Missing > 0 o Drift critico)
```

### Modifiche a skill esistenti

**siae-finishing-branch:** aggiungere step "Blind Review Gate" prima del push/PR:
```
REQUIRED SUB-SKILL: siae-blind-review
```
Se blind review rileva MISSING o DRIFT critico → blocca la PR, riporta i finding.

**using-devforge:** aggiungere al catalogo:
```
| siae-blind-review | "blind review", "review cieca", "audit spec", "verifica spec vs codice",
|                   | "review senza diff", /forge-blind-review | Rigid | 6. QA Gate |
```

### Criteri di accettazione
- [ ] Skill `siae-blind-review/SKILL.md` creata con processo a 3 step
- [ ] Skill segue template `siae-writing-skills/reference/skill-template.md`
- [ ] REQUIRED SUB-SKILL aggiunto in `siae-finishing-branch/SKILL.md`
- [ ] Trigger aggiunto nel catalogo di `using-devforge/SKILL.md`
- [ ] Output strutturato con verdetto PASS/FAIL/MISSING/DRIFT/YAGNI

---

## Improvement 5 — Retrospective (#864)

### Problema
Le correzioni e lezioni apprese si perdono tra sessioni. I 20 dev SIAE ripetono gli
stessi errori. Lo stop-gate hook intercetta la fine sessione ma fa solo telemetry +
verification gate.

### Soluzione
Nuova skill `siae-retrospective` invocata programmaticamente via stop-gate hook.
A fine sessione, estrae lezioni e le persiste nelle memory files di Claude Code.

### Posizionamento — PROGRAMMATICO

**Primario:** Lo stop-gate hook inietta la direttiva "esegui siae-retrospective" nel
messaggio di block, per sessioni produttive (almeno 1 commit).

**Fallback:** Step opzionale in `siae-verification` con nota: "Se la sessione sta per
chiudersi, esegui retrospective."

### Struttura file

```
skills/siae-retrospective/
  SKILL.md
```

### Processo (3 step)

| Step | Azione | Dettaglio |
|------|--------|-----------|
| 1 | **Raccogli** | Scansiona la conversazione: errori fatti, correzioni ricevute, approcci che hanno funzionato, sorprese |
| 2 | **Classifica** | Per ogni lezione: è un `feedback`, `project`, `user`, o `reference`? |
| 3 | **Persisti** | Salva come memory file in `~/.claude/projects/<project>/memory/` |

### Persistenza — Auto-Memory di Claude Code

```
Salva ogni lezione come memory file seguendo il sistema auto-memory:

1. Classifica la lezione per tipo: feedback, project, user, reference
2. Scrivi il file in ~/.claude/projects/<project>/memory/ con frontmatter
   (name, description, type)
3. Aggiorna MEMORY.md con il puntatore al nuovo file
4. Se esiste gia' una memory sullo stesso tema, aggiornala invece di duplicare

NON salvare in CLAUDE.md, NON salvare nel repo, NON creare file fuori da memory/.
Il sistema auto-memory e' l'unico canale di persistenza cross-sessione.
```

### Filtro "vale la pena salvare?"

```
Salva SOLO se:
- Non derivabile dal codice o git history
- Applicabile a sessioni future (non effimera)
- Sorprendente o non ovvia (non "i test vanno scritti prima")

NON salvare:
- Riassunti di cosa e' stato fatto (c'e' git log)
- Path di file o struttura progetto (c'e' il codice)
- Fix specifici (c'e' il commit)
```

### Output strutturato

```
RETROSPECTIVE
═════════════
Sessione: YYYY-MM-DD
Skills usate: N | Commits: M

Lezioni estratte:
  1. [FEEDBACK] ... → salvato in memory/feedback_xxx.md
  2. [PROJECT] ... → salvato in memory/project_xxx.md
  3. [SCARTATA] ... → motivo: derivabile da git log

Nessuna lezione? → "Sessione pulita, niente da persistere."
```

### Modifica allo stop-gate hook

Dopo il check verification (riga ~129), prima del block finale, aggiungere:

```bash
# Check if retrospective was invoked (solo se sessione produttiva)
if [ "$COMMITS_COUNT" -gt 0 ] && ! echo "$SESSION_SKILLS_CHECK" | grep -qF "siae-retrospective"; then
    # Inietta richiesta retrospective nel messaggio di block
fi
```

Il messaggio di block includerà: "Esegui siae-retrospective prima di fermarti."

### Modifiche a skill esistenti

**using-devforge:** aggiungere al catalogo:
```
| siae-retrospective | fine sessione, lezioni apprese, cosa ho imparato, retrospettiva,
|                    | salva per la prossima volta, /forge-retro | Rigid | Cross-cutting |
```

### Criteri di accettazione
- [ ] Skill `siae-retrospective/SKILL.md` creata con processo a 3 step
- [ ] Skill segue template `siae-writing-skills/reference/skill-template.md`
- [ ] Persistenza SOLO via auto-memory (memory files + MEMORY.md)
- [ ] Filtro "vale la pena salvare" implementato
- [ ] stop-gate hook modificato per iniettare direttiva retrospective
- [ ] Trigger aggiunto nel catalogo di `using-devforge/SKILL.md`

---

## Riepilogo

| # | Improvement | Tipo | File coinvolti | Effort |
|---|------------|------|---------------|--------|
| 1 | Context Awareness | Patch 4 skill | brainstorming, tdd, verification, debugging | 15 min |
| 2 | Option Zero Gate | Patch 1 skill | brainstorming + flowchart | 30 min |
| 3 | Checkbox Sync | Patch 3 skill | executing-plans, subagent-dev, writing-plans | 15 min |
| 4 | Blind-Review | Nuova skill + patch 2 | blind-review, finishing-branch, using-devforge | 2-3h |
| 5 | Retrospective | Nuova skill + patch 2 | retrospective, stop-gate, using-devforge | 3-4h |

**Story Points totali: 5 SP-Umano / 2 SP-Augmented**

## Decisioni Architetturali (ADR)

1. **Option Zero prima degli approcci** — evita brainstorming inutile per problemi risolvibili con config
2. **Blind-review programmatico** — REQUIRED SUB-SKILL in finishing-branch, non opzionale
3. **Retrospective programmatica** — via stop-gate hook injection, non on-demand
4. **Persistenza retrospective** — SOLO auto-memory di Claude Code, non CLAUDE.md o file nel repo
5. **Sanitize paths (#866)** — già pulito, nessun lavoro necessario
