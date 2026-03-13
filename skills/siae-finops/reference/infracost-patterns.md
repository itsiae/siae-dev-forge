# Infracost Patterns — Setup Terragrunt + Usage File Templates

> Reference per la skill `siae-finops`. Contiene setup Infracost per repo Terragrunt SIAE,
> usage file templates con valori tipici per servizi AWS, integrazione GitHub Actions,
> soglie di warning e checklist ottimizzazioni.

---

## 1. Setup Infracost + Terragrunt

### Installazione e Autenticazione

```bash
# Installazione
brew install infracost

# Autenticazione (gratuito, richiede account Infracost Cloud)
infracost auth login

# Verifica
infracost --version
infracost configure get api_key
```

### Configurazione `infracost.yml`

Creare `infracost.yml` nella root del repo IaC per gestire multi-environment:

```yaml
version: 0.1

projects:
  - path: live/sviluppo
    name: sviluppo
    usage_file: infracost-usage.yml
    terraform_binary: terragrunt
    terraform_plan_flags: "--terragrunt-working-dir live/sviluppo"

  - path: live/collaudo
    name: collaudo
    usage_file: infracost-usage.yml
    terraform_binary: terragrunt
    terraform_plan_flags: "--terragrunt-working-dir live/collaudo"

  - path: live/certificazione
    name: certificazione
    usage_file: infracost-usage.yml
    terraform_binary: terragrunt
    terraform_plan_flags: "--terragrunt-working-dir live/certificazione"

  - path: live/produzione
    name: produzione
    usage_file: infracost-usage-prod.yml
    terraform_binary: terragrunt
    terraform_plan_flags: "--terragrunt-working-dir live/produzione"
```

> **Nota:** Produzione usa un usage file separato (`infracost-usage-prod.yml`) perche' i volumi di traffico sono significativamente diversi.

### Comandi Base

```bash
# Stima costi singolo ambiente
infracost breakdown --path=live/sviluppo \
  --terraform-binary=terragrunt \
  --usage-file=infracost-usage.yml

# Stima tutti gli ambienti (usa infracost.yml)
infracost breakdown --config-file=infracost.yml

# Diff tra branch corrente e base (per PR)
infracost diff --path=live/sviluppo \
  --terraform-binary=terragrunt \
  --usage-file=infracost-usage.yml \
  --compare-to=/tmp/infracost-base.json

# Output JSON per analisi programmatica
infracost breakdown --path=live/sviluppo \
  --terraform-binary=terragrunt \
  --usage-file=infracost-usage.yml \
  --format=json --out-file=/tmp/infracost.json

# Output tabella leggibile
infracost output --path=/tmp/infracost.json --format=table
```

### Gestione Multi-Environment

I repo Terragrunt SIAE seguono la struttura `live/{ambiente}/terragrunt.hcl` con moduli in `modules/`. Per stimare correttamente:

1. **Singolo ambiente** — `infracost breakdown --path=live/sviluppo`
2. **Tutti gli ambienti** — usa `infracost.yml` con un `projects` entry per ambiente
3. **Diff PR** — genera baseline dal base branch, poi diff dal PR branch

```bash
# Workflow completo per diff PR
git stash
infracost breakdown --path=live/sviluppo \
  --terraform-binary=terragrunt \
  --usage-file=infracost-usage.yml \
  --format=json --out-file=/tmp/infracost-base.json
git stash pop

infracost diff --path=live/sviluppo \
  --terraform-binary=terragrunt \
  --usage-file=infracost-usage.yml \
  --compare-to=/tmp/infracost-base.json
```

---

## 2. Usage File Template

Infracost non puo' stimare servizi usage-based (Lambda, DynamoDB, Glue, S3 requests) senza un **usage file**. I template seguenti contengono valori tipici per i workload SIAE.

### `infracost-usage.yml` (ambienti non-prod: sviluppo, collaudo, certificazione)

