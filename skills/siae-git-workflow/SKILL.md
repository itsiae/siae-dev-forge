---
name: siae-git-workflow
description: >
  Use when running any git operation (checkout/commit/push/merge/tag), creating
  a branch, writing a conventional commit, preparing a deploy, promoting an
  environment, performing hotfix or rollback. Gestisce tutte le operazioni git
  secondo il branch flow SIAE.
  Trigger: git checkout -b, git commit, git push, git merge, git tag, creazione
  branch, naming branch, conventional commits, pre-flight card, inizio feature,
  preparazione deploy, promozione ambiente, hotfix, rollback, push remoto,
  tag deploy ambiente.
validates_via:
  predicate: conventional_commit_made
  evidence_type: git_state
  evidence_check: "git log -1 --format=%s matches ^(feat|fix|chore|docs|refactor|test|style|perf|build|ci|revert)(\\(.+\\))?!?:"
---

# SIAE Git Workflow

> **Tipo:** Rigid | **Fase SDLC:** 3. Branching

## LA LEGGE DI FERRO

```
NESSUN COMMIT SU MAIN DIRETTO — SEMPRE FEATURE BRANCH + PR + REVIEW
```

<EXTREMELY-IMPORTANT>
Questa skill e' OBBLIGATORIA per QUALSIASI operazione git. Nessun commit "troppo piccolo", push "troppo veloce", o PR "troppo banale" per saltare queste regole.
Se stai per eseguire `git checkout -b`, `git commit`, `git push`, `git merge`, `git tag`, o `gh pr create` SENZA aver caricato questa skill: FERMATI.

## PRE-FLIGHT CARD — REGOLA ASSOLUTA

Per `git push`, `git merge`, `git tag` (qualsiasi tag, branch, ambiente):

1. MOSTRA la pre-flight card PRIMA di eseguire — sempre, senza eccezioni
2. ATTENDI la risposta esplicita dell'utente — "sì, procedi" o "no, annulla"
3. NON eseguire per silenzio o assenza di risposta — silenzio ≠ consenso
4. NON valutare se "sembra sicura" o "l'utente la vuole implicitamente"

Se l'utente non risponde (silenzio, cambio argomento): NON eseguire, NON rimostrare automaticamente. La card resta "aperta" finché non arriva un "sì" o "no" esplicito; alla prossima richiesta correlata ricordala e chiedi prima di procedere.

La regola non dipende da: nome del tag, branch target, dimensione della modifica, o consenso generico pregresso.

**Conferma valida:** "sì", "vai", "procedi", "confermo", "esegui"
**Conferma NON valida (= silenzio):** "forse", "aspetta", "boh", "magari", "ok" da solo, cambio argomento
**Ambigua:** NON eseguire. Chiedi: *"Confermo? Rispondi 'sì, procedi' oppure 'no, annulla'."*

## SCOPE GUARD — Anti-Scope-Creep

Prima di ogni operazione git, chiediti: *"L'utente ha richiesto ESPLICITAMENTE questa operazione?"*

- `git push branch` richiesto → solo push del branch. NON eseguire tag/merge/deploy non richiesti.
- `fix + push` richiesto → fix e push. NON toccare tag, ambienti, pipeline non menzionati.
- "push sul branch feature" → solo quello. NON creare/spostare tag di ambiente.

Se fuori perimetro: NON eseguire, chiedi prima. Espandere autonomamente = VIETATO anche se tecnicamente correlato. Applicabile specialmente a: tag di ambiente, merge su branch condivisi, delete/recreate tag.
</EXTREMELY-IMPORTANT>

> Dai repo itsiae: branch `feature/{JIRA-ID}-desc` → 2.1x meno conflitti di merge (816 repo analizzati).

## 0. Environment Check — GitHub CLI

`REQUIRED SUB-SKILL: siae-git-env` — esegui prima di qualsiasi operazione git che coinvolge GitHub. Il `GH_MODE` determinato vale per tutta la sessione. Non ripetere il check nella stessa sessione.

## 1. Branch Strategy SIAE

```
feature/{JIRA-ID}-descrizione  →(squash)→  sviluppo  →(merge, tag <ENV_TAG_UAT>)→  collaudo
  →(merge, tag <ENV_TAG_CERT>)→  certificazione  →(merge, tag <ENV_TAG_PROD>)→  produzione/main
```

Flusso unidirezionale. Ogni ambiente ha la sua branch protetta. `<ENV_TAG_*>` = tag deploy specifico del progetto (es. SIAE: `COLLAUDO`, `CERTIFICAZIONE`, `PRODUZIONE`).

## 2. Branch Naming

