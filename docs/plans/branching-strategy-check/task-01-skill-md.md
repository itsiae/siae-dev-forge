# Task 01 — Crea SKILL.md branching-strategy-check

**Stato:** [PENDING]
**File coinvolti:**
- `skills/branching-strategy-check/SKILL.md` (CREATE)

---

## Step 1 — Crea la directory e il file SKILL.md

Crea `skills/branching-strategy-check/SKILL.md` con il seguente contenuto completo:

```markdown
---
name: branching-strategy-check
description: >
  Verifica compliance org-wide alla branching strategy SIAE su tutti i repo itsiae.
  Default branch deve essere main. Solo release/** puo' aprire PR verso main.
  Trigger: "branching check", "compliance org", "/branching-strategy-check",
  "PR verso main", "verifica branching strategy", "violazioni branching",
  "default branch errato", "release branch".
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
sdlc_phase: "6. QA Gate"
skill_type: "Flexible"
---

# Branching Strategy Check

\`\`\`
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨 DevForge · BRANCHING STRATEGY CHECK              ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
\`\`\`

> **Tipo:** Flexible | **Fase SDLC:** 6. QA Gate

---

## Obiettivo

Verificare che tutti i repository dell'organizzazione `itsiae` rispettino la
branching strategy SIAE:
- Il branch di default di ogni repo deve essere `main`
- Solo branch `release/**` possono aprire PR verso `main`

## Prerequisiti

- `gh auth status` deve essere OK
- `jq` deve essere installato

## Istruzioni

### Fase 1 — Scan org-wide (sempre eseguita)

#### Step 1 — Recupera tutti i repo itsiae

\`\`\`bash
gh search repos --owner=itsiae --limit 100 --json fullName -q '[.[].fullName]'
\`\`\`

Se il comando non restituisce risultati o fallisce, comunica all'utente e termina.

#### Step 2 — Controllo A: Default branch

Per ogni repository:

\`\`\`bash
gh repo view {owner/repo} --json defaultBranchRef -q '.defaultBranchRef.name'
\`\`\`

- Il branch di default **deve** essere `main`
- Se diverso: **VIOLATION — Default branch is not main**

#### Step 3 — Controllo B: PR verso main da branch non-release

Per ogni repository con default branch `main`:

\`\`\`bash
gh pr list --repo {owner/repo} --base main --state open \
  --json number,title,headRefName,url
\`\`\`

Per ogni PR trovata:
- `headRefName` matcha `release/**` → **COMPLIANT**
- `headRefName` NON matcha `release/**` → **VIOLATION — PR #{n} from `{branch}` targets main without being a release branch**

#### Step 4 — Report Fase 1

Genera e mostra il report seguendo il formato nella sezione "Genera il report".

### Fase 2 — Espansione topic (opzionale)

Dopo aver mostrato il report della Fase 1, chiedi:

**"Vuoi eseguire la ricerca espansa sui repository correlati per topic?"**

Se **No**: la skill termina.

Se **Si'**:

#### Step 1 — Raccogli topic dei repo già analizzati

\`\`\`bash
gh repo view {owner/repo} --json repositoryTopics \
  -q '[.repositoryTopics[].name] | join(",")'
\`\`\`

#### Step 2 — Chiedi su quali topic espandere

Mostra la lista topic trovati. Le opzioni:
- **Cerca su tutti** (prima opzione)
- Ogni topic come opzione singola

#### Step 3 — Cerca repo aggiuntivi per topic

\`\`\`bash
gh search repos --owner=itsiae --topic={topic} --json fullName -q '.[].fullName'
\`\`\`

Unisci i risultati eliminando duplicati e repo già verificati nella Fase 1.

#### Step 4 — Controlli sui repo aggiuntivi

Applica Controllo A (default branch) e Controllo B (PR verso main) sugli stessi criteri.

#### Step 5 — Report Fase 2

Aggiungi i risultati al report. La colonna "Fonte" sarà `topic: {nome}`.

### Genera il report

\`\`\`
## Branching Strategy Compliance Report

Data: {data corrente}
Repository analizzati: {count}

### Sommario

- **{count} VIOLAZIONI**
- {count} repo compliant
- {count} PR non soggette (target != main)

---

### VIOLAZIONI

#### Default branch non main

| Repository | Default Branch |
|---|---|
| {owner/repo} | \`{nome}\` (atteso: \`main\`) |

Se non ci sono violazioni di questo tipo, ometti la sezione.

#### PR verso main da branch non-release

| Repository | PR | Branch | Fonte |
|---|---|---|---|
| {owner/repo} | #{n} | \`{headRefName}\` | org-wide |
| {owner/repo} | #{n} | \`{headRefName}\` | topic: {topic} |

Se non ci sono violazioni di questo tipo, ometti la sezione.

---

### Repository compliant

| Repository | Status |
|---|---|
| {owner/repo} | ✅ |

---
\`\`\`

Se non ci sono violazioni, mostra un messaggio positivo al posto della sezione violazioni:

\`\`\`
✅ Tutti i {count} repository itsiae sono compliant con la branching strategy SIAE.
\`\`\`

### Regole di classificazione

- **Compliant**: default branch `main` E nessuna PR aperta verso main da branch non-`release/**`
- **Non compliant**: default branch ≠ `main` OPPURE almeno una PR da branch non-release verso main

## Riferimenti

La branching strategy SIAE prevede:
1. Il branch di default di ogni repository deve essere `main`
2. Solo i branch `release/**` possono aprire pull request verso `main`
3. I branch `feature/**` e `hotfix/**` devono confluire nel branch `release/**`, mai in `main` direttamente
```

---

## Step 2 — Verifica file creato

```bash
ls -la "skills/branching-strategy-check/"
```

Output atteso: `SKILL.md` presente nella directory.

---

## Step 3 — Commit

```bash
git add skills/branching-strategy-check/SKILL.md
git commit -m "feat(skills): add branching-strategy-check skill for org-wide compliance"
```