```yaml
version: 0.1

resource_type_default_usage:

  ##############################################
  # Lambda — Stime per ambiente non-produzione
  ##############################################
  aws_lambda_function:
    # API-triggered Lambda (es. CRUD, API Gateway backend)
    monthly_requests: 100000            # 100k invocazioni/mese
    request_duration_ms: 200            # 200ms durata media
    # Batch/scheduled Lambda (es. ETL trigger, cron)
    # Sovrascrivere per-risorsa se necessario

  ##############################################
  # DynamoDB — Stime per ambiente non-produzione
  ##############################################
  aws_dynamodb_table:
    # Modalita' PAY_PER_REQUEST (on-demand) — tipica per dev
    monthly_read_request_units: 50000    # 50k RRU/mese
    monthly_write_request_units: 10000   # 10k WRU/mese
    storage_gb: 1                        # 1 GB storage

  ##############################################
  # Glue — Stime per job bronze-to-silver
  ##############################################
  aws_glue_job:
    # Worker type: G.1X (4 vCPU, 16 GB) con FLEX execution
    number_of_dpus: 2                    # 2 DPU per job
    monthly_hours: 10                    # 10 DPU-hours/mese (job brevi, pochi run)

  ##############################################
  # S3 — Stime per ambiente non-produzione
  ##############################################
  aws_s3_bucket:
    storage_gb: 50                       # 50 GB dati
    monthly_tier_1_requests: 10000       # 10k PUT/COPY/POST/LIST
    monthly_tier_2_requests: 50000       # 50k GET/SELECT
    monthly_select_data_scanned_gb: 5    # 5 GB S3 Select

resource_usage:

  ##############################################
  # Override per-risorsa (Lambda specifiche)
  ##############################################

  # Lambda batch/scheduled — meno invocazioni, durata piu' lunga
  # Decommentare e adattare al nome risorsa nel modulo TF:
  #
  # module.lambda.aws_lambda_function.batch_processor:
  #   monthly_requests: 10000            # 10k invocazioni/mese (batch)
  #   request_duration_ms: 5000          # 5s durata media (elaborazione pesante)

  # Lambda API ad alto traffico — piu' invocazioni
  # module.api.aws_lambda_function.api_handler:
  #   monthly_requests: 500000           # 500k invocazioni/mese
  #   request_duration_ms: 150           # 150ms (API veloce)
```

### `infracost-usage-prod.yml` (ambiente produzione)

```yaml
version: 0.1

resource_type_default_usage:

  ##############################################
  # Lambda — Stime produzione
  ##############################################
  aws_lambda_function:
    monthly_requests: 1000000           # 1M invocazioni/mese
    request_duration_ms: 200            # 200ms durata media

  ##############################################
  # DynamoDB — Stime produzione
  ##############################################
  aws_dynamodb_table:
    monthly_read_request_units: 500000   # 500k RRU/mese
    monthly_write_request_units: 100000  # 100k WRU/mese
    storage_gb: 50                       # 50 GB storage

  ##############################################
  # Glue — Stime produzione (job piu' frequenti)
  ##############################################
  aws_glue_job:
    number_of_dpus: 4                    # 4 DPU per job (dataset piu' grandi)
    monthly_hours: 60                    # 60 DPU-hours/mese

  ##############################################
  # S3 — Stime produzione
  ##############################################
  aws_s3_bucket:
    storage_gb: 500                      # 500 GB dati
    monthly_tier_1_requests: 100000      # 100k PUT/COPY/POST/LIST
    monthly_tier_2_requests: 1000000     # 1M GET/SELECT
    monthly_select_data_scanned_gb: 50   # 50 GB S3 Select

resource_usage:

  # Override specifici per risorse produzione ad alto volume
  # Decommentare e adattare:
  #
  # module.lambda.aws_lambda_function.api_handler:
  #   monthly_requests: 5000000         # 5M invocazioni/mese (API ad alto traffico)
  #   request_duration_ms: 100          # 100ms (ottimizzata)
  #
  # module.datalake.aws_s3_bucket.raw:
  #   storage_gb: 2000                  # 2 TB data lake raw layer
  #   monthly_tier_1_requests: 500000   # 500k write (ingestion)
  #   monthly_tier_2_requests: 2000000  # 2M read (ETL + query)
```

### Guida ai Valori