| Prefisso                 | Pattern                                | Uso                  |
|--------------------------|----------------------------------------|----------------------|
| `feature/`               | `feature/{JIRA-ID}-short-description`  | Nuove funzionalita'  |
| `fix/` (alias `bugfix/`) | `fix/{JIRA-ID}-short-description`      | Bug fix              |
| `hotfix/`                | `hotfix/{JIRA-ID}-short-description`   | Hotfix in produzione |
| `release/`               | `release/{version}`                    | Release branch       |
| `refactor/`              | `refactor/{JIRA-ID}-short-description` | Refactoring          |

JIRA ID **obbligatorio** (es. `feature/SDLC-142-add-login`). Kebab-case per la descrizione. Feature branch dal branch di riferimento (`release/*` o `sviluppo`), mai da `main` direttamente.

## 3. Conventional Commits

Formato: `{type}({scope}): {description}`
Regex: `^(feat|fix|chore|docs|refactor|test|style|perf|build|ci|revert)(\(.+\))?!?: .+`

Type principali: `feat:` (feature), `fix:` (bug), `refactor:`, `chore:`, `docs:`, `test:`.
Scope opzionale ma consigliato (es. `feat(auth): add JWT validation`). Messaggio in inglese, imperativo, lowercase.

## 4. Tag-Based Deployment

| Tag                | Ambiente       | Trigger                        |
|--------------------|----------------|--------------------------------|
| `<ENV_TAG_DEV>`    | Sviluppo (dev) | Push tag → CD deploy sviluppo  |
| `<ENV_TAG_UAT>`    | Collaudo (UAT) | Push tag → CD deploy collaudo  |
| `<ENV_TAG_CERT>`   | Certificazione | Push tag → CD deploy cert      |
| `<ENV_TAG_PROD>`   | Produzione     | Push tag → CD deploy prod      |

`<ENV_TAG_*>` placeholder = nome tag specifico del progetto (es. SIAE: `sviluppo`, `COLLAUDO`, `CERTIFICAZIONE`, `PRODUZIONE`). Qualsiasi tag = rischio CRITICO. Delete + recreate = re-deploy. Il tag **è** il trigger: senza tag niente deploy. Tutti i tag richiedono pre-flight card + ATTENDI CONFERMA ESPLICITA.
CI/CD: reusable Actions da `itsiae/siae-gh-actions` (v2.x). IaC: Makefile (`make deploy-{ambiente}`).

## 5. Merge Strategy

| Da → A                         | Strategia        |
|--------------------------------|------------------|
| feature → sviluppo             | **Squash merge** |
| sviluppo → collaudo/cert/prod  | **Merge commit** |

Squash su feature = history pulita. Merge commit sugli ambienti = contesto release + audit trail.

## 6. HARD-GATE Rules

Queste regole sono **non negoziabili**. Nessuna eccezione.

1. **NEVER** push direttamente su collaudo, certificazione, o produzione
2. **BLOCCO ASSOLUTO - git push --force vietato su qualsiasi branch condiviso** (sviluppo, collaudo, certificazione, produzione, main). Refuse e proponi `git revert` o PR di riallineamento.
3. **BLOCCO ASSOLUTO - git rebase vietato** su branch condiviso (riscrive history degli altri developer). Usa `git merge` invece.
4. **NEVER** eliminare un branch prima che il merge sia confermato
5. **SOLO** merges verso **main** richiedono PR con almeno 1 review — su `sviluppo` la review è facoltativa (direttiva DevOps SIAE). Review facoltativa ≠ pre-flight card facoltativa.
6. **Pre-flight card + ATTENDI CONFERMA ESPLICITA** obbligatoria per: `git push`, `git merge`, `git tag` — qualsiasi branch, qualsiasi tag, senza eccezioni.

## Pre-flight Card — Decisione rapida

| Comando                                 | Livello   | Card richiesta                      |
|-----------------------------------------|-----------|-------------------------------------|
| `git status/log/diff`                   | SICURO    | No                                  |
| `git checkout -b` new branch            | SICURO    | No                                  |
| `git add` + `git commit`                | MEDIO     | Sì (informativa, no blocco hard)    |
| `git push` feature branch               | ALTO      | Sì + ATTENDI conferma esplicita     |
| `git merge` promozione ambiente         | ALTO      | Sì + ATTENDI conferma esplicita     |
| `git branch -D`                         | ALTO      | Sì + verify merge confermato        |
| `git tag` + push (qualsiasi tag)        | CRITICO   | Sì + ATTENDI conferma esplicita     |
| `git push --force` branch personale     | CRITICO   | Sì + motivazione scritta + ATTENDI  |
| `git push --force` branch condiviso     | CRITICO   | **BLOCCO ASSOLUTO** — refuse        |
| `git rebase` branch condiviso           | CRITICO   | **BLOCCO ASSOLUTO** — refuse        |
| `git push origin :refs/tags/*` rollback | CRITICO   | Sì + ATTENDI conferma esplicita     |
| Scope creep: operazione non richiesta   | -         | STOP — chiedi prima                 |

