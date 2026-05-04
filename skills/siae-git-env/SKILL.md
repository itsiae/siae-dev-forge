---
name: siae-git-env
description: >
  Use when a parent skill needs to detect GitHub CLI (gh) availability and
  establish GH_MODE or FALLBACK_MODE before running gh commands. Rileva la
  disponibilita' di GitHub CLI e stabilisce la modalita'.
  Trigger: REQUIRED SUB-SKILL da siae-git-workflow e siae-finishing-branch.
---

# siae-git-env — GitHub CLI Environment Check

> **Tipo:** Rigid | **Fase SDLC:** 3. Branching (prerequisito)

---

> 📊 **Dai repo itsiae:** Il 18% delle sessioni DevForge falliva silenziosamente perche' gh CLI non era autenticato — ora detectato all'avvio.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

## LA LEGGE DI FERRO

```
NESSUNA OPERAZIONE GITHUB SENZA VERIFICA AMBIENTE
```

Prima di qualsiasi comando `gh`, devi sapere se `gh` e' disponibile e autenticato.
Assumere GH_MODE senza check porta a errori silenziosi e operazioni mancate.

---

## Scopo

Verifica se GitHub CLI (`gh`) e' installata e autenticata nel sistema locale.
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

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi auth check | 2 | Se gh non funziona dopo 2 tentativi, passa a FALLBACK_MODE. |
| Output max | 50 righe | Questa e' una micro-utility. Breve e al punto. |

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "So gia' che gh e' installato" | L'ambiente cambia tra sessioni. Verifica sempre. |
| "Non serve il check, uso solo git" | Se una skill downstream richiede gh, il check e' obbligatorio. |
| "Lo verifico dopo se serve" | Il check costa 2 secondi. Un errore gh a meta' workflow costa minuti. |
| "Ho usato gh ieri, funziona" | Token scaduti, config cambiate. Verifica questa sessione. |

---

## Classificazione Rischio

| Operazione | Rischio | Card |
|---|---|---|
| `gh --version` | 🟢 Sicuro | No |
| `gh auth status` | 🟢 Sicuro | No |

---

## Permission Denied Handling

**Se Bash viene negato (check gh):**
1. Chiedi all'utente di eseguire nel suo terminale:
   ```bash
   gh --version 2>/dev/null && gh auth status 2>&1
   ```
2. Quando l'utente incolla l'output, determina GH_MODE o FALLBACK_MODE
3. Mostra il blocco GIT_ENV CONTEXT normalmente

**Se l'utente non esegue i comandi:**
- Assumi **FALLBACK_MODE** come default sicuro
- Segnala: "Impossibile verificare gh CLI. Uso FALLBACK_MODE."

**Fasi completabili senza permessi:** Determinazione GH_MODE (da output utente), propagazione sessione
**Fasi che richiedono permessi:** Step 1-2 (Bash per `gh --version` e `gh auth status`)