| Servizio | Metrica | Non-Prod | Produzione | Note |
|----------|---------|----------|------------|------|
| Lambda (API) | invocazioni/mese | 100k | 1M | Scaling lineare con traffico utenti |
| Lambda (batch) | invocazioni/mese | 10k | 100k | Scheduling: cron giornaliero o event-driven |
| Lambda | durata media (ms) | 200 | 200 | Simile tra ambienti se stessa configurazione |
| DynamoDB | RRU/mese | 50k | 500k | On-demand (PAY_PER_REQUEST) per dev, valutare provisioned per prod |
| DynamoDB | WRU/mese | 10k | 100k | Rapporto lettura:scrittura tipico 5:1 |
| DynamoDB | storage (GB) | 1 | 50 | Crescita ~5 GB/mese in prod |
| Glue | DPU | 2 (G.1X) | 4 (G.1X) | FLEX execution class per costo ridotto |
| Glue | DPU-hours/mese | 10 | 60 | Job bronze-to-silver: ~15 min/run, 1-4 run/giorno |
| S3 | storage (GB) | 50 | 500 | Raw + processed + archive layers |
| S3 | PUT requests/mese | 10k | 100k | Ingestion + ETL output |
| S3 | GET requests/mese | 50k | 1M | ETL read + API serving + analytics |

---

## 3. GitHub Actions Integration

### Richiamo del Reusable Workflow

Ogni repo Terragrunt SIAE puo' integrare la stima costi nelle PR aggiungendo queste righe al proprio workflow CI:

```yaml
# .github/workflows/ci.yml (nel repo consumer)
name: CI

on:
  pull_request:
    paths:
      - '**/*.tf'
      - '**/*.hcl'
      - '**/terragrunt.hcl'

jobs:
  cost-estimate:
    uses: itsiae/siae-dev-forge/.github/workflows/infracost.yml@main
    with:
      terragrunt_path: "live/"
    secrets:
      INFRACOST_API_KEY: ${{ secrets.INFRACOST_API_KEY }}
```

### Setup Prerequisiti (una tantum per org)

1. **Org secret GitHub**: `INFRACOST_API_KEY` come org-level secret (`Settings > Secrets > Actions`)
2. **Workflow pubblicato**: il reusable workflow e' in `itsiae/siae-dev-forge/.github/workflows/infracost.yml`
3. **Per-repo**: aggiungere le 5 righe del job `cost-estimate` nel workflow CI del repo

### Comportamento Atteso

- La PR riceve un **commento automatico** con tabella costi (risorsa, costo attuale, costo nuovo, delta)
- Se il delta supera la soglia configurata (default `$50/mese`) viene aggiunta la **label `cost-impact`** alla PR
- Il commento si aggiorna automaticamente ad ogni push sulla PR

### Customizzazione per Repo

```yaml
jobs:
  cost-estimate:
    uses: itsiae/siae-dev-forge/.github/workflows/infracost.yml@main
    with:
      terragrunt_path: "live/"
      threshold: 100           # Soglia custom (default: 50)
    secrets:
      INFRACOST_API_KEY: ${{ secrets.INFRACOST_API_KEY }}
```

---

## 4. Soglie di Warning

Tabella threshold per delta costi mensili stimati da Infracost.

| Livello | Delta Mensile | Azione | Visualizzazione |
|---------|---------------|--------|-----------------|
| Info | < $10/mese | Log nel commento PR, nessun alert | Tabella costi standard |
| Warning | $10 - $50/mese | Evidenzia nel commento PR | Riga evidenziata con nota |
| Alert | $50 - $200/mese | Label `cost-impact` sulla PR + nota nel commento | Label PR + sezione "Cost Alert" nel commento |
| Critical | > $200/mese | Label `cost-impact` + richiesta review FinOps | Label PR + sezione "Critical Cost Impact" + menzione team FinOps |

### Configurazione Soglie

Le soglie sono configurabili nel reusable workflow tramite input `threshold` (default: `50`). Per configurazione granulare, usare `infracost.yml`:

```yaml
# infracost.yml — sezione opzionale per policy
version: 0.1

projects:
  - path: live/sviluppo
    name: sviluppo
    usage_file: infracost-usage.yml
    terraform_binary: terragrunt
```

### Interpretazione Risultati

