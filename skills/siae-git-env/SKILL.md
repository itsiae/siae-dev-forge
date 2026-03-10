---
name: siae-git-env
description: >
  ALWAYS use when configuring git environment, setting up hooks, .gitignore, GPG signing, or git-lfs for a project.
  Trigger: configura git, git hooks, .gitignore, git config, pre-commit hooks, GPG commit, .gitattributes, git-lfs, template commit message, credenziali git.
---

# siae-git-env — GitHub CLI Environment Check

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨 DevForge · SIAE GIT ENV                          ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 3. Branching (prerequisito)

---

## LA LEGGE DI FERRO

```
GH_ENV CHECK OBBLIGATORIO PRIMA DI OGNI OPERAZIONE GITHUB-NATIVE
```

---

## Quando si Applica

Invoca questa skill come sub-skill prerequisito prima di:
- Qualsiasi operazione GitHub-native (apertura PR, review, merge via gh)
- All'avvio di `siae-git-workflow` o `siae-finishing-branch`

**Non ripetere nella stessa sessione** — il GH_MODE determinato vale per tutta la sessione.

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

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Non ho gh ma conosco i comandi git" | FALLBACK_MODE e' funzionale quanto GH_MODE. Il check stabilisce il contesto corretto per le skill downstream. |
| "Lo so gia' se gh e' installata" | La sessione non ha stato persistente. Esegui il check ad ogni nuova sessione. |
| "E' un'operazione veloce, salto il check" | Senza GIT_ENV CONTEXT le skill downstream non sanno quale modalita' usare. |
| "gh auth status e' lento" | Il comando ritorna in meno di 1 secondo. Il costo e' trascurabile. |
| "Basta sapere se gh c'e', l'auth non serve" | gh non autenticata equivale a gh assente per le operazioni GitHub-native. |
| "Uso sempre lo stesso ambiente, non cambia mai" | L'ambiente di sviluppo e CI/CD cambiano senza preavviso. Il check e' rapido — 2 secondi. |
| "gh funzionava ieri, funziona ancora" | L'autenticazione scade. Un token revocato non e' rilevabile senza check. |
| "Sono in FALLBACK_MODE, non cambiera'" | Se gh viene installata o autenticata dopo, solo il check aggiorna il contesto. |

---

## Vincoli

1. Esegui il check **UNA SOLA VOLTA** per sessione — non ripetere se GH_MODE è già determinato.
2. Il GH_MODE determinato è immutabile per la durata della sessione.
3. Non esporre credenziali o token nell'output del blocco GIT_ENV CONTEXT.
4. In FALLBACK_MODE, **NON omettere** nessuna operazione — ogni operazione GitHub-native ha un'alternativa documentata.

---

## Classificazione Rischio Operazioni

| Operazione | Rischio | Card |
|---|---|---|
| `gh --version` | 🟢 Sicuro | No |
| `gh auth status` | 🟢 Sicuro | No |
