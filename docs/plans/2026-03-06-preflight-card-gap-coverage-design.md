# Pre-Flight Card Gap Coverage — Design Doc

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-writing-plans` per trasformare questo design in piano implementativo.

**Goal:** Colmare i 20 gap nelle pre-flight card: operazioni rischiose che il design system prevede ma che le skill non mostrano.
**Architettura:** Card inline nelle SKILL.md con blocco `generate-card.py`, stesso pattern già consolidato.
**Stack:** Markdown (SKILL.md files), design-system/generate-card.py (invariato)
**SP:** 5

---

## Contesto

### Problema

L'audit delle skill ha rivelato **20 operazioni rischiose** (rischio >= 🟡) che **non mostrano pre-flight card** nonostante `devforge-visual.md` le renda obbligatorie.

Distribuzione per livello:
- 🚨 CRITICO: 6 gap (terraform apply, S3 deletion, credentials rotation, tag rollback, IAM policy, Glue deploy)
- 🔴 ALTO: 5 gap (push post-review, integrazione agenti, schema Glue, Glue manual run, rebase condiviso)
- 🟡 MEDIO: 9 gap (PR create, test/build, commit piano, batch execution, dispatch agenti, codebase map, CLAUDE.md, debugging fix)

### Causa

Il design doc precedente (`2026-03-06-preflight-card-standardization-design.md`) ha standardizzato il **formato** delle card esistenti, ma non ha verificato la **copertura**: molte skill classificano il rischio nella tabella ma non generano la card nello step.

---

## Design Approvato

### Approccio: Card Inline nelle Skill (Approccio A)

Aggiungere direttamente in ogni SKILL.md il blocco `generate-card.py` negli step che mancano la card. Pattern identico a quello già usato in `siae-finishing-branch`, `siae-security`, etc.

**Alternative scartate:**
- Card Registry centralizzato (SP: 8) — astrazione prematura, le card hanno contesto diverso per skill
- Card Middleware automatico (SP: 13) — le skill sono prompt Markdown, non codice eseguibile

### Formato Standard dell'Intervento

Ogni gap viene colmato con 3 parti:

**1. Etichetta rischio nello step:**
```markdown
### Step N — Nome Step

🔴 ALTO — Mostra pre-flight card prima di eseguire
```

**2. Blocco generate-card.py inline:**
```markdown
<EXTREMELY-IMPORTANT>
NON costruire card a mano. Usa SEMPRE `design-system/generate-card.py`.
</EXTREMELY-IMPORTANT>

