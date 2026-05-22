---
name: siae-add-transient-prefix
description: Aggiunge un nuovo prefix S3 alla event rule EventBridge `transient_relational_new` in modules/transient/eventbridge-new-data.tf seguendo il flusso completo SIAE — crea release+feature branch, applica edit, apre PR draft, mergia in deploy/collaudo, esegue make dev. Trigger - "aggiungi prefix transient", "nuovo prefix bronze", "aggiungi dominio a transient_relational_new", "abilita ingestion {db_name}", "registra prefix EventBridge", "registra dominio EDW".
---

# SIAE Add Transient Prefix — DevForge

> **Tipo:** Rigid | **Fase SDLC:** 3-7 (Branching → Implementation → Release)
>
> Skill end-to-end che incapsula il processo standard per registrare un nuovo
> dominio dati nel routing EventBridge del data lake SIAE: branch setup,
> edit del file `modules/transient/eventbridge-new-data.tf`, PR draft,
> merge in `deploy/collaudo` e deploy `make dev`.

---

## LA LEGGE DI FERRO

```
NESSUN PREFIX SENZA TICKET. NESSUN MERGE SENZA PR. NESSUN DEPLOY SENZA CONFERMA.
```

---

## Input Richiesti

| Parametro | Descrizione | Esempio |
|-----------|-------------|---------|
| `ticket-id` | ID numerico del ticket Jira (senza prefisso area) | `1566` |
| `incremento` | Numero increment formato `NN_NN` | `01_28` |
| `db-name` | Nome dominio/db da aggiungere come prefix S3 (snake_case) | `bm_utilizzazioni` |

**Default fissi (non parametrizzati):**
- `area` = `EDW`
- File target = `modules/transient/eventbridge-new-data.tf`
- Resource target = `aws_cloudwatch_event_rule.transient_relational_new`
- Prefix value = `transient/{db-name}/`

**Branch derivati:**
- Release: `release/EDW_DL_{incremento}` → es. `release/EDW_DL_01_28`
- Feature: `feature/EDW_DL_{incremento}/EDW-{ticket-id}` → es. `feature/EDW_DL_01_28/EDW-1566`

---

## Quando si Applica

**Sempre quando l'utente chiede di:**
- Aggiungere un nuovo dominio dati al routing EventBridge transient
- Registrare un prefix S3 per una nuova ingestion (es. `bm_utilizzazioni`, `accertatori`, `sap_bw`)
- Abilitare un nuovo flusso `transient/{db}/` nel data lake

**Eccezioni — chiedi se:**
- L'utente vuole modificare una event rule diversa da `transient_relational_new`
- Il file modificato non è `modules/transient/eventbridge-new-data.tf`
- Il prefix da aggiungere ha pattern diverso da `transient/{db_name}/`

---

## Step 1 — Valida i Parametri

🟢 SICURO

Verifica:
- `ticket-id`: solo cifre
- `incremento`: formato `NN_NN`
- `db-name`: snake_case minuscolo, solo `[a-z0-9_]`

Se mancanti, chiedi:
```
Parametri necessari:
- ticket-id (es. 1566):
- incremento (formato NN_NN, es. 01_28):
- db-name (es. bm_utilizzazioni):
```

Costruisci:
```
RELEASE_BRANCH=release/EDW_DL_{INCREMENTO}
FEATURE_BRANCH=feature/EDW_DL_{INCREMENTO}/EDW-{TICKET_ID}
PREFIX_VALUE=transient/{DB_NAME}/
```

---

## Step 2 — Verifica Stato Repo

🟢 SICURO

```bash
git status --short
git fetch origin
git ls-remote --heads origin "{RELEASE_BRANCH}" "{FEATURE_BRANCH}" "deploy/collaudo"
grep -n "aws_cloudwatch_event_rule\" \"transient_relational_new\"" modules/transient/eventbridge-new-data.tf
```

Se il file o la resource non esistono → STOP, chiedi all'utente.

Se uno dei branch esiste già → mostra all'utente e chiedi se usare quello esistente.

---

## Step 3 — Pre-flight Card

🔴 ALTO — Mostra card e attendi conferma esplicita.