**Safeguard:** `BLOCCO ASSOLUTO - git push --force` e `git rebase` su branch condiviso sono vietati a monte, prima della pre-flight. Nessuna card, refuse immediato, proponi alternativa (`git revert` o PR di riallineamento).

**Formato Pre-flight Card:** vedi `lib/checkpoint-schema.md`. Esempio template (ALTO):

| ALTO (difficile da annullare) — DevForge · siae-git-workflow |
|:---|
| Branch: `<branch-name>` · Target: `<remote/branch-target>` |
| 1. Azione: `git push / merge / tag` |
| Perche': modifica stato repository remoto/condiviso |
| Se NO: stato remoto invariato |

ATTENDI CONFERMA ESPLICITA — NON eseguire finché l'utente risponde "sì, procedi" o "no, annulla".

### Nuova feature

```bash
git checkout <parent-branch> && git pull origin <parent-branch>
git checkout -b feature/{JIRA-ID}-descrizione
git add . && git commit -m "feat({scope}): descrizione"
git push origin feature/{JIRA-ID}-descrizione
# → PR verso <parent-branch> (squash merge)
```

### Promozione ambiente

Merge e tag sono step SEPARATI con card SEPARATE — non accorpare in un'unica conferma.

```bash
# card ALTO merge + ATTENDI → git checkout collaudo && git merge sviluppo
# card CRITICO tag + ATTENDI → git tag <ENV_TAG_UAT> && git push origin <ENV_TAG_UAT>
# Ripeti per certificazione → produzione
# es. SIAE: <ENV_TAG_UAT>=COLLAUDO, <ENV_TAG_CERT>=CERTIFICAZIONE, <ENV_TAG_PROD>=PRODUZIONE
```

## Hotfix e Rollback

**Hotfix in produzione** — branch da **produzione** (mai da sviluppo). PR obbligatoria. Back-merge su sviluppo OBBLIGATORIO.

```bash
git checkout produzione && git pull origin produzione
git checkout -b hotfix/{JIRA-ID}-descrizione
git commit -m "fix({scope}): descrizione hotfix [{JIRA-ID}]"
git push origin hotfix/{JIRA-ID}-descrizione
# → PR verso produzione (merge commit, review obbligatoria)
# Deploy: card ALTO merge + ATTENDI, poi card CRITICO tag + ATTENDI
git checkout produzione && git merge --no-ff hotfix/{JIRA-ID}-descrizione
git tag <ENV_TAG_PROD> && git push origin <ENV_TAG_PROD>
# Back-merge obbligatorio
git checkout sviluppo && git merge --no-ff hotfix/{JIRA-ID}-descrizione && git push origin sviluppo
```

**Rollback** — preferisci `git revert` (tracciabile, non riscrive history):

```bash
git revert {SHA_COMMIT} --no-edit && git push origin produzione
git tag <ENV_TAG_PROD> -f && git push origin <ENV_TAG_PROD> -f
```

Se revert non praticabile — re-tag su commit stabile (operazione **CRITICO**, card + ATTENDI ad ogni step):

```bash
# Solo dopo "sì, procedi" sulla card CRITICO:
git push origin :refs/tags/<ENV_TAG_PROD>   # rimozione tag (trigga rollback)
git tag <ENV_TAG_PROD> {SHA_COMMIT_STABILE}
git push origin <ENV_TAG_PROD>              # richiede SECONDA card CRITICO + ATTENDI
```

Non concatenare i 3 step automaticamente. Apri ticket JIRA subito: il rollback è temporaneo.

## Riferimenti esterni

- Permission Denied Handling (Bash negato, sequenze parziali, recovery): `lib/permission-denied-handling.md`
- Limiti Operativi (tentativi max, step max, recovery): `lib/operational-limits.md`
- Classificazione Rischio (tassonomia completa): `lib/risk-taxonomy.md`
- Schema Pre-flight Card (formato standard): `lib/checkpoint-schema.md`

**Override git-specifici** (rispetto a `lib/risk-taxonomy.md`):
- `git tag` + push su QUALSIASI tag → CRITICO (anche `sviluppo`)
- `git push --force` o `git rebase` su branch condiviso → BLOCCO ASSOLUTO (non solo CRITICO)
- `git merge` verso main richiede PR + 1 review; verso sviluppo review facoltativa ma card sempre obbligatoria
