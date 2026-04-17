---
name: siae-git-workflow
description: >
  Gestisce tutte le operazioni git secondo il branch flow SIAE.
  Trigger: git checkout -b, git commit, git push, git merge, git tag, creazione
  branch, naming branch, conventional commits, pre-flight card, inizio feature,
  preparazione deploy, promozione ambiente, hotfix, rollback, push remoto,
  tag COLLAUDO/CERTIFICAZIONE/PRODUZIONE.
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

## PRE-FLIGHT CARD — REGOLA ASSOLUTA

Per `git push`, `git merge`, `git tag` (QUALSIASI tag, QUALSIASI branch, QUALSIASI ambiente):

1. MOSTRA la pre-flight card PRIMA di eseguire — SEMPRE, senza eccezioni
2. ATTENDI la risposta esplicita dell'utente — "sì, procedi" o "no, annulla"
3. NON eseguire per silenzio, timeout, o assenza di risposta — silenzio ≠ consenso
4. NON valutare se l'operazione "sembra sicura" o "l'utente la vuole implicitamente"

Se l'utente NON risponde alla card (silenzio, cambio argomento, altra richiesta):
- NON eseguire l'operazione
- NON rimostare la card automaticamente
- Se l'utente fa una nuova richiesta correlata: ricorda la card pendente e chiedi prima di procedere
- La card rimane "aperta" finché non arriva un "sì" o "no" esplicito

Questa regola NON dipende da:
- Il nome del tag (sviluppo, COLLAUDO, custom, qualsiasi)
- Il branch di destinazione (main, sviluppo, feature, qualsiasi)
- La dimensione della modifica ("è solo un push piccolo")
- Il fatto che l'utente abbia "già detto" di procedere in modo generico

**Risposte valide per "sì, procedi":** varianti chiare come "sì", "vai", "ok procedi", "confermo", "esegui"
**Risposte NON valide (= silenzio):** "forse", "aspetta", "ci penso", "boh", "magari", "ok" senza contesto chiaro, cambio argomento
**Se risposta ambigua:** NON eseguire. Chiedi: *"Confermo l'operazione? Rispondi 'sì, procedi' oppure 'no, annulla'."*

## SCOPE GUARD — Regola Anti-Scope-Creep

Prima di QUALSIASI operazione git, rispondi a questa domanda:
"L'utente ha richiesto ESPLICITAMENTE questa operazione?"

- `git push branch` richiesto → esegui push del branch. NON eseguire tag, merge, o deploy non richiesti.
- `fix + push` richiesto → fix e push. NON toccare tag, ambienti, o pipeline non menzionati.
- "push sul branch feature" richiesto → solo push su quel branch. NON creare/spostare tag di ambiente.

SE l'operazione non e' nel perimetro esplicito della richiesta → NON eseguire, chiedi prima.
Espandere autonomamente il perimetro e' VIETATO, anche se tecnicamente correlato.
Questo vale specialmente per: tag di ambiente (sviluppo, COLLAUDO, ecc.), merge su branch condivisi,
delete/recreate di tag esistenti.
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
- Creare la feature branch dal branch di riferimento (tipicamente `release/*` o `sviluppo`), mai da `main` direttamente

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
| `sviluppo`       | Sviluppo (dev)   | Push tag → CD deploy sviluppo 🚨 |
| `COLLAUDO`       | Collaudo (UAT)   | Push tag → CD deploy collaudo    |
| `CERTIFICAZIONE` | Certificazione   | Push tag → CD deploy cert        |
| `PRODUZIONE`     | Produzione       | Push tag → CD deploy prod        |

- CI/CD: reusable GitHub Actions da `itsiae/siae-gh-actions` (v2.x)
- IaC repos: pattern Makefile (`make deploy-collaudo`, `make deploy-certificazione`, `make deploy-produzione`)
- Senza tag, non c'e' deploy. Il tag **e'** il trigger.

> ⚠️ Il tag `sviluppo` triggerizza un deploy automatico esattamente come COLLAUDO.
> Classificazione rischio: 🚨 CRITICO — richiede conferma esplicita, anche se l'ambiente
> e' "solo dev". Delete + recreate del tag causa un re-deploy immediato.

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
4. **SOLO** merges verso **main** richiedono PR con almeno 1 review — su `sviluppo` la review è facoltativa (direttiva DevOps SIAE)
   > ⚠️ Review facoltativa ≠ pre-flight card facoltativa. La card 🔴 ALTO per `git merge` è obbligatoria indipendentemente dal target branch. Sono due requisiti distinti.