| 🔴 ALTO — Operazioni multiple su origin · siae-add-transient-prefix |
|:---|
| **⚠️ EFFETTI REMOTI MULTIPLI** |
| **Parametri:** ticket=`EDW-{TICKET_ID}` · increment=`{INCREMENTO}` · db=`{DB_NAME}` |
| **Branch:** `{RELEASE_BRANCH}` · `{FEATURE_BRANCH}` |
| **Prefix da aggiungere:** `{PREFIX_VALUE}` in `transient_relational_new` |
| **▼ Sequenza Azioni** |
| 1. 🌿 Crea + push `{RELEASE_BRANCH}` da `main` |
| 2. 🌿 Crea + push `{FEATURE_BRANCH}` da `{RELEASE_BRANCH}` |
| 3. 📝 Edit `modules/transient/eventbridge-new-data.tf` (aggiunge prefix) |
| 4. 💾 Commit + push su feature branch |
| 5. 📋 Crea PR draft `feature → release` |
| 6. 🔀 Merge feature → `deploy/collaudo` (può richiedere risoluzione conflitti) |
| 7. 🚀 Push `deploy/collaudo` |
| 8. 🚀 `make dev` (lancia pipeline CI/CD su collaudo) |
| 💡 Perché: registra il nuovo dominio nel routing S3→EventBridge |
| 🚫 Se NO: nessuna azione viene eseguita |

⏸️ **ATTENDI CONFERMA ESPLICITA** — "sì, procedi" / "no, annulla". Silenzio ≠ consenso.

---

## Step 4 — Crea Branch Release + Feature

🔴 ALTO

```bash
git checkout main && git pull origin main
git checkout -b {RELEASE_BRANCH}
git push -u origin {RELEASE_BRANCH}
git checkout -b {FEATURE_BRANCH}
git push -u origin {FEATURE_BRANCH}
```

---

## Step 5 — Edit File EventBridge

🟡 MEDIO

Leggi il file `modules/transient/eventbridge-new-data.tf` e localizza l'array `key` dentro `aws_cloudwatch_event_rule.transient_relational_new`. Aggiungi la nuova entry come **ultima** dell'array (mantenere ordine cronologico di registrazione domini), aggiornando la virgola sulla riga precedente.

Pattern Edit:
- **old_string:** ultime 2 righe dell'array (penultima entry + chiusura `]`)
- **new_string:** stesso pattern con virgola aggiunta + nuova entry `{ "prefix" : "{PREFIX_VALUE}" }` + chiusura `]`

Esempio (per `bm_utilizzazioni`):
```hcl
          { "prefix" : "transient/edwh/" },
          { "prefix" : "transient/{DB_NAME}/" }
        ]
```

**Verifica post-edit:** `grep -n "{DB_NAME}" modules/transient/eventbridge-new-data.tf` deve trovare la nuova riga.

---

## Step 6 — Commit + Push + PR Draft

🔴 ALTO

```bash
git add modules/transient/eventbridge-new-data.tf
git commit -m "feat(EDW-{TICKET_ID}): add {DB_NAME} prefix to transient_relational_new event rule

Co-Authored-By: SIAE DevForge"
git push origin {FEATURE_BRANCH}

gh pr create \
  --base {RELEASE_BRANCH} \
  --head {FEATURE_BRANCH} \
  --draft \
  --title "EDW-{TICKET_ID} — increment {INCREMENTO}: add {DB_NAME} prefix" \
  --body "## Summary
- Aggiunge prefix \`transient/{DB_NAME}/\` alla event rule \`transient_relational_new\`
- Abilita routing EventBridge per nuovi oggetti S3 sotto \`transient/{DB_NAME}/\`

## Ticket
EDW-{TICKET_ID}

## Branch
- Base: \`{RELEASE_BRANCH}\`
- Feature: \`{FEATURE_BRANCH}\`

Co-Authored-By: SIAE DevForge"
```

---

## Step 7 — Merge in deploy/collaudo

🔴 ALTO — Mostra mini pre-flight prima di procedere.

> **Nota importante:** il merge diretto su `deploy/collaudo` può essere bloccato dal classifier di auto-mode perché bypassa il PR review. In quel caso, fornire i comandi manuali all'utente.

```bash
git checkout deploy/collaudo
git pull origin deploy/collaudo
git merge --no-ff {FEATURE_BRANCH} -m "Merge {FEATURE_BRANCH} into deploy/collaudo

Co-Authored-By: SIAE DevForge"
```

**Gestione conflitti** (probabile su `eventbridge-new-data.tf` se altri prefix sono stati aggiunti in parallelo):
1. Aprire il file e cercare i marker `<<<<<<< HEAD ... =======  ...>>>>>>>`
2. Risolvere mantenendo **entrambe** le entry (concatenare i prefix)
3. `git add modules/transient/eventbridge-new-data.tf && git commit`

```bash
git push origin deploy/collaudo
```

---

## Step 8 — Deploy `make dev`

🟢 SICURO (la pipeline è gated)

Invoca la skill `siae-datalake-deploy` con argomento `dev`, oppure esegui direttamente:

