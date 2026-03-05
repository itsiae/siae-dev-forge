---
name: siae-git-worktrees
description: >
  Trigger: prima di eseguire un piano implementativo, inizio feature,
  setup workspace isolato, implementazione su branch separato.
---

# SIAE Git Worktrees

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨  DevForge  ·  SIAE Git Worktrees                  ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 3. Branching (prima dell'implementazione)

---

## La Regola

```
NON INIZIARE MAI L'IMPLEMENTAZIONE NEL BRANCH CORRENTE
Crea sempre un worktree isolato prima di toccare qualsiasi file.
```

**Violare la lettera di questa regola significa violare lo spirito della regola.**

Lavorare nel branch principale durante lo sviluppo significa:
- File non committati che inquinano il context di Claude
- Impossibilita' di passare rapidamente a un altro task
- Rischio di committare lavoro parziale
- Nessun isolamento tra feature parallele

---

## Quando si Applica

**SEMPRE prima di:**
- Iniziare l'implementazione di un piano (dopo siae-brainstorming)
- Lavorare su una feature che richiede piu' di 1 commit
- Implementare task con `/forge-implement` (siae-subagent-development)
- Qualsiasi lavoro che modifica piu' di 3 file

**Non serve per:**
- Fix di un singolo file con 1 commit immediato
- Aggiornamenti di documentazione puri

---

## Setup Worktree

### Step 1 — Seleziona la Directory

Priorita' di scelta (in ordine):

1. `.worktrees/` — se esiste nella root del repo (verifica `.gitignore`)
2. `worktrees/` — se esiste
3. Path specificata in `CLAUDE.md` del progetto
4. Chiedi all'utente

**Safety gate obbligatorio:**

```bash
# Prima di creare la directory, verifica che sia ignorata da git
git check-ignore -v .worktrees/
# Se NON e' ignorata → aggiungila a .gitignore
echo ".worktrees/" >> .gitignore
git add .gitignore && git commit -m "chore: add .worktrees/ to .gitignore"
```

### Step 2 — Crea il Worktree

```bash
# Sintassi base
git worktree add .worktrees/{branch-name} {branch-name}

# Esempio SIAE: branch gia' esistente
git worktree add .worktrees/feature-SDLC-142 feature/SDLC-142-add-login

# Esempio SIAE: branch nuovo da sviluppo (branch base SIAE)
git worktree add -b feature/SDLC-142-add-login .worktrees/feature-SDLC-142 sviluppo
```

**Regola branch base SIAE:** usa sempre `sviluppo` come base, mai `main` o `master`.

### Step 3 — Auto-detect Setup

Dopo aver creato il worktree, rileva lo stack e installa le dipendenze:

```bash
cd .worktrees/{branch-name}

# Java / Maven
[ -f pom.xml ] && mvn dependency:resolve -q

# TypeScript (frontend o backend)
[ -f package.json ] && npm install --silent || yarn install --silent

# Python
[ -f requirements.txt ] && pip install -r requirements.txt -q
[ -f pyproject.toml ] && poetry install -q

# IaC — nessun setup necessario
```

### Step 4 — Baseline Test Check

```bash
# Esegui la suite test per verificare che il worktree sia integro
# Java
mvn test -q 2>&1 | tail -5

# TypeScript
npm test -- --passWithNoTests 2>&1 | tail -5

# Python
pytest --tb=no -q 2>&1 | tail -5
```

Se i test falliscono sul worktree appena creato → **STOP**. Riporta i fallimenti all'utente e chiedi consenso prima di procedere. I test erano gia' rotti prima del tuo lavoro.

---

## Comandi Utili

```bash
# Lista worktree attivi
git worktree list

# Rimuovi un worktree dopo il merge
git worktree remove .worktrees/{branch-name}

# Forza rimozione (se ci sono file non committati)
git worktree remove --force .worktrees/{branch-name}

# Prune worktree rimossi manualmente
git worktree prune
```

---

## Integrazione con il Workflow SIAE

```
siae-brainstorming      →  design approvato
       ↓
siae-git-workflow       →  crea feature/{JIRA-ID}-descrizione da sviluppo
       ↓
siae-git-worktrees      →  git worktree add + dipendenze + baseline test
       ↓
siae-tdd / implementazione nel worktree isolato
       ↓
siae-finishing-branch   →  review diff, PR verso sviluppo
       ↓
git worktree remove     →  cleanup
```

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "E' una modifica piccola, non serve il worktree" | Le modifiche piccole diventano grandi. Crea il worktree. |
| "Ho gia' il branch checkout, lavoro qui" | Il branch checkout inquina il contesto con file parziali. |
| "Il worktree e' lento da configurare" | E' piu' lento disambiguare file parziali dopo. |
| "Lavoro su un solo file" | Un file modificato non committato blocca il checkout. |
| "Il progetto non ha .worktrees/" | Crea la directory e aggiungila al .gitignore. 30 secondi. |

---

## Vincoli

1. **NON** iniziare l'implementazione senza aver completato il safety gate `.gitignore`
2. **NON** procedere se il baseline test fallisce senza consenso esplicito dell'utente
3. **NON** usare `main` o `master` come branch base — sempre `sviluppo`
4. **NON** committare dal worktree senza aver eseguito i test
5. Dopo il merge PR → `git worktree remove` obbligatorio (cleanup)

---

## Classificazione Rischio Operazioni

| Operazione | Rischio |
|------------|---------|
| `git worktree list` | 🟢 Sicuro |
| `git worktree add` | 🟡 Medio |
| `git worktree remove` | 🟡 Medio |
| `git worktree remove --force` | 🔴 Alto |
