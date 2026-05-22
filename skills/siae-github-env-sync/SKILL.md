---
name: siae-github-env-sync
description: >
  Use when copying or syncing GitHub Actions environment variables from a
  reference datalake repo to a target datalake repo, or when setting/updating
  a single variable on one or more environments. Trigger: "popola variabili",
  "copia variabili ambiente", "sync env variables", "setup variabili repo",
  "variabili GitHub Actions mancanti", "allinea variabili", "setta variabile",
  "imposta variabile", "aggiorna variabile", "gh variable set".
---

# SIAE GitHub Env Sync

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║          🔨 DevForge · SIAE GITHUB ENV SYNC                    ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 2. Setup Infrastruttura

---

> 📊 **Dai repo itsiae:** I repo datalake con variabili ambiente incomplete causano
> pipeline CD fallite al primo deploy. Allineare le variabili prima del primo push
> evita un ciclo medio di 3 fix iterativi.

## Modalità operative

La skill supporta **due modalità** distinte. Determina quale usare dagli input:

### Modalità A — Set variabile singola

Quando l'utente vuole impostare (o aggiornare) una variabile specifica su uno o più ambienti di un repo.

**Input richiesti:**

| Parametro | Descrizione | Esempio |
|-----------|-------------|---------|
| `repo-target` | Repo su cui scrivere | `datalake-zucchetti-ingestion` |
| `nome-variabile` | Nome della variabile da impostare | `SFTP_FILE_PATTERN` |
| `valore` | Valore da assegnare | `ACCERTAMENTO.csv` |
| `ambienti` | Ambienti target, oppure `all` | `collaudo` oppure `all` |

Se `ambienti=all`, espandi automaticamente a `collaudo,certificazione,produzione`.

Vai direttamente allo **Step A — Set variabile singola**.

---

### Modalità B — Sync completo da repo di riferimento

Quando l'utente vuole copiare tutte le variabili da un repo sorgente a un repo target.

**Input richiesti:**

| Parametro | Descrizione | Esempio |
|-----------|-------------|---------|
| `repo-riferimento` | Repo da cui copiare le variabili | `datalake-pmo-iac` |
| `repo-target` | Repo di destinazione | `datalake-zucchetti-iac` |
| `ambienti` | Lista ambienti da sincronizzare, oppure `all` | `collaudo,certificazione,produzione` oppure `all` (equivalenti) |

Se l'utente specifica `all` per gli ambienti, recupera automaticamente la lista
degli ambienti dalla repo di riferimento.

Vai allo **Step 1** (flusso sync completo).

---

## Step A — Set variabile singola

🔴 ALTO — Mostra pre-flight card prima di eseguire

| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-github-env-sync |
|:---|
| **⚠️ OPERAZIONE DIFFICILE DA ANNULLARE** |
| 📋 Repo: `itsiae/{repo-target}` · 🌍 Ambienti: `{lista-ambienti}` |
| **▼ Azione** |
| 1. 🔧 Imposta `{nome-variabile}={valore}` su tutti gli ambienti indicati |
| 💡 Perché: Aggiornamento variabile GitHub Actions richiesto dall'utente |
| 🚫 Se NO: Nessuna variabile viene modificata |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

**Solo dopo "sì, procedi"**, per ogni ambiente:

1. Verifica se la variabile esiste già (GET):

```bash
gh api "repos/itsiae/{repo-target}/environments/{env}/variables/{nome-variabile}" 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('exists')" 2>/dev/null || echo "missing"
```

2. Se esiste → PATCH, se non esiste → POST:

```bash
# Crea (POST) se non esiste
gh api -X POST "repos/itsiae/{repo-target}/environments/{env}/variables" \
  --field name="{nome-variabile}" --field value="{valore}"

# Aggiorna (PATCH) se esiste
gh api -X PATCH "repos/itsiae/{repo-target}/environments/{env}/variables/{nome-variabile}" \
  --field name="{nome-variabile}" --field value="{valore}"
```

3. Verifica post-operazione — rileggi e mostra il valore effettivo:

```bash
for env in {lista-ambienti}; do
  echo "--- $env ---"
  gh api "repos/itsiae/{repo-target}/environments/${env}/variables" \
    --jq ".variables[] | select(.name==\"{nome-variabile}\") | \"\(.name)=\(.value)\""
done
```

