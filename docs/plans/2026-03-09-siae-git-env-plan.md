# siae-git-env — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-executing-plans`
> per implementare questo piano task per task.

**Goal:** Creare la micro-skill `siae-git-env` per la detection di GitHub CLI,
e aggiornare le skill git che hanno operazioni GitHub-native per invocarla come Step 0.

**Architettura:** Nuova skill di utility (`skills/siae-git-env/SKILL.md`) invocata
come `REQUIRED SUB-SKILL` all'inizio di `siae-git-workflow` e `siae-finishing-branch`.
Stabilisce `GH_MODE` (gh disponibile) o `FALLBACK_MODE` (gh assente) per la sessione.

**Stack:** Markdown (SKILL.md), Bash (`gh --version`, `gh auth status`)

**SP:** 3

---

## Task 1: Crea `skills/siae-git-env/SKILL.md` [DONE]

**File coinvolti:**
- Crea: `skills/siae-git-env/SKILL.md`

**Step 1: Verifica che la directory non esiste già**

```bash
ls skills/ | grep git-env
```
Output atteso: nessun output (directory non esiste)

**Step 2: Crea la skill**

Crea `skills/siae-git-env/SKILL.md` con il contenuto seguente:

````markdown
---
name: siae-git-env
description: >
  Micro-skill di utility per la detection di GitHub CLI (gh).
  Trigger: REQUIRED SUB-SKILL da siae-git-workflow e siae-finishing-branch.
  Stabilisce GH_MODE o FALLBACK_MODE per la sessione corrente.
---

# siae-git-env — GitHub CLI Environment Check

`╔══ 🔨 DevForge — SIAE GIT ENV ══╗`

> **Tipo:** Rigid | **Fase SDLC:** 3. Branching (prerequisito)

---

## Scopo

Verifica se GitHub CLI (`gh`) è installata e autenticata nel sistema locale.
Imposta il modo operativo per la sessione:

- **GH_MODE** — `gh` disponibile: usa `gh` per tutte le operazioni GitHub-native
- **FALLBACK_MODE** — `gh` non disponibile: usa alternative complete (template, URL, API REST)

---

## Check da Eseguire

### Step 1 — Verifica installazione gh

```bash
gh --version 2>/dev/null
```

- Output con versione → `gh` installato, procedi a Step 2
- Nessun output / errore → `gh` non installato → **FALLBACK_MODE** (vai a Sezione Fallback)

### Step 2 — Verifica autenticazione gh

```bash
gh auth status 2>&1
```

- Contiene `Logged in to github.com` → `gh` autenticato → **GH_MODE**
- Contiene `not logged` / errore → `gh` installato ma non autenticato → **FALLBACK_MODE**

---

## Output — Blocco GIT_ENV CONTEXT

Dopo i check, mostra sempre questo blocco all'utente:

**Se GH_MODE:**
```
GIT_ENV CONTEXT
───────────────
gh CLI:    ✅ disponibile e autenticata
GH_MODE:   NATIVE — uso gh per operazioni GitHub
```

**Se FALLBACK_MODE (non installata):**
```
GIT_ENV CONTEXT
───────────────
gh CLI:    ❌ non installata
GH_MODE:   FALLBACK — uso alternative (template, URL browser, API REST)
Installa:  https://cli.github.com
```

**Se FALLBACK_MODE (non autenticata):**
```
GIT_ENV CONTEXT
───────────────
gh CLI:    ⚠️  installata ma non autenticata
GH_MODE:   FALLBACK — esegui `gh auth login` per abilitare GH_MODE
```

---

## GH_MODE — Operazioni con gh

| Operazione | Comando |
|---|---|
| Apri PR | `gh pr create --base sviluppo --title "..." --body "..."` |
| Vedi PR aperte | `gh pr list` |
| Dettagli PR | `gh pr view <numero>` |
| Stato review | `gh pr status` |
| Merge PR | `gh pr merge <numero> --squash` |

---

## FALLBACK_MODE — Alternative Complete

