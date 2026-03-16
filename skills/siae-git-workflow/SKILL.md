---
name: siae-git-workflow
description: >
  OBBLIGATORIA per qualsiasi operazione git: git checkout -b, git commit,
  git push, git merge, git tag, creazione branch, naming branch, conventional
  commits, pre-flight card, inizio feature, preparazione deploy, promozione
  ambiente, hotfix, rollback, push remoto, tag COLLAUDO/CERTIFICAZIONE/PRODUZIONE.
---

# SIAE Git Workflow

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨 DevForge · SIAE GIT WORKFLOW                     ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 3. Branching

## LA LEGGE DI FERRO

```
NESSUN COMMIT SU MAIN DIRETTO — SEMPRE FEATURE BRANCH + PR + REVIEW
```

<EXTREMELY-IMPORTANT>
Questa skill e' OBBLIGATORIA per QUALSIASI operazione git. Non esiste un commit "troppo piccolo",
un push "troppo veloce", o una PR "troppo banale" per saltare queste regole.

Se stai per eseguire `git checkout -b`, `git commit`, `git push`, `git merge`, `git tag`,
o `gh pr create` SENZA aver caricato e seguito questa skill: FERMATI.

Violazioni comuni che questa skill previene:
- Branch creato senza JIRA ID → impossibile tracciare il lavoro
- Commit senza conventional format → history illeggibile
- Push senza pre-flight card → nessun checkpoint prima dell'irreversibile
- PR senza test verdi → sprechi il tempo dei reviewer

L'unico modo per "saltare" questa skill e' che l'utente scriva esplicitamente:
"procedi senza git-workflow" — e anche in quel caso, registra il bypass nel commit message.
</EXTREMELY-IMPORTANT>

---

> 📊 **Dai repo itsiae:** I repo che seguono branch naming `feature/{JIRA-ID}-desc` hanno 2.1x meno conflitti di merge.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

## 0. Environment Check — GitHub CLI

```
REQUIRED SUB-SKILL: siae-git-env
```

Esegui `siae-git-env` prima di qualsiasi operazione git che coinvolge GitHub.
Il `GH_MODE` determinato qui vale per tutta la sessione e determina i comandi usati nella sezione **Flusso Operativo (Step 8)** per l'apertura PR di promozione.

**Non ripetere il check nella stessa sessione.** Se `siae-git-env` è già stata eseguita, usa il GH_MODE già determinato.

---

## 1. Branch Strategy SIAE

```
feature/{JIRA-ID}-descrizione
   ↓ (squash merge)
sviluppo (development)
   ↓ (merge commit, tag COLLAUDO)
collaudo (UAT/test)
   ↓ (merge commit, tag CERTIFICAZIONE)
certificazione (QA/staging)
   ↓ (merge commit, tag push to PRODUZIONE)
produzione / main (production)
```

Il flusso e' unidirezionale. Ogni ambiente ha la sua branch protetta.

---

## 2. Branch Naming

| Prefisso   | Pattern                              | Uso                     |
|------------|--------------------------------------|-------------------------|
| `feature/` | `feature/{JIRA-ID}-short-description` | Nuove funzionalita'    |
| `fix/`     | `fix/{JIRA-ID}-short-description`     | Bug fix                 |
| `hotfix/`  | `hotfix/{JIRA-ID}-short-description`  | Hotfix in produzione    |
| `refactor/`| `refactor/{JIRA-ID}-short-description`| Refactoring             |

Regole:
- Il JIRA ID e' **obbligatorio** (es. `feature/SDLC-142-add-login`)
- Usare kebab-case per la descrizione
- Creare sempre la feature branch da **sviluppo**, mai da main/produzione

---

## 3. Conventional Commits

Formato: `{type}({scope}): {description}`

| Type        | Quando                              |
|-------------|-------------------------------------|
| `feat:`     | Nuova funzionalita'                 |
| `fix:`      | Bug fix                             |
| `refactor:` | Ristrutturazione codice             |
| `chore:`    | Manutenzione, dipendenze, config    |
| `docs:`     | Documentazione                      |
| `test:`     | Aggiunta/modifica test              |