Mostra tabella riepilogativa finale con ✅ per ogni ambiente aggiornato correttamente.

---

---

## Step 1 — Verifica prerequisiti

🟢 SICURO

Verifica che `gh` sia disponibile e autenticata. Se `siae-git-env` è già stata
eseguita nella sessione, usa il GH_MODE già determinato.

```bash
gh auth status 2>&1
```

---

## Step 2 — Scopri gli ambienti

🟢 SICURO

Se `ambienti=all`, recupera la lista dalla repo di riferimento:

```bash
gh api repos/itsiae/{repo-riferimento}/environments \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(v['name']) for v in d.get('environments',[])]"
```

Se l'utente ha specificato una lista esplicita, usa quella direttamente.

Mostra all'utente gli ambienti che verranno sincronizzati e attendi conferma se
la lista è diversa da quanto atteso.

---

## Step 3 — Leggi variabili dalla repo di riferimento

🟢 SICURO

⚠️ **OBBLIGATORIO: usa sempre `?per_page=100`** — la GitHub API restituisce di default
solo i primi 10 risultati anche se `total_count` indica un numero maggiore. Senza
questo parametro il delta sarà incompleto e le variabili mancanti verranno sovrastimate.

Per ogni ambiente, recupera le variabili dalla repo di riferimento:

```bash
gh api "repos/itsiae/{repo-riferimento}/environments/{env}/variables?per_page=100" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f\"{v['name']}={v['value']}\") for v in d.get('variables',[])]"
```

Mostra all'utente una tabella riepilogativa con tutti i valori trovati, organizzata
per ambiente:

| Variabile | {env-1} | {env-2} | {env-3} |
|-----------|---------|---------|---------|
| `AWS_ENV` | `dev` | `qa` | `prod` |
| ... | ... | ... | ... |

---

## Step 4 — Leggi stato attuale della repo target

🟢 SICURO

Anche qui usa `?per_page=100` per leggere tutte le variabili già presenti:

```bash
gh api "repos/itsiae/{repo-target}/environments/{env}/variables?per_page=100" 2>&1 \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(v['name']) for v in d.get('variables',[])]"
```

Calcola il **delta**: variabili mancanti nel target rispetto al riferimento.

Mostra il delta all'utente:
- ✅ Già presenti (non verranno toccate)
- ❌ Mancanti (verranno create)
- ⚠️ Presenti ma con valore diverso (chiedi conferma prima di sovrascrivere)

---

## Step 5 — Applica il sync

🔴 ALTO — Mostra pre-flight card prima di eseguire

| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-github-env-sync |
|:---|
| **⚠️ OPERAZIONE DIFFICILE DA ANNULLARE** |
| 📋 Repo target: `itsiae/{repo-target}` · 🌍 Ambienti: `{lista-ambienti}` |
| **▼ Azione** |
| 1. 🔧 Crea variabili mancanti → `{N-variabili}` variabili su `{N-ambienti}` ambienti |
| 2. ⚠️ Sovrascrive variabili con valore diverso (solo se confermato al Step 4) |
| 💡 Perché: Allineamento variabili GitHub Actions necessario per pipeline CD |
| 🚫 Se NO: Nessuna variabile viene creata o modificata nel target |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

**Solo dopo "sì, procedi"**, per ogni variabile mancante:

```bash
# Crea variabile (POST)
gh api --method POST repos/itsiae/{repo-target}/environments/{env}/variables \
  -f name={NOME} -f value='{VALORE}'

# Aggiorna variabile esistente (PATCH)
gh api --method PATCH repos/itsiae/{repo-target}/environments/{env}/variables/{NOME} \
  -f name={NOME} -f value='{VALORE}'
```

---

## Step 6 — Verifica post-sync

🟢 SICURO

Rileggi le variabili dalla repo target e confronta con il riferimento.
Mostra tabella comparativa finale con status ✅/❌ per ogni variabile.

```bash
for env in {lista-ambienti}; do
  echo "=== $env ==="
  gh api "repos/itsiae/{repo-target}/environments/$env/variables?per_page=100" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f\"  {v['name']}={v['value']}\") for v in d.get('variables',[])]"
done
```

Se ci sono ancora discrepanze, segnalale esplicitamente con i passi per risolverle.

---

## Fallback Obbligatori

