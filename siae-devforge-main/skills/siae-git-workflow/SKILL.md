---
name: siae-git-workflow
description: >
  Applica la branch strategy e il git flow SIAE. Trigger: operazioni git
  (branch, merge, release, tag), inizio feature, preparazione deploy.
  Enforces conventional commits, tag-based deployment, branch naming.
---

# SIAE Git Workflow

`╔══ 🔨 DevForge — SIAE GIT WORKFLOW ══╗`

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

---

## 9. Anti-Rationalization Table

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
| `git status/log/diff`   | 🟢 SICURO  | Nessuna card                  |
| `git add/commit`        | 🟡 MEDIO   | Card bordo `╔══╗` giallo      |
| `git push`              | 🔴 ALTO    | Card bordo `┏━━┓` rosso       |
| `git merge`             | 🔴 ALTO    | Card bordo `┏━━┓` rosso       |
| `git tag` + push        | 🔴 ALTO    | Card bordo `┏━━┓` rosso       |
| `git push --force`      | 🚨 CRITICO | Card bordo `┏━━┓` rosso bold  |
| `git rebase` (condiviso)| 🚨 CRITICO | Card bordo `┏━━┓` rosso bold  |