```bash
make dev
```

Recupera il run ID e monitora:

```bash
sleep 5
gh api "repos/itsiae/dataplatform-datalake-iaac/actions/runs?per_page=1&event=push" \
  | python3 -c "import sys,json; r=json.load(sys.stdin)['workflow_runs'][0]; print(r['id'], r['status'], r['html_url'])"
```

Polling fino a `completed`, poi mostra esito jobs.

**Nota nota:** se la pipeline fallisce con `TEST_COVERAGE_PERCENTAGE variable is not set` o `No merged PR found for commit ...`, è perché il merge diretto su `deploy/collaudo` non passa per PR. Soluzioni:
- Settare la variabile sul repo: `gh variable set TEST_COVERAGE_PERCENTAGE --body "0" --repo itsiae/dataplatform-datalake-iaac`
- Oppure mergiare via PR (release → deploy/collaudo)

---

## Step 9 — Riepilogo Finale

🟢 SICURO

```
✅ Prefix `transient/{DB_NAME}/` registrato su EventBridge
   Ticket: EDW-{TICKET_ID}
   Increment: {INCREMENTO}
   Release: {RELEASE_BRANCH}
   Feature: {FEATURE_BRANCH}
   PR draft: <URL>
   Deploy collaudo: <run URL>
   Esito make dev: <success|failure>
```

---

## Fallback Obbligatori

### Risposta ambigua alla pre-flight
Riformula: *"Confermi? Rispondi 'sì, procedi' oppure 'no, annulla'."*

### Branch già esistente
NON forzare. Chiedere se usare l'esistente, rinominare o annullare.

### Conflitto di merge in deploy/collaudo
Risolvere mantenendo TUTTE le entry esistenti più la nuova. NON sovrascrivere.

### Push bloccato dal classifier
Fornire i comandi esatti all'utente per esecuzione manuale.

### Pipeline `make dev` fallita per coverage
Vedere Step 8 per le opzioni di sblocco. NON modificare il workflow YAML senza esplicita richiesta.

### Resource o file non trovati
STOP immediato. La skill assume struttura repo `dataplatform-datalake-iaac`. Se il repo è diverso, chiedere all'utente.

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realtà |
|----------|--------|
| "Skippo la PR draft, tanto poi mergio direttamente in collaudo" | La PR è il gate audit + traccia il diff per la pipeline coverage |
| "Aggiungo il prefix in mezzo all'array per ordine alfabetico" | L'array è cronologico per registrazione — append in coda |
| "Il conflitto in collaudo lo risolvo prendendo HEAD" | Si perdono i prefix paralleli — concatena SEMPRE |
| "Push diretto su deploy/collaudo è veloce, salto PR" | Bypassa quality gate; classifier bloccherà comunque |
| "Il db-name lo metto in CamelCase" | Il file usa snake_case ovunque — coerenza obbligatoria |
| "Salto la pre-flight, sono operazioni sicure" | Push su origin + merge in branch condiviso = effetti su tutto il team |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Validazione parametri | 🟢 Sicuro | No |
| Fetch + verifica stato | 🟢 Sicuro | No |
| Edit file Terraform | 🟡 Medio | No (incluso in pre-flight Step 3) |
| Push branch su origin | 🔴 Alto | Sì (Step 3) |
| Merge in deploy/collaudo | 🔴 Alto | Sì (Step 3) |
| Push deploy/collaudo | 🔴 Alto | Sì (Step 3) |
| `make dev` (push tag COLLAUDO) | 🟡 Medio | No (gated dalla pipeline) |

---

## Vincoli

1. **MAI** modificare file diversi da `modules/transient/eventbridge-new-data.tf` senza richiesta esplicita
2. **MAI** modificare event rule diverse da `transient_relational_new`
3. **SEMPRE** validare `ticket-id`, `incremento`, `db-name` prima di costruire branch
4. **SEMPRE** PR draft `feature → release` prima del merge in collaudo
5. **PRE-FLIGHT OBBLIGATORIA** per push su origin e merge in deploy/collaudo
6. **MAI** force push (`--force`) senza richiesta esplicita
7. **SEMPRE** risolvere conflitti mantenendo TUTTE le entry esistenti
8. **MAI** modificare il workflow YAML CI/CD per bypassare gate falliti

---

## Esempio Invocazione

```
Utente: "siae-add-transient-prefix 1566 01_28 bm_utilizzazioni"
oppure
Utente: "Aggiungi il prefix per bm_utilizzazioni, ticket EDW-1566 increment 01_28"
```

Output atteso: branch creati, PR #X aperta, merge collaudo eseguito, run pipeline avviato e monitorato.