5. **Pre-flight card 🔴 ALTO** obbligatoria per: `git push`, `git merge`, `git tag` — **su qualsiasi branch, qualsiasi tag, senza eccezioni**

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

**Caso speciale — Bash negato DOPO "sì, procedi":**
Se l'utente ha confermato la card ma poi nega il tool call Bash:
1. NON ripetere il tentativo automaticamente
2. Comunica: "Hai confermato l'operazione ma il permesso Bash è stato negato. Esegui manualmente:"
3. Fornisci il comando esatto pronto da incollare nel terminale
4. Chiedi conferma quando eseguito: "Dimmi quando hai eseguito il comando"

**Caso speciale — Bash negato A METÀ sequenza (stato inconsistente):**
Se un'operazione multi-step si interrompe a metà (es. merge OK → push tag NEGATO):
1. NON procedere autonomamente con i passi successivi
2. Comunica lo stato attuale: "Ho completato [step X]. Il passo successivo [step Y] è bloccato."
3. Mostra i comandi rimanenti in lista numerata
4. Aspetta istruzioni esplicite: "Come vuoi procedere?"
5. NON tentare di rollback automatico dello step già completato senza consenso

---

## 7. Vincoli Operativi

> ⚠️ "Pre-flight + ATTENDI" significa: mostra la card, NON eseguire, aspetta "sì, procedi" esplicito.
> Nessuna operazione sotto 🔴 o 🚨 si esegue per silenzio, implicito, o inferenza.

| Operazione                      | Rischio    | Vincolo                                              |
|---------------------------------|------------|------------------------------------------------------|
| `git push`                      | 🔴 ALTO    | Pre-flight + ATTENDI CONFERMA ESPLICITA              |
| `git merge`                     | 🔴 ALTO    | Pre-flight + ATTENDI CONFERMA ESPLICITA              |
| `git tag` + push (QUALSIASI)    | 🚨 CRITICO | Pre-flight + ATTENDI CONFERMA ESPLICITA — qualsiasi tag triggerizza pipeline |
| `git push --force`              | 🚨 CRITICO | Pre-flight + ATTENDI CONFERMA ESPLICITA + motivazione scritta |
| `git branch -D`                 | 🔴 ALTO    | Pre-flight + ATTENDI CONFERMA ESPLICITA — solo dopo merge confermato |
| `git rebase` (branch condiviso) | 🚨 CRITICO | MAI senza Pre-flight + ATTENDI CONFERMA ESPLICITA    |
| `git push origin :refs/tags/*`  | 🚨 CRITICO | Pre-flight + ATTENDI CONFERMA ESPLICITA — rollback immediato |

Regole aggiuntive:
- No `--force` senza conferma esplicita dell'utente (rischio 🚨)
- Branch delete solo dopo merge confermato
- Feature branch dal branch di riferimento (`release/*` o `sviluppo`), mai da `main` direttamente

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

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

### Nuova feature
```bash
# Checkout dal branch di riferimento (release/* o sviluppo)
git checkout <parent-branch>
git pull origin <parent-branch>
git checkout -b feature/{JIRA-ID}-descrizione
# ... sviluppo ...
git add .
git commit -m "feat({scope}): descrizione"
git push origin feature/{JIRA-ID}-descrizione
# → Apri PR verso <parent-branch> (squash merge)
# Il target della PR viene rilevato automaticamente da siae-finishing-branch (Step 0b)
```

### Promozione ambiente

> ⚠️ **Ogni operazione sotto richiede la propria pre-flight card + ATTENDI CONFERMA ESPLICITA.**
> Merge e tag sono step SEPARATI con card SEPARATE — non si accorpano in un'unica conferma.
> I comandi sotto sono riferimento tecnico, NON una sequenza da eseguire automaticamente.

**Step 1 — Mostra card per merge, ATTENDI "sì", poi esegui:**
```bash
git checkout collaudo && git merge sviluppo   # → pre-flight 🔴 ALTO + ATTENDI
```

**Step 2 — Solo dopo conferma Step 1. Mostra card per tag, ATTENDI "sì", poi esegui:**
```bash
git tag COLLAUDO && git push origin COLLAUDO  # → pre-flight 🚨 CRITICO + ATTENDI
```

**Step 3-4 — Ripeti il pattern per ogni promozione successiva:**
```bash
git checkout certificazione && git merge collaudo    # → card merge + ATTENDI
git tag CERTIFICAZIONE && git push origin CERTIFICAZIONE  # → card tag + ATTENDI

git checkout produzione && git merge certificazione  # → card merge + ATTENDI
git tag PRODUZIONE && git push origin PRODUZIONE     # → card tag + ATTENDI
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

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

**Solo dopo "sì, procedi":**
```bash
# Step A — rimozione tag remoto (trigga rollback immediato)
git push origin :refs/tags/PRODUZIONE

