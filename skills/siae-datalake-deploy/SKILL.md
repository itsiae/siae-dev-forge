---
name: siae-datalake-deploy
description: >
  Use when launching a CI/CD pipeline for a datalake repo and monitoring its result.
  Trigger: "make dev", "make qa", "make plan_dev", "make plan_qa", "lancia pipeline",
  "deploy dev", "deploy qa", "plan dev", "plan qa", "triggera pipeline",
  "avvia deploy", "esegui deploy", "monitora pipeline".
  Parametro obbligatorio: ambiente = "dev", "qa", "plan_dev" oppure "plan_qa".
---

# SIAE Datalake Deploy

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║          🔨 DevForge · SIAE DATALAKE DEPLOY                   ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 7. Release

---

> 📊 **Dai repo itsiae:** Le pipeline datalake usano tag-based deploy via Makefile.
> Applicabile a: `datalake-{dominio}-etl`, `datalake-{dominio}-iac`, `datalake-{dominio}-ingestion`.

## Input Richiesti

| Parametro | Valori ammessi | Descrizione |
|---|---|---|
| `ambiente` | `dev`, `qa`, `plan_dev`, `plan_qa` | Ambiente target del deploy o del plan |

| Valore | Azione | Tag pushato | Descrizione |
|---|---|---|---|
| `dev` | Deploy | `COLLAUDO` | Deploy Terraform su collaudo (dev AWS) |
| `qa` | Deploy | `CERTIFICAZIONE` | Deploy Terraform su certificazione (qa AWS) |
| `plan_dev` | Plan only | `PLAN-COLLAUDO` | Terraform plan su collaudo senza apply |
| `plan_qa` | Plan only | `PLAN-CERTIFICAZIONE` | Terraform plan su certificazione senza apply |

Se `ambiente` non viene specificato o ha un valore diverso dai quattro ammessi, **fermati e chiedi** prima di procedere. Non assumere un default.

---

## Step 1 — Verifica prerequisiti

🟢 SICURO

### 1.1 — Verifica presenza Makefile

```bash
ls Makefile 2>/dev/null
```

- **Makefile presente** → procedi allo Step 2
- **Makefile assente** → mostra questo messaggio e **FERMATI**:

```
❌ Makefile non trovato nella directory corrente.

Il Makefile è necessario per lanciare la pipeline CI/CD.
Opzioni:
  1. Recuperarlo dal repo di riferimento (datalake-sport-etl o datalake-pmo-iac)
  2. Crearlo con `siae-datalake-etl-setup` o `siae-datalake-iac-setup`

Vuoi che lo recupero o lo creo?
```

### 1.2 — Verifica target Makefile

Controlla che il target `{ambiente}` esista nel Makefile:

```bash
grep -E "^dev:|^qa:" Makefile
```

- Target presente → procedi
- Target assente → segnala che il Makefile non ha il target `{ambiente}` e fermati

### 1.3 — Verifica gh CLI

```bash
gh auth status 2>&1 | grep -E "Logged in|not logged"
```

Se `gh` non è disponibile o non autenticato → segnala e fermati (serve per il monitoring).

---

## Step 2 — Lancio pipeline

🟢 SICURO — esegui direttamente senza chiedere conferma

```bash
make {ambiente}
```

Mappa ambiente → tag:
| ambiente | tag pushato | tag rc (baseline release) |
|---|---|---|
| `dev` | `COLLAUDO` | `rc-COLLAUDO` |
| `qa` | `CERTIFICAZIONE` | `rc-CERTIFICAZIONE` |
| `plan_dev` | `PLAN-COLLAUDO` | `rc-PLAN-COLLAUDO` |
| `plan_qa` | `PLAN-CERTIFICAZIONE` | `rc-PLAN-CERTIFICAZIONE` |

Cattura l'output di `make` e mostralo all'utente.

---

## Step 3 — Recupera Run ID

🟢 SICURO

Subito dopo il push del tag, recupera il run ID della pipeline appena partita:

```bash
gh api "repos/itsiae/{repo}/actions/runs?per_page=1&event=push" \
  | python3 -c "import sys,json; r=json.load(sys.stdin)['workflow_runs'][0]; print(r['id'], r['status'], r['head_sha'][:10])"
```

Mostra il Run ID all'utente e il link diretto:
`https://github.com/itsiae/{repo}/actions/runs/{run-id}`

---

## Step 4 — Monitoring pipeline

🟢 SICURO

Attendi il completamento con polling (ogni 15 secondi, timeout 10 minuti):

```bash
until [ "$(gh api repos/itsiae/{repo}/actions/runs/{run-id} \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")" = "completed" ]; \
  do sleep 15; done
```

Quando completato, mostra il risultato per job:

