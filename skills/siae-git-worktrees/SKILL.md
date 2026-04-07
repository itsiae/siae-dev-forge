---
name: siae-git-worktrees
description: >
  Configura workspace isolati con git worktree prima di implementazioni multi-file.
  Trigger: prima di eseguire un piano implementativo, setup workspace isolato,
  implementazione su branch separato, /forge-implement, inizio feature
  multi-commit, isola lavoro, worktree, branch dedicato per implementazione.
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

> 📊 **Dai repo itsiae:** Developer che usano worktree isolati hanno 0 conflitti da work-in-progress vs 23% con branch condivisi.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

```
REQUIRED SUB-SKILL: siae-git-env
```
Invoca `siae-git-env` PRIMA di creare worktree, per verificare che git e gh siano disponibili.

## LA LEGGE DI FERRO

```
NON INIZIARE MAI L'IMPLEMENTAZIONE NEL BRANCH CORRENTE
```

**Violare la lettera di questa regola significa violare lo spirito della regola.**

<EXTREMELY-IMPORTANT>
Stai per iniziare a scrivere codice nel branch corrente senza creare un worktree?
FERMATI. Crea il worktree prima. Il branch corrente deve restare pulito.

"E' una modifica piccola, non serve il worktree" = le modifiche piccole diventano grandi.
"Ho gia' il branch checkout, lavoro qui" = file parziali che inquinano il context.
</EXTREMELY-IMPORTANT>

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

### Step 3b — Sync DevForge Config

Dopo aver installato le dipendenze, sincronizza la configurazione DevForge
nel worktree tramite symlink. Senza questo step, l'agent nel worktree
non ha hook, settings, ne' CLAUDE.md.

```bash
cd .worktrees/{branch-name}

# Symlink .claude/ dal repo principale (hook, settings, CLAUDE.md)
MAIN_REPO=$(git worktree list | head -1 | awk '{print $1}')
[ -d "$MAIN_REPO/.claude" ] && ln -sfn "$MAIN_REPO/.claude" .claude

# Symlink CLAUDE.md root se esiste
[ -f "$MAIN_REPO/CLAUDE.md" ] && ln -sfn "$MAIN_REPO/CLAUDE.md" CLAUDE.md
```

**Se `.claude/` non esiste nel repo principale:** skip silenzioso — il repo
non usa DevForge hooks.

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
```

**⚠️ Operazione rischiosa — mostra pre-flight card PRIMA di eseguire:**

| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-git-worktrees |
|:---|
| **⚠️ OPERAZIONE DIFFICILE DA ANNULLARE** |
| 📁 Worktree: `<path worktree>` · 🌿 Branch: `<branch-name>` |
| **▼ Azione** |
| 1. 🗑️ Azione: Rimozione forzata worktree (file non committati persi) → `<path worktree>` |
| 💡 Perche': Worktree non rimovibile normalmente (file non committati presenti) |
| 🚫 Se NO: Il worktree resta attivo, commit o stash prima di rimuovere |

```bash
# Forza rimozione (se ci sono file non committati)
git worktree remove --force .worktrees/{branch-name}

# Prune worktree rimossi manualmente
git worktree prune
```

---

## Warning: Rebase su Branch Condivisi

🚨 CRITICO — Mostra pre-flight card OBBLIGATORIA prima di eseguire

Se stai per fare `git rebase` su un branch che altri developer usano, questa operazione riscrive la history e può corrompere il lavoro altrui.

<EXTREMELY-IMPORTANT>
NON eseguire rebase su branch condivisi senza mostrare la pre-flight card e ottenere
conferma esplicita dall'utente. Questa operazione riscrive la history ed e' IRREVERSIBILE
per gli altri developer che hanno gia' basato il loro lavoro su questo branch.
</EXTREMELY-IMPORTANT>

| 🚨 CRITICO (irreversibile) — 🔨 DevForge · siae-git-worktrees |
|:---|
| **⚠️ STOP — Rebase su branch condiviso riscrive history per tutti i developer** |
| 🌿 Branch: `<branch-name>` · 🎯 Target rebase: `<base-branch>` · 👥 Condiviso: `Si — altri developer usano questo branch` |
| **▼ Azione** |
| 1. ⚠️ Azione: Rebase interattivo su branch condiviso (riscrive history) → `<branch-name>` |
| 💡 Perche': Rebase necessario per allineare al branch base |
| 🚫 Se NO: STOP — usa merge invece di rebase su branch condivisi |

**Regola:** Se il branch è condiviso (altri developer ci lavorano), preferisci SEMPRE `git merge` a `git rebase`. Il rebase è sicuro solo su branch personali.

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

## Permission Denied Handling

**Step 1 (Seleziona directory) — parzialmente permission-free:**
- Check `.gitignore`: `Grep("\\.worktrees", ".gitignore")` — permission-free
- Se `.worktrees/` non e' nel `.gitignore`, fornisci i comandi per aggiungerla

**Step 2-4 (Crea worktree, setup, baseline test) — Bash richiesto:**
Se Bash viene negato, passa a modalita' guida manuale:
1. Presenta i comandi esatti in lista numerata
2. Indica lo stack rilevato e le dipendenze da installare
3. Fornisci il comando test per il baseline check
4. L'utente esegue nel suo terminale

**Esempio guida manuale:**
```
Non ho permessi per eseguire comandi. Ecco i passi:
1. `git worktree add .worktrees/feature-SDLC-142 feature/SDLC-142-add-login`
2. `cd .worktrees/feature-SDLC-142`
3. `npm install` (stack TS rilevato)
4. `npm test` (baseline check)
Conferma quando fatto.
```

**Fasi completabili senza permessi:** check `.gitignore` (Grep), analisi stack
**Fasi che richiedono permessi:** tutte le operazioni git worktree e setup (Bash)

Se i permessi sono negati:
1. Completa le verifiche read-only
2. Presenta tutti i comandi per esecuzione manuale
3. NON entrare in loop di retry su tool negato
4. NON dichiarare completamento per fasi non eseguite

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi fix per errore | 2 | Fermati. Diagnosi diversa necessaria. |
| Worktree attivi contemporaneamente | 3 | Se ne servono di piu', il workflow ha un problema di design. |
| Output max per raccomandazione | 200 righe | Prioritizza. Top 5 issue, non lista esaustiva. |

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

| Operazione | Rischio | Card |
|------------|---------|------|
| `git worktree list` | 🟢 Sicuro | No |
| `git worktree add` | 🟡 Medio | No |
| `git worktree remove` | 🟡 Medio | No |
| `git worktree remove --force` | 🔴 Alto | Si |
| `git rebase` su branch condiviso | 🚨 Critico | Si |