# Step B — ricreazione tag su commit stabile
git tag PRODUZIONE {SHA_COMMIT_STABILE}

# Step C — push nuovo tag (trigga re-deploy su commit stabile)
# → richiede una seconda card 🚨 CRITICO prima di eseguire questo step
git push origin PRODUZIONE
```

> ⚠️ Il push del nuovo tag (Step C) è un'operazione separata che **richiede una seconda card + ATTENDI**
> prima di essere eseguita. Non concatenare i 3 step in un'unica esecuzione automatica.

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

### Recovery da operazioni parziali

Quando una sequenza multi-step si interrompe a metà (errore, Bash negato, network), segui questa matrice:

| Step completato | Step fallito | Azione Claude |
|---|---|---|
| nessuno | qualsiasi | Comunica l'errore. Mostra i comandi da eseguire. Chiedi come procedere. |
| merge ✅ | tag push ❌ | "Merge completato su `<branch>`. Il push del tag `<TAG>` è fallito: `<errore>`. Il deploy NON è stato avviato. Vuoi riprovare il push del tag?" |
| merge ✅ + tag ✅ | push tag ❌ | "Tag creato localmente ma NON pushato. Deploy non avviato. Comando da eseguire: `git push origin <TAG>`" |
| push ✅ | verifica PR ❌ | "Push completato. Non riesco a verificare lo stato della PR (gh CLI non disponibile). Verifica manualmente su GitHub." |

**Regole per recovery:**
- NON rollback automatico dello step già completato senza consenso esplicito
- NON riprovare più di 2 volte lo stesso step fallito → fermati e chiedi
- Comunica SEMPRE lo stato corrente prima di proporre qualsiasi azione

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "E' un fix piccolo, posso pushare direttamente" | Ogni modifica passa per PR. Nessuna eccezione. |
| "Sono su sviluppo, e' safe" | Sviluppo e' condiviso. Feature branch sempre. |
| "Il tag lo metto dopo" | Tag-based deploy. Senza tag non c'e' deploy. |
| "Force push per pulire la history" | Force push distrugge lavoro altrui. MAI su branch condivisi. |
| "Non serve il JIRA ID nel branch" | Il JIRA ID traccia il lavoro. Sempre nel nome del branch. |
| "Faccio merge diretto, la review rallenta" | La review protegge il team. 1 review minimo su main, sempre. |
| "L'utente ha detto fix + push, il tag e' implicito" | Scope guard: se non e' nella richiesta, non e' nel perimetro. Chiedi prima. |
| "Ho mostrato la card, quindi ho avuto conferma" | Mostrare la card ≠ ricevere consenso. Attendi risposta esplicita. |
| "Su sviluppo non serve la review" | Su sviluppo la review e' facoltativa per DevOps, ma il tag e' ancora un trigger CD critico. |

---

## 10. Esempi Pratici — Pre-flight Card

Ogni esempio mostra: richiesta utente → pre-flight card corretta → ATTENDI → comportamento post-risposta.

---

### Caso 1 — `git push` feature branch

**Richiesta utente:** "fai push del branch feature/SDLC-42-login"

```
Ho preparato il push. Prima di procedere:

| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-git-workflow |
|:---|
| **⚠️ OPERAZIONE DIFFICILE DA ANNULLARE** |
| 🌿 Branch: `feature/SDLC-42-login` · 🎯 Target: `origin` |
| **▼ Azione** |
| 1. 🚀 Azione: `git push origin feature/SDLC-42-login` |
| 💡 Perche': Push del branch verso il remote per apertura PR |
| 🚫 Se NO: Il branch resta locale, nessuna PR possibile |

⏸️ Confermo il push? (sì, procedi / no, annulla)
```

- **Utente: "sì, procedi"** → esegue `git push origin feature/SDLC-42-login`
- **Utente: "no"** → STOP. Branch resta locale.
- **Utente: silenzio / altra richiesta** → NON esegue. Rimostra la card alla prossima interazione.

---

### Caso 2 — `git tag` + push (qualsiasi tag)

**Richiesta utente:** "deployiamo in collaudo"

```
Verifico lo stato del branch collaudo e preparo la promozione. Prima di procedere:

| 🚨 CRITICO (irreversibile) — 🔨 DevForge · siae-git-workflow |
|:---|
| **⚠️ AZIONE IRREVERSIBILE — CONFERMA RICHIESTA** |
| 🏷️ Tag: `COLLAUDO` · 🌍 Ambiente: Collaudo (UAT) · 🌿 Branch: `collaudo` · 📝 Commit: `a1b2c3d` |
| **▼ Azione** |
| 1. 🚀 `git tag COLLAUDO && git push origin COLLAUDO` → trigger automatico pipeline CD collaudo |
| 💡 Perche': Il tag è il trigger. Push del tag avvia il deploy su collaudo. |
| 🚫 Se NO: Tag non creato, nessun deploy avviato |

⏸️ Confermo il deploy su collaudo? (sì, procedi / no, annulla)
```

- **Utente: "sì, procedi"** → `git tag COLLAUDO && git push origin COLLAUDO`
- **Utente: "no"** → STOP.

> **Nota:** Identica card per tag `sviluppo`, `CERTIFICAZIONE`, `PRODUZIONE`, o qualsiasi custom tag.
> Il nome del tag non cambia il comportamento — la card è sempre obbligatoria.

---

### Caso 3 — `git merge` (promozione sviluppo → collaudo)

**Richiesta utente:** "promuovi sviluppo in collaudo"

```
Verifico divergenza tra sviluppo e collaudo. Prima di procedere al merge:

| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-git-workflow |
|:---|
| **⚠️ OPERAZIONE DIFFICILE DA ANNULLARE** |
| 🌿 Branch source: `sviluppo` · 🎯 Target: `collaudo` · 📝 Commit aggiuntivi: N |
| **▼ Azione** |
| 1. 🔀 Azione: `git checkout collaudo && git merge sviluppo` |
| 💡 Perche': Promozione rilascio da sviluppo verso ambiente collaudo |
| 🚫 Se NO: Branch collaudo invariato, nessuna promozione eseguita |

⏸️ Confermo il merge sviluppo → collaudo? (sì, procedi / no, annulla)
```

- **Utente: "sì"** → merge. Poi mostrerà una seconda card per il tag `COLLAUDO` (passo separato, conferma separata).
- **Nota:** merge e tag sono **due card distinte** — non si accorpano.

---

### Caso 4 — `git push --force`

**Richiesta utente:** "force push del branch fix/SDLC-99"

```
| 🚨 CRITICO (irreversibile) — 🔨 DevForge · siae-git-workflow |
|:---|
| **⚠️ AZIONE IRREVERSIBILE — CONFERMA RICHIESTA** |
| 🌿 Branch: `fix/SDLC-99-auth-bug` · 🎯 Target: `origin` |
| **▼ Azione** |
| 1. ⚠️ `git push --force origin fix/SDLC-99-auth-bug` → sovrascrive history remota |
| 💡 Perche': [motivazione obbligatoria — es. "rebase su sviluppo dopo review"] |
| 🚫 Se NO: STOP — history remota invariata |

⏸️ Confermo il force push? Indica il motivo se non già specificato. (sì, procedi / no, annulla)
```

- Richiede **motivazione esplicita** prima di procedere.
- Se l'utente non fornisce motivazione: chiedere "Per quale motivo è necessario il force push?" prima di mostrare la card.

---

### Caso 5 — Scope Creep (tag non richiesto)

**Richiesta utente:** "fai la fix Critical-2 e pusha sul branch feature"

```
Fix applicata. Eseguo il push del branch feature/SDLC-77-critical-2.

| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-git-workflow |
|:---|
| **⚠️ OPERAZIONE DIFFICILE DA ANNULLARE** |
| 🌿 Branch: `feature/SDLC-77-critical-2` · 🎯 Target: `origin` |
| **▼ Azione** |
| 1. 🚀 `git push origin feature/SDLC-77-critical-2` |
| 💡 Perche': Pubblicazione fix Critical-2 sul remote |
| 🚫 Se NO: Branch resta locale |

⏸️ Confermo il push? (sì, procedi / no, annulla)
```

**Cosa NON fare (scope creep):**
```
❌ SBAGLIATO — dopo il push, eseguire autonomamente:
   git tag -d sviluppo
   git tag sviluppo feature/SDLC-77-critical-2
   git push origin sviluppo
   → NON richiesto. NON nel perimetro. NON eseguire.
```

La richiesta era "fix + push sul branch feature". Qualsiasi operazione su tag, ambienti,
o pipeline è FUORI PERIMETRO e richiede una nuova richiesta esplicita dall'utente.

---

### Caso 6 — `git push --force` su branch condiviso (BLOCCO ASSOLUTO)

**Richiesta utente:** "force push su sviluppo"

```
⛔ STOP — Operazione bloccata.

`git push --force` su `sviluppo` è vietato dalla HARD-GATE rule #2:
"NEVER force-push su qualsiasi branch condiviso"

