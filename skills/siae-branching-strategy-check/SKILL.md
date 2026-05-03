---
name: siae-branching-strategy-check
description: >
  Use when checking SIAE branching strategy compliance across PRs in itsiae
  org, the current repo, or repos selected by GitHub topic. Verifica compliance
  alla branching strategy SIAE: default branch deve essere main, solo
  release/** apre PR verso main. Trigger: "branching check",
  "/branching-strategy-check", "PR verso main", "verifica branching strategy",
  "violazioni branching", "default branch errato", "release branch".
---

# Branching Strategy Check — DevForge

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║              🔨 DevForge · BRANCHING STRATEGY CHECK            ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 6. QA Gate

---

## Quando si Applica

**Sempre:**
- Check automatico all'avvio sessione (via hook session-start) sul repo corrente
- Invocazione manuale per verifica compliance PR in review
- Prima di approvare PR nell'org itsiae
- Quando si clona o si inizia a lavorare su un repo nuovo

**Eccezioni:**
- Repository senza remote GitHub (solo local)
- `gh auth status` non OK — comunicare e terminare

---

## Istruzioni

### Step 1 — Check repo corrente

🟢 SICURO

Identifica il repo corrente ed esegui i due controlli base.

```bash
gh repo view --json nameWithOwner -q '.nameWithOwner'
```

Se il comando fallisce (non sei in un repo con remote GitHub), comunicalo e passa allo Step 2.

**Controllo A — Default branch:**

```bash
gh repo view --json defaultBranchRef -q '.defaultBranchRef.name'
```

- Deve essere `main`. Se diverso: **VIOLATION**.

**Controllo B — PR verso main da branch non-release:**

Eseguito **indipendentemente** dal risultato del Controllo A.

```bash
gh pr list --base main --state open --json number,title,headRefName,url
```

Per ogni PR:
- `headRefName` matcha `release/**` → **COMPLIANT**
- `headRefName` NON matcha `release/**` → **VIOLATION**

### Step 2 — PR in review nell'org itsiae

🟢 SICURO

```bash
gh search prs --review-requested=@me --state=open --owner=itsiae --json repository,number,title,url
```

Se non ci sono PR in review, comunicalo e passa allo Step 3.

Per ogni PR trovata, recupera i branch:

```bash
gh pr view {number} --repo {owner/repo} --json headRefName,baseRefName -q '"\(.headRefName)\t\(.baseRefName)"'
```

Per ogni repository **unico** (escludendo il repo gia' verificato nello Step 1):

**Controllo A — Default branch** (come Step 1).

**Controllo B — PR verso main:**
- PR con `baseRefName` = `main` e `headRefName` non matcha `release/**` → **VIOLATION**
- PR che non puntano a `main` → **NON SOGGETTE** (riportate separatamente)

### Step 3 — Report Fasi 1+2

🟢 SICURO

Genera il report seguendo il formato in "Template Report" piu' sotto.
La colonna Fonte distingue `corrente` vs `review`.

Dopo il report, proponi l'espansione per topic (Step 4).

### Step 4 — Espansione per topic GitHub (opzionale)

🟢 SICURO

Chiedi: **"Vuoi eseguire la ricerca espansa sui repository correlati per topic?"**

Se **No** → la skill termina.

Se **Si'**:

Raccogli i topic dei repository unici dalla Fase 2:

```bash
gh repo view {owner/repo} --json repositoryTopics -q '[.repositoryTopics[].name] | join(",")'
```

Mostra la lista topic e chiedi su quali espandere:
- **Cerca su tutti** — prima opzione
- Ogni topic come opzione singola (selezione multipla)

Per ogni topic selezionato:

```bash
gh search repos --owner=itsiae --topic={topic} --json fullName -q '.[].fullName'
```

Elimina duplicati e repository gia' verificati. Applica Controlli A e B sui nuovi repository.

Aggiorna il report. La colonna Fonte sara' `topic: {nome}`.

---

## Template Report

Le violazioni hanno sempre la massima priorita' visiva.

```
## Branching Strategy Compliance Report

Data: {data corrente}
Repo corrente: {owner/repo}
PR in review: {count}
Repository da espansione topic: {count, solo se Step 4 eseguito}
Repository totali analizzati: {count}

### Sommario

- **{count} VIOLAZIONI**
- {count} PR/repo compliant
- {count} PR non soggette (target != main)

---

### VIOLAZIONI

#### Default branch non main

| Repository | Default Branch | Fonte |
|---|---|---|
| {owner/repo} | `{nome}` (atteso: `main`) | corrente / review / topic: {t} |

Se non ci sono violazioni di questo tipo, ometti la sezione.

#### PR verso main da branch non-release

| Repository | PR | Branch | Target | Fonte |
|---|---|---|---|---|
| {owner/repo} | #{n} | `{headRefName}` | main | corrente / review / topic: {t} |

Se non ci sono violazioni di questo tipo, ometti la sezione.

---

### PR compliant

| Repository | PR | Branch | Target |
|---|---|---|---|
| {owner/repo} | #{n} | `release/x.y.z` | main |

### PR non soggette

PR che non puntano a `main`. Non in violazione, riportate per completezza.

| Repository | PR | Branch | Target |
|---|---|---|---|
| {owner/repo} | #{n} | `feature/xyz` | release/x.y.z |
```

Se zero violazioni:

```
✅ Tutti i repository analizzati sono compliant con la branching strategy SIAE.
```

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura stato repo e PR via `gh` | 🟢 Sicuro | No |
| Generazione report compliance | 🟢 Sicuro | No |
| Espansione per topic (query org-wide) | 🟢 Sicuro | No |

---

## Vincoli

1. **NON** inventare dati — ogni violazione deve venire da output `gh` reale
2. **NON** modificare branch, PR o impostazioni del repository — skill read-only
3. **SEMPRE** eseguire Controllo A e B indipendentemente l'uno dall'altro
4. **SEMPRE** classificare le PR non soggette separatamente (target != main)
5. **SEMPRE** distinguere la Fonte nel report (corrente / review / topic)

---

## Risorse Aggiuntive

- [reference/branching-strategy.md](reference/branching-strategy.md) — Regole complete della branching strategy SIAE