```bash
gh api repos/itsiae/{repo}/actions/runs/{run-id}/jobs \
  | python3 -c "
import sys,json
d=json.load(sys.stdin)
for j in d['jobs']:
    icon = '✅' if j['conclusion'] == 'success' else '❌' if j['conclusion'] == 'failure' else '⏭️'
    print(f'{icon} {j[\"name\"]} | {j[\"conclusion\"]}')
    for s in j['steps']:
        if s['conclusion'] == 'failure':
            print(f'   └─ FAILED STEP: {s[\"name\"]}')
"
```

**Se tutti i job sono success** → mostra messaggio finale e termina:
```
✅ Deploy {ambiente} completato con successo.
```

**Se uno o più job falliscono** → procedi allo Step 5.

---

## Step 5 — Analisi errore

🟢 SICURO

Recupera i log del job fallito:

```bash
# Ottieni job ID del job fallito
gh api repos/itsiae/{repo}/actions/runs/{run-id}/jobs \
  | python3 -c "
import sys,json
d=json.load(sys.stdin)
for j in d['jobs']:
    if j['conclusion'] == 'failure':
        print(j['id'])
"

# Leggi i log
gh api repos/itsiae/{repo}/actions/jobs/{job-id}/logs 2>&1 \
  | grep -E "Error|error|╷|│|failed|FAILED|cannot|invalid|Invalid|does not|already exist|ResourceAlreadyExists|No such" \
  | grep -v "##\[" \
  | head -60
```

**Analisi immediata** — classifica il tipo di errore:

| Pattern errore | Categoria | Azione tipica |
|---|---|---|
| `vars map does not contain key` | templatefile Terraform — variabile mancante nel .json | Aggiungere la variabile al templatefile() |
| `ResourceAlreadyExistsException` | Risorsa già presente su AWS, non in state | Import block o cancellazione manuale |
| `ExpiredTokenException` | Token AWS scaduto in CI | Verificare credenziali GitHub Actions |
| `refs/tags/rc-{ENV}` 404 | Tag baseline release mancante | Eseguire `make init` |
| `The specified log group does not exist` | Risorsa non presente su AWS | Terraform la creerà al prossimo apply |
| `No changes. Infrastructure is up-to-date` | Nessuna modifica da applicare | Non è un errore — deploy già allineato |
| `Error acquiring the state lock` | State lock DynamoDB attivo | Attendere o sbloccare manualmente |

Dopo l'analisi, proponi la soluzione concreta con i comandi o le modifiche da applicare.

---

## Step 6 — Proposta soluzione

🟡 MEDIO / 🔴 ALTO — dipende dalla soluzione

Presenta la soluzione in modo strutturato:

```
🔍 Errore rilevato: {descrizione breve}
📁 File/risorsa coinvolta: {path o nome risorsa}

💡 Soluzione proposta:
{descrizione della soluzione}

Comandi / modifiche necessarie:
{codice o file da modificare}

Vuoi che applico la soluzione? Rispondi "sì, procedi" oppure "no, annulla".
```

⏸️ **ATTENDI CONFERMA ESPLICITA** prima di applicare qualsiasi modifica o comando.

**Solo dopo "sì, procedi"** → applica la soluzione, poi torna allo **Step 2** per rilanciare il deploy.

---

## Fallback Obbligatori

### Ambiente non valido
Se l'utente specifica un valore diverso da `dev` o `qa`:
```
❌ Ambiente non valido: "{valore}".
Valori ammessi: "dev" oppure "qa".
```

### Run ID non trovato
Se il run non appare nei 30 secondi dopo il push del tag, riprova:
```bash
gh api "repos/itsiae/{repo}/actions/runs?per_page=3&event=push" \
  | python3 -c "import sys,json; [print(r['id'], r['created_at'], r['status']) for r in json.load(sys.stdin)['workflow_runs']]"
```

### Timeout monitoring (> 10 minuti)
Segnala all'utente e mostra il link diretto alla pipeline.

### Errore non classificato
Se l'errore non rientra nella tabella del Step 5, mostra i log grezzi e chiedi all'utente contesto aggiuntivo prima di proporre una soluzione.

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|---|---|---|
| Verifica Makefile e gh CLI | 🟢 Sicuro | No |
| `make {ambiente}` — push tag | 🟢 Sicuro | No |
| Monitoring run (polling) | 🟢 Sicuro | No |
| Lettura log job fallito | 🟢 Sicuro | No |
| Applicazione soluzione (modifica file) | 🟡 Medio | Sì |
| Applicazione soluzione (comando AWS/gh) | 🔴 Alto | Sì |

---

## Vincoli

1. **SOLO** `dev`, `qa`, `plan_dev`, `plan_qa` come valori per `ambiente` — rifiuta tutto il resto
2. **MAI** eseguire `make prod` o `make plan_prod` — bloccato dal Makefile stesso
3. **PRE-FLIGHT OBBLIGATORIA** solo per le soluzioni applicate in caso di errore — NON per `make {ambiente}`
4. **SEMPRE** attendere conferma esplicita prima di applicare soluzioni
5. **SEMPRE** mostrare il Run ID e il link GitHub Actions dopo il lancio
6. **NON** proporre soluzioni senza aver letto i log — analisi prima, proposta dopo