Lo scope e' opzionale ma consigliato (es. `feat(auth): add JWT validation`).
Il messaggio deve essere in inglese, imperativo, lowercase.

---

## 4. Tag-Based Deployment

| Tag              | Ambiente         | Trigger                          |
|------------------|------------------|----------------------------------|
| `COLLAUDO`       | Collaudo (UAT)   | Push tag → CD deploy collaudo    |
| `CERTIFICAZIONE` | Certificazione   | Push tag → CD deploy cert        |
| `PRODUZIONE`     | Produzione       | Push tag → CD deploy prod        |

- CI/CD: reusable GitHub Actions da `itsiae/siae-gh-actions` (v2.x)
- IaC repos: pattern Makefile (`make deploy-collaudo`, `make deploy-certificazione`, `make deploy-produzione`)
- Senza tag, non c'e' deploy. Il tag **e'** il trigger.

---

## 5. Merge Strategy

| Da → A                        | Strategia        | Motivo                        |
|-------------------------------|------------------|-------------------------------|
| feature → sviluppo            | **Squash merge** | History pulita su sviluppo    |
| sviluppo → collaudo           | **Merge commit** | Preserva contesto di release  |
| collaudo → certificazione     | **Merge commit** | Tracciabilita' completa       |
| certificazione → produzione   | **Merge commit** | Audit trail per produzione    |

---

## 6. HARD-GATE Rules

Queste regole sono **non negoziabili**. Nessuna eccezione.

1. **NEVER** push direttamente su collaudo, certificazione, o produzione
2. **NEVER** force-push su qualsiasi branch condiviso
3. **NEVER** eliminare un branch prima che il merge sia confermato
4. **ALL** merges verso sviluppo richiedono PR con almeno 1 review
5. **Pre-flight card 🔴 ALTO** obbligatoria per: `git push`, `git merge`, `git tag`

---

## Permission Denied Handling

Questa skill richiede Bash per tutte le operazioni git.

**Se Bash viene negato:**
1. Passa a modalita' "guida manuale" per l'intera sessione git
2. Presenta i comandi esatti in lista numerata con spiegazione
3. Mantieni tutte le regole (branch naming, conventional commits, pre-flight)
4. NON entrare in loop di retry — un rifiuto = guida manuale

**Esempio:**
```
Non ho permessi per eseguire comandi git. Ecco i comandi:
1. `git checkout sviluppo && git pull origin sviluppo`
2. `git checkout -b feature/PROJ-123-add-login`
Eseguili nel tuo terminale e conferma quando fatto.
```

**Fasi completabili senza permessi:** strategia, naming, merge strategy, pre-flight check verbale
**Fasi che richiedono permessi:** tutte le operazioni git (Bash)

Il valore della skill (strategia corretta, naming, merge strategy) si preserva.
Le HARD-GATE rules si applicano anche in guida manuale.

---

## 7. Vincoli Operativi

| Operazione                  | Rischio | Vincolo                                        |
|-----------------------------|---------|------------------------------------------------|
| `git push`                  | 🔴 ALTO | Pre-flight card obbligatoria                   |
| `git merge`                 | 🔴 ALTO | Pre-flight card obbligatoria                   |
| `git tag`                   | 🔴 ALTO | Pre-flight card obbligatoria                   |
| `git push --force`          | 🚨 CRIT | Conferma esplicita utente + motivazione        |
| `git branch -D`             | 🔴 ALTO | Solo dopo merge confermato                     |
| `git rebase` (branch condiviso) | 🚨 CRIT | MAI su branch condivisi                   |

Regole aggiuntive:
- No `--force` senza conferma esplicita dell'utente (rischio 🚨)
- Branch delete solo dopo merge confermato
- Feature branch sempre da **sviluppo** (mai da main)

---

## 8. Flusso Operativo

