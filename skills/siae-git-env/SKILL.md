---
name: siae-git-env
description: >
  Micro-skill di utility per la detection di GitHub CLI (gh).
  Trigger: REQUIRED SUB-SKILL da siae-git-workflow e siae-finishing-branch.
  Stabilisce GH_MODE o FALLBACK_MODE per la sessione corrente.
---

# siae-git-env — GitHub CLI Environment Check

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