`sviluppo` è un branch condiviso dal team. Il force push sovrascrive la history
di tutti i developer che hanno già basato il loro lavoro su questo branch.

Alternativa sicura: usa `git revert` per creare un commit di annullamento.
Se hai bisogno di allineare sviluppo, apri una PR dal tuo branch.

Vuoi procedere con il revert?
```

- **Nessuna card mostrata** — l'operazione viene bloccata a monte prima ancora della pre-flight.

---

### Caso 7 — `git add/commit` (🟡 MEDIO)

**Utente:** committa le modifiche

**Claude:**

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-git-workflow |
|:---|
| 🌿 Branch: `feature/SDLC-42-add-login` |
| **▼ Azione** |
| 1. 📌 `git add src/main/java/it/siae/auth/AuthService.java` |
| 2. 📌 `git commit -m "feat(auth): add null check on login input [SDLC-42]"` |
| 💡 Perché: Registra le modifiche nella history locale |
| 🚫 Se NO: Le modifiche restano unstaged |

> ℹ️ Card 🟡 MEDIO: informativa, non richiede blocco hard. Procedo se l'utente non dice esplicitamente "no".
> Differenza con 🔴/🚨: qui il silenzio è accettabile perché l'operazione è **reversibile** (`git reset`).

---

### Caso 8 — `git branch -D` (con verifica merge obbligatoria)

**Utente:** cancella il branch `feature/SDLC-88` dopo il merge

**Claude:** Prima verifico che il merge sia confermato — HARD-GATE rule #3.

```bash
$ gh pr list --head feature/SDLC-88 --state merged
#104  feat(catalog): new search endpoint [SDLC-88]  MERGED ✅
```

> **Fallback — gh non disponibile (FALLBACK_MODE):**
> Sostituisci il comando con: `git branch -r --merged origin/main | grep feature/SDLC-88`
> Se il branch appare nell'output → merge confermato. Se non appare → STOP, verifica manualmente.

Merge PR #104 confermato. Procedo:

| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-git-workflow |
|:---|
| **⚠️ OPERAZIONE DIFFICILE DA ANNULLARE** |
| 🌿 Branch: `feature/SDLC-88-search` · ✅ PR #104 MERGED confermata |
| **▼ Azione** |
| 1. 🗑️ `git branch -d feature/SDLC-88-search` → cancellazione locale |
| 2. 🗑️ `git push origin --delete feature/SDLC-88-search` → cancellazione remote |
| 💡 Perché: Cleanup post-merge, PR confermata |
| 🚫 Se NO: Branch locale e remote restano attivi |

⏸️ **Confermo la cancellazione? ("sì, procedi" / "no, annulla") — non eseguo fino a risposta esplicita.**

**Se merge NON confermato:**
```
⛔ STOP — Branch delete bloccato. HARD-GATE rule #3: mai eliminare un branch prima che il merge sia confermato.
Verifica lo stato della PR e riprova.
```

---

### Caso 9 — `git rebase` su branch condiviso (BLOCCO ASSOLUTO)

**Utente:** fai rebase di `sviluppo` su `main` per allineare

⛔ **STOP — Operazione bloccata prima della pre-flight.**

`git rebase` su `sviluppo` è vietato: `sviluppo` è un branch condiviso. Il rebase riscrive la history e rompe il lavoro di tutti i developer che hanno già basato il loro branch su `sviluppo`.

**Alternativa corretta:**
```bash
# Merge commit — preserva history per tutti
git checkout sviluppo
git merge main
# → questa operazione richiede pre-flight card 🔴 ALTO + ATTENDI
```

Procedo con il merge invece del rebase?

---

## Classificazione Rischio Operazioni

| Operazione              | Rischio    | Card + ATTENDI CONFERMA       |
|-------------------------|------------|-------------------------------|
| `git status/log/diff`   | 🟢 SICURO  | No                            |
| `git add/commit`        | 🟡 MEDIO   | Si — card senza blocco hard   |
| `git push`              | 🔴 ALTO    | Si — ATTENDI risposta esplicita |
| `git merge`             | 🔴 ALTO    | Si — ATTENDI risposta esplicita |
| `git tag` + push (qualsiasi) | 🚨 CRITICO | Si — ATTENDI risposta esplicita · qualsiasi tag triggerizza pipeline |
| `git push --force`      | 🚨 CRITICO | Si — ATTENDI risposta esplicita |
| `git rebase` (condiviso)| 🚨 CRITICO | Si — ATTENDI risposta esplicita |
| `git push origin :refs/tags/*` (rollback) | 🚨 CRITICO | Si — ATTENDI risposta esplicita |
