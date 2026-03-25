---
name: branching-strategy-check
description: >
  Verifica compliance alla branching strategy SIAE sul repo corrente (o nuovo/clonato).
  Default branch deve essere main. Solo release/** puo' aprire PR verso main.
  Trigger: "branching check", "/branching-strategy-check",
  "PR verso main", "verifica branching strategy", "violazioni branching",
  "default branch errato", "release branch", "ho clonato il repo", "nuovo repo".
sdlc_phase: "6. QA Gate"
skill_type: "Flexible"
---

# Branching Strategy Check

```
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
```

> **Tipo:** Flexible | **Fase SDLC:** 6. QA Gate

---

## Obiettivo

Verificare che il repository corrente rispetti la branching strategy SIAE:
- Il branch di default deve essere `main`
- Solo branch `release/**` possono aprire PR verso `main`

Il controllo si esegue automaticamente all'avvio di sessione su qualsiasi repo
clonato o nuovo. Puoi anche invocarlo manualmente in qualsiasi momento.

## Prerequisiti

- `gh auth status` deve essere OK
- Il working directory deve essere un repository git con remote `origin`

## Istruzioni

### Fase 1 — Check repo corrente (sempre eseguita)

#### Step 1 — Identifica il repo

```bash
gh repo view --json nameWithOwner -q '.nameWithOwner'
```

Se il comando fallisce (non sei in un repo con remote GitHub), comunica all'utente e termina.

#### Step 2 — Controllo A: Default branch

```bash
gh repo view --json defaultBranchRef -q '.defaultBranchRef.name'
```

- Il branch di default **deve** essere `main`
- Se diverso: **VIOLATION — Default branch is not main**

#### Step 3 — Controllo B: PR verso main da branch non-release

```bash
gh pr list --base main --state open --json number,title,headRefName,url
```

Per ogni PR trovata:
- `headRefName` matcha `release/**` → **COMPLIANT**
- `headRefName` NON matcha `release/**` → **VIOLATION — PR #{n} from `{branch}` targets main without being a release branch**

#### Step 4 — Report Fase 1

Genera e mostra il report seguendo il formato nella sezione "Genera il report".

### Fase 2 — Espansione org-wide (opzionale)

Dopo aver mostrato il report della Fase 1, chiedi:

**"Vuoi estendere il controllo a tutti i repo itsiae?"**

Se **No**: la skill termina.

Se **Si'**:

#### Step 1 — Recupera tutti i repo itsiae

```bash
gh search repos --owner=itsiae --limit 100 --json fullName -q '[.[].fullName]'
```

#### Step 2 — Applica i controlli A e B su ogni repo

Per ogni repository (escludendo quello già verificato nella Fase 1):

```bash
gh repo view {owner/repo} --json defaultBranchRef -q '.defaultBranchRef.name'
gh pr list --repo {owner/repo} --base main --state open --json number,title,headRefName,url
```

#### Step 3 — Report Fase 2

Aggiungi i risultati al report. La colonna "Fonte" sarà `org-wide`.

### Genera il report

```
## Branching Strategy Compliance Report

Data: {data corrente}
Repository analizzati: {count}

### Sommario

- **{count} VIOLAZIONI**
- {count} repo compliant

---

### VIOLAZIONI

#### Default branch non main

| Repository | Default Branch |
|---|---|
| {owner/repo} | `{nome}` (atteso: `main`) |

Se non ci sono violazioni di questo tipo, ometti la sezione.

#### PR verso main da branch non-release

| Repository | PR | Branch | Fonte |
|---|---|---|---|
| {owner/repo} | #{n} | `{headRefName}` | corrente |
| {owner/repo} | #{n} | `{headRefName}` | org-wide |

Se non ci sono violazioni di questo tipo, ometti la sezione.

---

### Repository compliant

| Repository | Status |
|---|---|
| {owner/repo} | ✅ |

---
```

Se non ci sono violazioni, mostra un messaggio positivo:

```
✅ {owner/repo} è compliant con la branching strategy SIAE.
```

### Regole di classificazione

- **Compliant**: default branch `main` E nessuna PR aperta verso main da branch non-`release/**`
- **Non compliant**: default branch ≠ `main` OPPURE almeno una PR da branch non-release verso main

## Riferimenti

La branching strategy SIAE prevede:
1. Il branch di default di ogni repository deve essere `main`
2. Solo i branch `release/**` possono aprire pull request verso `main`
3. I branch `feature/**` e `hotfix/**` devono confluire nel branch `release/**`, mai in `main` direttamente