| Scenario | Esempio | Azione Suggerita |
|----------|---------|------------------|
| Nuova Lambda + API GW | +$5/mese | Info — nessuna azione |
| Nuova RDS db.r5.xlarge | +$180/mese | Alert — valutare sizing, ambiente dev potrebbe usare db.t3.medium |
| Nuovo cluster ECS 3 task | +$350/mese | Critical — review architettura, valutare Fargate Spot o right-sizing |
| DynamoDB provisioned 1000 RCU | +$70/mese | Alert — valutare PAY_PER_REQUEST se traffico variabile |
| Glue G.2X 10 worker | +$120/mese | Alert — valutare G.1X FLEX, ridurre worker, auto-scaling |

---

## 5. Ottimizzazioni Comuni

Checklist da consultare quando il delta costi supera la soglia di warning.

### Compute

- [ ] **Lambda memory right-sizing** — Usa AWS Lambda Power Tuning per trovare il rapporto costo/prestazione ottimale. Spesso 256 MB e' sufficiente per API CRUD; oltre 512 MB solo se giustificato da profiling
- [ ] **Lambda ARM64 (Graviton2)** — 20% piu' economico di x86_64 a parita' di prestazioni. Compatibile con la maggior parte dei runtime (Node.js, Python, Java 11+)
- [ ] **ECS Fargate Spot** — Fino al 70% di sconto per workload fault-tolerant (batch, worker). Non usare per API sincrone
- [ ] **Reserved Instances (RI)** — Per RDS e ElastiCache con workload stabile (>70% utilizzo). Commitment 1 anno = ~30% sconto, 3 anni = ~50%
- [ ] **Savings Plans** — Compute Savings Plans per Lambda e Fargate. Commitment basato su $/hour, piu' flessibile di RI

### Database

- [ ] **DynamoDB PAY_PER_REQUEST vs PROVISIONED** — Usare PAY_PER_REQUEST (on-demand) per traffico imprevedibile o <25% capacita' provisioned. Passare a PROVISIONED con auto-scaling quando il pattern e' stabile e >25% utilizzo
- [ ] **DynamoDB Reserved Capacity** — Per tabelle produzione con traffico stabile: 1 anno RC = ~53% sconto su WCU/RCU provisioned
- [ ] **RDS right-sizing** — Monitorare CPU media per 14 giorni. Se <20%, scendere di instance class (es. r5.xlarge -> r5.large). Dev/collaudo: usare db.t3.medium o t3.small

### Data & Analytics

- [ ] **Glue FLEX execution class** — Fino al 35% piu' economico di STANDARD per job non time-critical. Ideale per ETL bronze-to-silver batch. Worker type G.1X (non G.2X) per la maggior parte dei job
- [ ] **Glue auto-scaling** — Abilitare `--enable-auto-scaling` per ridurre DPU inutilizzati. Max workers come cap, non come default
- [ ] **S3 Intelligent-Tiering** — Per bucket con pattern di accesso imprevedibile. Nessun costo di retrieval, solo $0.0025/1000 oggetti di monitoring. Ideale per data lake
- [ ] **S3 Lifecycle Rules** — Transizione a Glacier dopo 90 giorni per dati archiviati. Delete automatico di oggetti temporanei dopo 30 giorni

### Ambienti Non-Produzione

- [ ] **Off-hours scheduling** — Spegnere risorse sviluppo/collaudo fuori orario (20:00-08:00 CET, weekend). Risparmio ~65% su RDS, ECS, EC2. Vedi policy Cloud Custodian `off-hours-dev`
- [ ] **Sizing ridotto per dev** — Dev non necessita dello stesso sizing di produzione. Regola: dev = 1/4 della capacita' prod, collaudo = 1/2
- [ ] **Ambienti on-demand** — Per certificazione, valutare infrastruttura effimera (create/destroy per ciclo di test) anziche' always-on

### Network & Transfer

- [ ] **VPC Endpoints** — Gateway endpoints per S3 e DynamoDB (gratuiti). Interface endpoints per altri servizi AWS riducono costi NAT Gateway
- [ ] **NAT Gateway sharing** — Un singolo NAT Gateway per VPC (non per subnet). In dev, valutare NAT Instance (t3.nano) se traffico basso
- [ ] **CloudFront caching** — Per API pubbliche, abilitare caching sulle risposte GET. Riduce invocazioni Lambda/API Gateway e costi di transfer