In FALLBACK_MODE nessuna operazione viene omessa. Ogni operazione GitHub-native
ha un'alternativa funzionante:

| Operazione | Alternativa FALLBACK |
|---|---|
| Apri PR | Template markdown completo in chat + URL: `https://github.com/<owner>/<repo>/compare/<branch>` |
| Vedi PR aperte | `git log --oneline origin/sviluppo..HEAD` + URL: `https://github.com/<owner>/<repo>/pulls` |
| Dettagli PR | URL: `https://github.com/<owner>/<repo>/pull/<numero>` |
| Stato review | URL: `https://github.com/<owner>/<repo>/pulls?q=is:open+review-requested` |
| Merge PR | Istruzioni UI: apri la PR su GitHub → pulsante "Squash and merge" |

---

## Propagazione nella Sessione

Il GH_MODE determinato da questa skill vale per tutta la sessione.
Le skill downstream (`siae-git-workflow`, `siae-finishing-branch`) lo usano
senza ri-eseguire il check.

---

## Classificazione Rischio

| Operazione | Rischio | Card |
|---|---|---|
| `gh --version` | 🟢 Sicuro | No |
| `gh auth status` | 🟢 Sicuro | No |
````

**Step 3: Verifica contenuto**

```bash
head -5 skills/siae-git-env/SKILL.md
```
Output atteso: le prime righe del frontmatter YAML (`---`, `name: siae-git-env`, ...)

**Step 4: Commit**

```bash
git add skills/siae-git-env/SKILL.md
git commit -m "feat(skills): add siae-git-env github cli detection utility skill"
```
Output atteso: `[feature/... <sha>] feat(skills): add siae-git-env...`

---

## Task 2: Aggiorna `siae-git-workflow` — Step 0 [DONE]

**File coinvolti:**
- Modifica: `skills/siae-git-workflow/SKILL.md`

**Step 1: Identifica il punto di inserimento**

Leggi `skills/siae-git-workflow/SKILL.md`. Il blocco `## LA LEGGE DI FERRO` è subito dopo
l'header della skill. Inserisci il nuovo Step 0 prima della sezione `## 1. Branch Strategy SIAE`.

**Step 2: Aggiungi Step 0**

Inserisci il seguente blocco tra `## Permission Denied Handling` e `## 1. Branch Strategy SIAE`:

````markdown
## 0. Environment Check — GitHub CLI

```
REQUIRED SUB-SKILL: siae-git-env
```

Esegui `siae-git-env` prima di qualsiasi operazione git che coinvolge GitHub.
Il `GH_MODE` determinato qui vale per tutta la sessione.

**Non ripetere il check nella stessa sessione.** Se `siae-git-env` è già stata eseguita,
usa il GH_MODE già determinato.
````

Inseriscilo **dopo** il blocco `## LA LEGGE DI FERRO` e **prima** di `## 1. Branch Strategy SIAE`.

**Step 3: Aggiorna la sezione Promozione ambiente con comportamento condizionale**

Nella sezione `## 8. Flusso Operativo` → `### Promozione ambiente`, aggiungi dopo i comandi `git`:

````markdown
**Apertura PR (se necessaria):**

**Se GH_MODE:**
```bash
gh pr create --base sviluppo --title "release: promozione <da> → <a>" --body "Promozione ambiente"
```

**Se FALLBACK_MODE:**
Apri manualmente: `https://github.com/<owner>/<repo>/compare/<branch-target>...<branch-source>`
````

**Step 4: Verifica che la skill sia ancora parsabile**

```bash
head -20 skills/siae-git-workflow/SKILL.md
```
Output atteso: frontmatter YAML + header skill intatto

**Step 5: Commit**

```bash
git add skills/siae-git-workflow/SKILL.md
git commit -m "feat(skills): add step 0 siae-git-env to siae-git-workflow"
```

---

## Task 3: Aggiorna `siae-finishing-branch` — Step 0 + Step 5 condizionale [DONE]

**File coinvolti:**
- Modifica: `skills/siae-finishing-branch/SKILL.md`

**Step 1: Aggiungi Step 0 prima di "Processo in 5 Step"**