**Pre-flight card 🟡 MEDIO — obbligatoria prima di `git add/commit`:**

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-git-workflow |
|:---|
| 🌿 Branch: `<branch-name>` |
| **▼ Azione** |
| 1. 📌 Azione: `git add` + `git commit` → `<file/i modificati>` |
| 💡 Perche': Si stanno registrando modifiche nella history locale del branch |
| 🚫 Se NO: Le modifiche restano unstaged / uncommitted |

**Pre-flight card 🔴 ALTO — obbligatoria prima di `git push`, `git merge`, `git tag`:**

| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-git-workflow |
|:---|
| **⚠️ OPERAZIONE DIFFICILE DA ANNULLARE** |
| 🌿 Branch: `<branch-name>` · 🎯 Target: `<branch-target o remote>` |
| **▼ Azione** |
| 1. 🚀 Azione: `git push / merge / tag` → `origin/<branch-name>` |
| 💡 Perche': L'operazione modifica lo stato del repository remoto o condiviso |
| 🚫 Se NO: L'operazione non viene eseguita — lo stato remoto rimane invariato |

### Nuova feature
```bash
git checkout sviluppo
git pull origin sviluppo
git checkout -b feature/{JIRA-ID}-descrizione
# ... sviluppo ...
git add .
git commit -m "feat({scope}): descrizione"
git push origin feature/{JIRA-ID}-descrizione
# → Apri PR verso sviluppo (squash merge)
```

### Promozione ambiente
```bash
# sviluppo → collaudo
git checkout collaudo && git merge sviluppo
git tag COLLAUDO && git push origin COLLAUDO

# collaudo → certificazione
git checkout certificazione && git merge collaudo
git tag CERTIFICAZIONE && git push origin CERTIFICAZIONE

# certificazione → produzione
git checkout produzione && git merge certificazione
git tag PRODUZIONE && git push origin PRODUZIONE
```

**Apertura PR per promozione (se necessaria):**

**Se GH_MODE:**
```bash
gh pr create --base <branch-target> --title "release: promozione <da> → <a>" --body "Promozione ambiente"
```

**Se FALLBACK_MODE:**

1. Apri: `https://github.com/<owner>/<repo>/compare/<branch-target>...<branch-source>`
   *(base: branch-target, compare: branch-source — es. `compare/collaudo...sviluppo`)*
2. Clicca "Create pull request"
3. Usa questo template per il body:

```
## Promozione <branch-source> → <branch-target>

[Descrizione delle modifiche promosse]

## Checklist

- [ ] Test verdi su <branch-source>
- [ ] Approvazione da team lead
```

---

## 9. Hotfix e Rollback

### Hotfix in produzione

Un hotfix si applica quando un bug critico in produzione non può attendere il ciclo normale (sviluppo → collaudo → certificazione → produzione).

```bash
# 1. Branch da produzione (MAI da sviluppo)
git checkout produzione
git pull origin produzione
git checkout -b hotfix/{JIRA-ID}-descrizione

# 2. Fix minimale + commit
git commit -m "fix({scope}): descrizione hotfix [{JIRA-ID}]"
git push origin hotfix/{JIRA-ID}-descrizione
# → Apri PR verso produzione (merge commit, review obbligatoria)

# 3. Merge e deploy
git checkout produzione && git merge --no-ff hotfix/{JIRA-ID}-descrizione
git tag PRODUZIONE && git push origin PRODUZIONE

# 4. Back-merge su sviluppo (OBBLIGATORIO — non perdere il fix)
git checkout sviluppo
git merge --no-ff hotfix/{JIRA-ID}-descrizione
git push origin sviluppo
```

| Regola hotfix | Dettaglio |
|---------------|-----------|
| Branch da **produzione** | Mai da sviluppo: include modifiche non in produzione |
| PR obbligatoria | Anche per hotfix — nessuna eccezione |
| Back-merge su sviluppo | Obbligatorio dopo deploy: il fix non deve perdersi |
| Commit type `fix:` | Con JIRA ID nel messaggio |