Genera la card con:
[blocco bash con JSON specifico dell'operazione]
```

**3. Colonna "Card" nella tabella Classificazione Rischio:**
```markdown
| Operazione | Livello | Card |
|------------|---------|------|
| operazione X | 🟡 Medio | Si |
```

---

## Inventario Gap per Skill

| Skill | Gap # | Operazione | Livello Card | Posizione |
|-------|-------|-----------|-------------|-----------|
| siae-git-worktrees | 1 | `git worktree remove --force` | 🔴 ALTO | Sezione "Comandi Utili" |
| siae-git-worktrees | 2 | `git rebase -i` su branch condiviso | 🚨 CRITICO | Nuovo paragrafo warning |
| siae-git-workflow | 3 | `git push origin :refs/tags/PRODUZIONE` | 🚨 CRITICO | Sezione rollback |
| siae-debugging | 4 | Fase 4 Implementation | 🟡 MEDIO | Inizio Fase 4 |
| siae-requesting-review | 5 | Assegnazione reviewer PR | 🟡 MEDIO | Step 2 |
| siae-receiving-review | 6 | Push aggiornamento branch | 🔴 ALTO | Step 3 |
| siae-verification | 7 | Esecuzione test/build/lint | 🟡 MEDIO | Step 2 ESEGUI |
| siae-writing-plans | 8 | Git commit piano | 🟡 MEDIO | Step 4 |
| siae-executing-plans | 9 | Implementazione task batch | 🟡 MEDIO | Step 2 |
| siae-parallel-agents | 10 | Dispatch agenti paralleli | 🟡 MEDIO | Step 3 |
| siae-parallel-agents | 11 | Integrazione output | 🔴 ALTO | Step 4 |
| siae-codebase-map | 12 | Scrittura CODEBASE_MAP.md | 🟡 MEDIO | Step 6 |
| siae-codebase-map | 13 | Aggiornamento CLAUDE.md | 🟡 MEDIO | Step 7 |
| siae-security | 14 | Rotazione credenziali / Secrets Manager | 🚨 CRITICO | Nuova sezione |
| siae-iac | 15 | `terraform apply` | 🚨 CRITICO | Step apply |
| siae-iac | 16 | Modifica IAM policy | 🚨 CRITICO | Inline su risorse IAM |
| siae-data-engineering | 17 | Deploy Glue job via terraform | 🚨 CRITICO | Sezione deploy |
| siae-data-engineering | 18 | Cancellazione dati S3 | 🚨 CRITICO | Sezione data operations |
| siae-data-engineering | 19 | Modifica schema Glue Catalog | 🔴 ALTO | Sezione schema |
| siae-data-engineering | 20 | `aws glue start-job-run` manuale | 🔴 ALTO | Sezione esecuzione |

---

## Card JSON per Gap

### 3.1 — siae-git-worktrees

**Gap #1 — `git worktree remove --force`** (🔴 ALTO)

```json
{
  "level": "ALTO",
  "skill": "siae-git-worktrees",
  "context": [
    {"emoji": "📁", "label": "Worktree", "value": "<path worktree>"},
    {"emoji": "🌿", "label": "Branch", "value": "<branch-name>"}
  ],
  "actions": [
    {"emoji": "🗑️", "label": "Rimozione forzata worktree (file non committati persi)", "path": "<path worktree>"}
  ],
  "reason": "Worktree non rimovibile normalmente (file non committati presenti)",
  "ifno": "Il worktree resta attivo, commit o stash prima di rimuovere"
}
```

**Gap #2 — `git rebase -i` su branch condiviso** (🚨 CRITICO)

```json
{
  "level": "CRITICO",
  "skill": "siae-git-worktrees",
  "context": [
    {"emoji": "🌿", "label": "Branch", "value": "<branch-name>"},
    {"emoji": "🎯", "label": "Target rebase", "value": "<base-branch>"},
    {"emoji": "👥", "label": "Condiviso", "value": "Si — altri developer usano questo branch"}
  ],
  "actions": [
    {"emoji": "⚠️", "label": "Rebase interattivo su branch condiviso (riscrive history)", "path": "<branch-name>"}
  ],
  "reason": "Rebase necessario per allineare al branch base",
  "ifno": "STOP — usa merge invece di rebase su branch condivisi"
}
```

### 3.2 — siae-git-workflow

**Gap #3 — Rollback tag PRODUZIONE** (🚨 CRITICO)

```json
{
  "level": "CRITICO",
  "skill": "siae-git-workflow",
  "context": [
    {"emoji": "🏷️", "label": "Tag da eliminare", "value": "<tag-name>"},
    {"emoji": "🌍", "label": "Ambiente", "value": "PRODUZIONE"},
    {"emoji": "📝", "label": "Commit stabile", "value": "<commit-hash>"}
  ],
  "actions": [
    {"emoji": "⚠️", "label": "Cancellazione tag remoto (trigga rollback deploy)", "path": "origin/refs/tags/<tag-name>"}
  ],
  "reason": "Rollback necessario per incident/bug critico in produzione",
  "ifno": "Il tag resta, nessun rollback — il deploy corrente rimane attivo"
}
```

### 3.3 — siae-debugging

**Gap #4 — Fase 4 Implementation** (🟡 MEDIO)

```json
{
  "level": "MEDIO",
  "skill": "siae-debugging",
  "context": [
    {"emoji": "🔑", "label": "Root cause", "value": "<descrizione root cause identificata>"},
    {"emoji": "📊", "label": "Ipotesi", "value": "Confermata in Fase 3"}
  ],
  "actions": [
    {"emoji": "🧪", "label": "Scrivi test di regressione + fix minimale", "path": "<file target>"}
  ],
  "reason": "Root cause confermata, fix minimale pronto",
  "ifno": "Nessun fix applicato, torna a Fase 3 per nuova ipotesi"
}
```

### 3.4 — siae-requesting-review

**Gap #5 — Assegnazione reviewer** (🟡 MEDIO)

```json
{
  "level": "MEDIO",
  "skill": "siae-requesting-review",
  "context": [
    {"emoji": "🌿", "label": "Branch", "value": "<branch-name>"},
    {"emoji": "🎯", "label": "Target", "value": "sviluppo"},
    {"emoji": "📝", "label": "Commit", "value": "<N> commit"}
  ],
  "actions": [
    {"emoji": "🚀", "label": "Assegnazione reviewer alla PR", "path": "PR #<number>"}
  ],
  "reason": "PR pronta, reviewer da assegnare",
  "ifno": "La PR resta senza reviewer assegnato"
}
```

### 3.5 — siae-receiving-review

**Gap #6 — Push aggiornamento branch** (🔴 ALTO)

```json
{
  "level": "ALTO",
  "skill": "siae-receiving-review",
  "context": [
    {"emoji": "🌿", "label": "Branch", "value": "<branch-name>"},
    {"emoji": "📝", "label": "Fix applicati", "value": "<N> REQUIRED, <M> SUGGESTION"},
    {"emoji": "🧪", "label": "Test suite", "value": "<risultato test>"}
  ],
  "actions": [
    {"emoji": "🚀", "label": "Push fix al branch della PR", "path": "origin/<branch-name>"}
  ],
  "reason": "Fix review completati, test verdi, pronto per re-review",
  "ifno": "I fix restano locali, il reviewer non vede le modifiche"
}
```

### 3.6 — siae-verification

**Gap #7 — Esecuzione test/build/lint** (🟡 MEDIO)

```json
{
  "level": "MEDIO",
  "skill": "siae-verification",
  "context": [
    {"emoji": "🔧", "label": "Comandi", "value": "<lista comandi identificati in Step 1>"},
    {"emoji": "📁", "label": "Working dir", "value": "<directory>"}
  ],
  "actions": [
    {"emoji": "🧪", "label": "Esecuzione suite di verifica", "path": "<comandi>"}
  ],
  "reason": "Verifica necessaria prima di qualsiasi claim di completamento",
  "ifno": "Nessuna verifica eseguita — non puoi dichiarare completamento"
}
```

### 3.7 — siae-writing-plans

**Gap #8 — Git commit piano** (🟡 MEDIO)

```json
{
  "level": "MEDIO",
  "skill": "siae-writing-plans",
  "context": [
    {"emoji": "📋", "label": "Piano", "value": "<filename>.md"},
    {"emoji": "🔢", "label": "Task", "value": "<N> task definiti"}
  ],
  "actions": [
    {"emoji": "📌", "label": "Commit piano implementativo", "path": "docs/plans/<filename>.md"}
  ],
  "reason": "Piano validato, pronto per commit",
  "ifno": "Il piano resta non committato"
}
```

### 3.8 — siae-executing-plans

**Gap #9 — Implementazione task batch** (🟡 MEDIO)

```json
{
  "level": "MEDIO",
  "skill": "siae-executing-plans",
  "context": [
    {"emoji": "📋", "label": "Piano", "value": "<filename>.md"},
    {"emoji": "🔢", "label": "Batch", "value": "Task <N>-<M> di <totale>"}
  ],
  "actions": [
    {"emoji": "✏️", "label": "Implementazione batch con TDD", "path": "<file coinvolti>"}
  ],
  "reason": "Batch pronto, piano validato",
  "ifno": "Il batch non viene eseguito, attende feedback"
}
```

### 3.9 — siae-parallel-agents

**Gap #10 — Dispatch agenti paralleli** (🟡 MEDIO)

```json
{
  "level": "MEDIO",
  "skill": "siae-parallel-agents",
  "context": [
    {"emoji": "🤖", "label": "Agenti", "value": "<N> agenti paralleli"},
    {"emoji": "🔢", "label": "Domini", "value": "<lista domini>"}
  ],
  "actions": [
    {"emoji": "⚡", "label": "Dispatch agenti in parallelo", "path": "<scope per agente>"}
  ],
  "reason": "Task indipendenti confermati, nessuno stato condiviso",
  "ifno": "Dispatch annullato, esecuzione sequenziale"
}
```

**Gap #11 — Integrazione output** (🔴 ALTO)

```json
{
  "level": "ALTO",
  "skill": "siae-parallel-agents",
  "context": [
    {"emoji": "🤖", "label": "Agenti completati", "value": "<N>/<N>"},
    {"emoji": "📁", "label": "File modificati", "value": "<lista file>"}
  ],
  "actions": [
    {"emoji": "🔀", "label": "Integrazione output agenti + risoluzione conflitti", "path": "<file coinvolti>"}
  ],
  "reason": "Tutti gli agenti completati, integrazione necessaria",
  "ifno": "Output agenti non integrati, verifiche manuali necessarie"
}
```

### 3.10 — siae-codebase-map

**Gap #12 — Scrittura CODEBASE_MAP.md** (🟡 MEDIO)

```json
{
  "level": "MEDIO",
  "skill": "siae-codebase-map",
  "context": [
    {"emoji": "📊", "label": "File analizzati", "value": "<N> file, <N> token"},
    {"emoji": "🤖", "label": "Subagent", "value": "<N> report sintetizzati"}
  ],
  "actions": [
    {"emoji": "✏️", "label": "Scrittura mappa codebase", "path": "docs/CODEBASE_MAP.md"}
  ],
  "reason": "Analisi completa, mappa pronta per scrittura",
  "ifno": "La mappa non viene scritta, analisi disponibile solo in chat"
}
```

**Gap #13 — Aggiornamento CLAUDE.md** (🟡 MEDIO)

```json
{
  "level": "MEDIO",
  "skill": "siae-codebase-map",
  "context": [
    {"emoji": "📋", "label": "Sezione", "value": "Architettura Codebase"},
    {"emoji": "🔄", "label": "Tipo", "value": "<nuovo | aggiornamento>"}
  ],
  "actions": [
    {"emoji": "📝", "label": "Aggiornamento sezione architettura", "path": "CLAUDE.md"}
  ],
  "reason": "Mappa aggiornata, CLAUDE.md da sincronizzare",
  "ifno": "CLAUDE.md non aggiornato, future sessioni usano info vecchie"
}
```

### 3.11 — siae-security

**Gap #14 — Rotazione credenziali** (🚨 CRITICO)

```json
{
  "level": "CRITICO",
  "skill": "siae-security",
  "context": [
    {"emoji": "🔐", "label": "Secret", "value": "<secret-name>"},
    {"emoji": "🌍", "label": "Ambiente", "value": "<dev|collaudo|produzione>"},
    {"emoji": "📦", "label": "Servizi dipendenti", "value": "<lista servizi>"}
  ],
  "actions": [
    {"emoji": "⚠️", "label": "Rotazione credenziale / aggiornamento secret", "path": "aws secretsmanager update-secret --secret-id <id>"}
  ],
  "reason": "Secret scaduto/compromesso, rotazione necessaria",
  "ifno": "STOP — il secret resta invariato, valuta rischio manuale"
}
```

### 3.12 — siae-iac

**Gap #15 — `terraform apply`** (🚨 CRITICO)

```json
{
  "level": "CRITICO",
  "skill": "siae-iac",
  "context": [
    {"emoji": "🏗️", "label": "Ambiente", "value": "<dev|collaudo|produzione>"},
    {"emoji": "📋", "label": "Plan output", "value": "<N> to add, <N> to change, <N> to destroy"},
    {"emoji": "🎫", "label": "Ticket", "value": "<PROJ-NNN>"}
  ],
  "actions": [
    {"emoji": "⚠️", "label": "Applicazione modifiche infrastruttura AWS", "path": "<modulo terraform>"}
  ],
  "reason": "Plan verificato, risorse da creare/modificare",
  "ifno": "STOP — nessuna modifica applicata all'infrastruttura"
}
```

**Gap #16 — Modifica IAM policy** (🚨 CRITICO)

```json
{
  "level": "CRITICO",
  "skill": "siae-iac",
  "context": [
    {"emoji": "🔐", "label": "Risorsa IAM", "value": "<role/policy name>"},
    {"emoji": "🌍", "label": "Ambiente", "value": "<ambiente>"},
    {"emoji": "📦", "label": "Servizi impattati", "value": "<lista servizi>"}
  ],
  "actions": [
    {"emoji": "⚠️", "label": "Modifica policy IAM (impatta accesso risorse)", "path": "<file .tf>"}
  ],
  "reason": "Modifica necessaria per <motivazione>",
  "ifno": "STOP — policy invariata, accessi non modificati"
}
```

### 3.13 — siae-data-engineering

**Gap #17 — Deploy Glue job** (🚨 CRITICO)

```json
{
  "level": "CRITICO",
  "skill": "siae-data-engineering",
  "context": [
    {"emoji": "🏗️", "label": "Ambiente", "value": "<ambiente>"},
    {"emoji": "📋", "label": "Job", "value": "<job-name>"},
    {"emoji": "🔄", "label": "Layer", "value": "<bronze|silver|gold>"}
  ],
  "actions": [
    {"emoji": "⚠️", "label": "Deploy Glue job via terraform apply", "path": "<modulo terraform>"}
  ],
  "reason": "Job aggiornato, test locali verdi",
  "ifno": "STOP — job non deployato, versione precedente resta attiva"
}
```

**Gap #18 — Cancellazione dati S3** (🚨 CRITICO)

```json
{
  "level": "CRITICO",
  "skill": "siae-data-engineering",
  "context": [
    {"emoji": "🗄️", "label": "Bucket", "value": "<bucket-name>"},
    {"emoji": "📁", "label": "Prefix", "value": "<s3-prefix>"},
    {"emoji": "📊", "label": "File coinvolti", "value": "<N> file, <size>"}
  ],
  "actions": [
    {"emoji": "🗑️", "label": "Cancellazione dati S3 (irreversibile senza backup)", "path": "s3://<bucket>/<prefix>"}
  ],
  "reason": "Dati obsoleti/corrotti da rimuovere",
  "ifno": "STOP — dati preservati, nessuna cancellazione"
}
```

**Gap #19 — Modifica schema Glue Catalog** (🔴 ALTO)

```json
{
  "level": "ALTO",
  "skill": "siae-data-engineering",
  "context": [
    {"emoji": "🗄️", "label": "Database", "value": "<glue-database>"},
    {"emoji": "🔧", "label": "Tabella", "value": "<table-name>"},
    {"emoji": "📦", "label": "Downstream", "value": "<query/job dipendenti>"}
  ],
  "actions": [
    {"emoji": "🔧", "label": "Modifica schema Glue Catalog (backward compatibility)", "path": "<file schema/terraform>"}
  ],
  "reason": "Schema da aggiornare per nuovi requisiti dati",
  "ifno": "Schema invariato, downstream non impattati"
}
```

**Gap #20 — `aws glue start-job-run` manuale** (🔴 ALTO)

```json
{
  "level": "ALTO",
  "skill": "siae-data-engineering",
  "context": [
    {"emoji": "📋", "label": "Job", "value": "<job-name>"},
    {"emoji": "🏗️", "label": "Ambiente", "value": "<ambiente>"},
    {"emoji": "🔧", "label": "Parametri", "value": "<parametri input>"}
  ],
  "actions": [
    {"emoji": "🖥️", "label": "Esecuzione manuale Glue job (consuma risorse, scrive S3)", "path": "aws glue start-job-run --job-name <name>"}
  ],
  "reason": "Esecuzione manuale necessaria per <motivazione>",
  "ifno": "Job non eseguito, nessun dato processato"
}
```

---

## Trade-off Scelti

| Decisione | Alternativa scartata | Motivazione |
|-----------|---------------------|-------------|
| Card inline nelle skill | Card Registry centralizzato | YAGNI — le card hanno contesto diverso per skill |
| Card inline nelle skill | Card Middleware automatico | Le skill sono prompt Markdown, non codice eseguibile |
| Aggiunta colonna "Card" nelle tabelle rischio | Nessuna modifica tabella | Rende esplicito quali operazioni hanno card |
| Nuova sezione in siae-security per operazioni attive | Solo checklist passiva | La skill deve coprire anche rotazione credenziali |
| generate-card.py invariato | Estensione con --from-registry | Nessuna feature nuova necessaria |

---

## Criteri di Accettazione

- [ ] Tutte le 20 operazioni hanno blocco `generate-card.py` inline nello step corretto
- [ ] Ogni skill modificata ha colonna "Card" nella tabella Classificazione Rischio
- [ ] Le 3 skill senza tabella di classificazione la ottengono
- [ ] Nessuna card costruita a mano
- [ ] Livelli rischio coerenti con `devforge-visual.md` sezione 0.2
- [ ] Skill non modificate restano intatte
- [ ] `generate-card.py` non viene modificato