### Risposta ambigua dell'utente alla card
Se l'utente non risponde con "sì, procedi" o "no, annulla": NON eseguire.
Chiedere: *"Confermo il sync? Rispondi 'sì, procedi' oppure 'no, annulla'."*

### gh CLI non disponibile
Se `gh` non è autenticata, mostra i comandi equivalenti via API REST curl che
l'utente può eseguire manualmente nel suo terminale.

### Variabile con valore diverso tra ambienti
Se una variabile ha lo stesso nome ma valori diversi tra riferimento e target
(es. `CRON_SCHED` personalizzato), NON sovrascrivere automaticamente.
Mostra il confronto e chiedi all'utente quale valore vuole mantenere.

### Ambiente non presente nella repo target
Se un ambiente esiste nel riferimento ma non nel target, segnalalo e chiedi
se crearlo prima di procedere.

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura variabili repo riferimento | 🟢 Sicuro | No |
| Lettura stato attuale repo target | 🟢 Sicuro | No |
| Calcolo delta mancanti | 🟢 Sicuro | No |
| Creazione variabili mancanti (POST) | 🔴 Alto | Sì |
| Sovrascrittura variabili esistenti (PATCH) | 🔴 Alto | Sì |

---

## Regola Speciale — STEPFUN_CRON_STATUS / CRON_SCHED_STATUS

Il comportamento dipende dal tipo di repo target:

### Repo `datalake-{dominio}-iac`

⚠️ **OBBLIGATORIO** — dopo il sync, indipendentemente dal valore nel repo di riferimento,
imposta **sempre** `false` per `CRON_SCHED_STATUS` e `STEPFUN_CRON_STATUS` (se presente) su tutti gli ambienti:

```bash
for env in {lista-ambienti}; do
  gh api --method PATCH "repos/itsiae/{repo-target}/environments/$env/variables/CRON_SCHED_STATUS" \
    -f name=CRON_SCHED_STATUS -f value=false 2>/dev/null

  # Solo se presente nel target
  gh api --method PATCH "repos/itsiae/{repo-target}/environments/$env/variables/STEPFUN_CRON_STATUS" \
    -f name=STEPFUN_CRON_STATUS -f value=false 2>/dev/null
done
```

**Perché:** i repo IaC non devono mai avere scheduler o Step Function abilitati automaticamente
su un repo nuovo — i valori `true`/`ENABLED` vanno impostati manualmente dopo il primo deploy validato.

### Repo `datalake-{dominio}-etl`

⚠️ **OBBLIGATORIO** — dopo il sync, indipendentemente dal valore nel repo di riferimento,
imposta **sempre** `DISABLED` per `STEPFUN_CRON_STATUS` e `CRON_SCHED_STATUS` su tutti gli ambienti:

```bash
for env in {lista-ambienti}; do
  gh api --method PATCH "repos/itsiae/{repo-target}/environments/$env/variables/STEPFUN_CRON_STATUS" \
    -f name=STEPFUN_CRON_STATUS -f value=DISABLED 2>/dev/null

  gh api --method PATCH "repos/itsiae/{repo-target}/environments/$env/variables/CRON_SCHED_STATUS" \
    -f name=CRON_SCHED_STATUS -f value=DISABLED 2>/dev/null
done
```

**Perché:** un deploy su un repo ETL nuovo non deve mai abilitare automaticamente
la Step Function — rischierebbe di triggerare pipeline in modo inaspettato.
Il valore `ENABLED` va impostato manualmente dopo il primo deploy validato.

### Altri tipi di repo

Copia il valore dal repo di riferimento senza override.

---

## Vincoli

1. **MAI** sovrascrivere variabili già presenti nel target senza conferma esplicita
2. **SEMPRE** mostrare il delta prima di applicare modifiche
3. **SEMPRE** verificare post-sync con lettura effettiva dal target
4. **NON** modificare variabili nella repo di riferimento — solo lettura
5. **PRE-FLIGHT OBBLIGATORIA** per qualsiasi operazione di scrittura (POST/PATCH)
6. **SEMPRE** applicare la Regola Speciale scheduler dopo il sync: `false` per repo `datalake-{dominio}-iac`, `DISABLED` per repo `datalake-{dominio}-etl`, valore dal riferimento per gli altri

---

## Risorse Aggiuntive

- [reference/gh-api-variables.md](reference/gh-api-variables.md) — Comandi gh API per variabili GitHub Actions