### Rollback

Usa il rollback quando un deploy introduce una regressione critica e il fix immediato non è disponibile.

#### Opzione 1 — Revert commit (preferita)

Crea un commit che annulla le modifiche. Non riscrive la history, è tracciabile e reversibile.

```bash
# Identifica il commit da annullare
git log produzione --oneline

# Revert: crea un nuovo commit di annullamento
git revert {SHA_COMMIT} --no-edit
git push origin produzione

# Re-tag per triggerare il re-deploy
git tag PRODUZIONE -f
git push origin PRODUZIONE -f
```

#### Opzione 2 — Re-tag versione precedente

Se il revert non è praticabile, ri-punta il tag al commit stabile precedente.

```bash
# Identifica il commit stabile
git log produzione --oneline

# Rimuovi il tag corrente e ricrealo sul commit stabile
git tag -d PRODUZIONE
```

**🚨 Operazione CRITICA — pre-flight card OBBLIGATORIA:**

| 🚨 CRITICO (irreversibile) — 🔨 DevForge · siae-git-workflow |
|:---|
| **⚠️ AZIONE IRREVERSIBILE — CONFERMA RICHIESTA** |
| 🏷️ Tag da eliminare: `<tag-name>` · 🌍 Ambiente: `PRODUZIONE` · 📝 Commit stabile: `<commit-hash>` |
| **▼ Azione** |
| 1. ⚠️ Azione: Cancellazione tag remoto (trigga rollback deploy) → `origin/refs/tags/<tag-name>` |
| 💡 Perche': Rollback necessario per incident/bug critico in produzione |
| 🚫 Se NO: Il tag resta, nessun rollback — il deploy corrente rimane attivo |

```bash
git push origin :refs/tags/PRODUZIONE
git tag PRODUZIONE {SHA_COMMIT_STABILE}
git push origin PRODUZIONE
```

| Regola rollback | Dettaglio |
|-----------------|-----------|
| Preferisci il **revert** | Tracciabile, reversibile, non riscrive history |
| Opzione 2 solo se revert non praticabile | Es. commit merge con molti file conflittuali |
| Apri ticket JIRA subito | Il rollback è temporaneo: il fix definitivo va pianificato |
| Non lasciare produzione in rollback | Risolvi il fix nel ciclo normale (hotfix se urgente) |

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi max per step | 2 | Fermati. Chiedi all'utente prima di riprovare. |
| Step totali del workflow | 4 | Se ne servono di piu', il task e' mal definito. Torna al design. |
| Output max per analisi | 300 righe | Sintetizza. L'utente non legge wall-of-text. |

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "E' un fix piccolo, posso pushare direttamente" | Ogni modifica passa per PR. Nessuna eccezione. |
| "Sono su sviluppo, e' safe" | Sviluppo e' condiviso. Feature branch sempre. |
| "Il tag lo metto dopo" | Tag-based deploy. Senza tag non c'e' deploy. |
| "Force push per pulire la history" | Force push distrugge lavoro altrui. MAI su branch condivisi. |
| "Non serve il JIRA ID nel branch" | Il JIRA ID traccia il lavoro. Sempre nel nome del branch. |
| "Faccio merge diretto, la review rallenta" | La review protegge il team. 1 review minimo, sempre. |

---

## Classificazione Rischio Operazioni

| Operazione              | Rischio    | Card                          |
|-------------------------|------------|-------------------------------|
| `git status/log/diff`   | 🟢 SICURO  | No                            |
| `git add/commit`        | 🟡 MEDIO   | Si                            |
| `git push`              | 🔴 ALTO    | Si                            |
| `git merge`             | 🔴 ALTO    | Si                            |
| `git tag` + push        | 🔴 ALTO    | Si                            |
| `git push --force`      | 🚨 CRITICO | Si                            |
| `git rebase` (condiviso)| 🚨 CRITICO | Si                            |
| `git push origin :refs/tags/*` (rollback) | 🚨 CRITICO | Si         |