Inserisci il seguente blocco subito prima di `## Processo in 5 Step`:

````markdown
## 0. Environment Check — GitHub CLI

```
REQUIRED SUB-SKILL: siae-git-env
```

Esegui `siae-git-env` prima di procedere. Il GH_MODE determina i comandi
usati in Step 5 (apertura PR). Se già eseguita nella sessione, usa il contesto esistente.
````

**Step 2: Aggiorna Step 5 con comportamento condizionale**

Nella sezione `### Step 5 — Apri la Pull Request`, sostituisci il blocco bash con:

````markdown
**Dopo la conferma:**

**Se GH_MODE:**

```bash
# Push del branch
git push origin feature/{JIRA-ID}-descrizione

# Apri PR via GitHub CLI
gh pr create \
  --base sviluppo \
  --title "feat({scope}): descrizione [JIRA-ID]" \
  --body "$(cat <<'EOF'
## Cosa fa questa PR

[Descrizione della modifica]

## Come testare

1. ...
2. ...

## JIRA

[JIRA-ID](https://jira.siae.it/browse/JIRA-ID)

## Checklist

- [ ] Test passano
- [ ] Self-review completata
- [ ] Documentazione aggiornata (se necessario)
EOF
)"
```

**Se FALLBACK_MODE:**

```bash
# Push del branch
git push origin feature/{JIRA-ID}-descrizione
```

Poi apri la PR manualmente:
1. Vai su: `https://github.com/<owner>/<repo>/compare/sviluppo...feature/{JIRA-ID}-descrizione`
2. Clicca "Create pull request"
3. Usa il template seguente per il body:

```
## Cosa fa questa PR

[Descrizione della modifica]

## Come testare

1. ...
2. ...

## JIRA

[JIRA-ID](https://jira.siae.it/browse/JIRA-ID)

## Checklist

- [ ] Test passano
- [ ] Self-review completata
- [ ] Documentazione aggiornata (se necessario)
```
````

**Step 3: Verifica che la skill sia ancora parsabile**

```bash
head -20 skills/siae-finishing-branch/SKILL.md
```
Output atteso: frontmatter YAML + header skill intatto

**Step 4: Commit**

```bash
git add skills/siae-finishing-branch/SKILL.md
git commit -m "feat(skills): add step 0 siae-git-env and conditional gh/fallback to siae-finishing-branch"
```

---

## Task 4: Aggiorna `plugin.json` e `marketplace.json` — count skill [DONE]

**File coinvolti:**
- Modifica: `.claude-plugin/plugin.json` (riga 3 — description)
- Modifica: `.claude-plugin/marketplace.json` (riga 13 — description nel plugin)

**Step 1: Aggiorna plugin.json**

Nella descrizione, aggiorna `27 skill` → `28 skill`.

**Step 2: Aggiorna marketplace.json**

Nella descrizione del plugin interno, aggiorna `27 skill` → `28 skill`.

**Step 3: Verifica**

```bash
grep "skill" .claude-plugin/plugin.json
grep "skill" .claude-plugin/marketplace.json
```
Output atteso entrambi: `28 skill`

**Step 4: Commit**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore(plugin): update skill count to 28 after siae-git-env addition"
```

---

## Verifica Finale

```bash
# Verifica struttura nuova skill
ls skills/siae-git-env/

# Verifica Step 0 in siae-git-workflow
grep -n "siae-git-env" skills/siae-git-workflow/SKILL.md

# Verifica Step 0 e GH_MODE/FALLBACK in siae-finishing-branch
grep -n "siae-git-env\|GH_MODE\|FALLBACK" skills/siae-finishing-branch/SKILL.md

# Verifica count aggiornato
grep "skill" .claude-plugin/plugin.json
```

Output atteso:
```
skills/siae-git-env/: SKILL.md
siae-git-workflow: riga con "REQUIRED SUB-SKILL: siae-git-env"
siae-finishing-branch: righe con siae-git-env, GH_MODE, FALLBACK_MODE
plugin.json: "28 skill"
```
