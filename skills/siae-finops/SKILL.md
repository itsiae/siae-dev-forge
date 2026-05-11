---
name: siae-finops
description: >
  Use when reviewing AWS costs, estimating PR cost impact, verifying tag
  compliance, or identifying idle resources and waste. Analizza costi AWS,
  stima impatto PR, verifica tag compliance e identifica sprechi.
  Trigger: review costi AWS, stima impatto PR, ottimizzazione risorse,
  tag compliance, budget analysis, /forge-cost, /forge-finops, Infracost,
  Steampipe, Cloud Custodian, risorse idle, sprechi.
---

# SIAE FinOps — Cost Visibility & Governance

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║              🔨 DevForge · SIAE FINOPS                          ║
║         "Il codice si forgia. Il developer cresce."             ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 4. Implementation

---

> 📊 **Dai repo itsiae:** Il 71% delle risorse AWS senza tag di cost allocation non viene attribuito a nessun team — costo invisibile.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

## Quando si Applica

**Sempre:**
- Analisi completa costi cloud (AWS o Azure)
- Revisione costi (risorse idle, sprechi, ottimizzazione)
- Stima impatto economico di modifiche Terraform/Terragrunt nelle PR
- Audit tag compliance (risorse senza tag obbligatori)
- Query interattive sui costi da Claude Code
- Setup o configurazione Infracost, Steampipe MCP, Cloud Custodian

**Eccezioni:**
- Per tagging standard e convenzioni .tf/.hcl usa `siae-iac`
- Per security review (IAM, encryption) usa `siae-security`

---

## 0. Analisi Completa — /forge-finops

Questa sezione descrive il flusso operativo principale. Quando l'utente chiede
un'analisi costi, esegui questo flusso **automaticamente**.

### LEGGE ANTI-ALLUCINAZIONE

```
MAI INVENTARE DATI DI COSTO, RISORSE, O METRICHE.
OGNI DATO PRESENTATO DEVE VENIRE DA UN COMANDO ESEGUITO O UNA QUERY REALE.
SE UN TOOL NON E' DISPONIBILE, DILLO — NON INVENTARE L'OUTPUT.
```

### Step 1 — Cloud & Account Detection

🟢 SICURO

Detecta automaticamente quale cloud e' configurato:

```bash
# Prova AWS
aws sts get-caller-identity --output json 2>/dev/null

# Prova Azure
az account show --output json 2>/dev/null
```

**Risultati possibili:**
- Solo AWS → procedi con analisi AWS
- Solo Azure → procedi con analisi Azure
- Entrambi → chiedi all'utente quale analizzare
- Nessuno → guida setup credenziali (aws configure / az login)

Presenta all'utente:
```
CLOUD DETECTATO: AWS
Account:  123456789012 (alias: siae-produzione)
Identity: arn:aws:iam::123456789012:user/lorenzo
Region:   eu-west-1
```

### Step 2 — Dispatch Analisi Parallele (Subagent)

🟡 MEDIO — Mostra pre-flight card

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-finops |
|:---|
| ☁️ Cloud: `<AWS/Azure>` · 🏢 Account: `<account-id>` |
| **▼ Azioni (4 subagent paralleli)** |
| 1. 💰 Agent "Cost Overview" → `aws ce get-cost-and-usage` |
| 2. 🔍 Agent "Idle Resources" → `aws ec2/rds/lambda describe-*` |
| 3. 🏷️ Agent "Tag Compliance" → `aws resourcegroupstaggingapi` |
| 4. 📊 Agent "Optimization" → `aws compute-optimizer` |
| 💡 Perche': Esegue query read-only per identificare sprechi e ottimizzazioni |
| 🚫 Se NO: Nessuna query eseguita |

**Dispatch 4 subagent in parallelo:**
Lancia 4 Agent tool call in un singolo messaggio con `run_in_background: true`:
1. Agent "Cost Overview" — `aws ce get-cost-and-usage`
2. Agent "Idle Resources" — `aws ec2/rds/lambda describe-*`
3. Agent "Tag Compliance" — `aws resourcegroupstaggingapi`
4. Agent "Optimization" — `aws compute-optimizer`

Lancia **subagent paralleli** per le 4 aree di analisi. Ogni subagent:
- Riceve SOLO i comandi/query da eseguire
- Esegue comandi READ-ONLY (nessuna modifica a risorse)
- Riporta SOLO dati reali dall'output dei comandi
- Se un comando fallisce, riporta l'errore — NON inventa dati

**Subagent A — Cost Overview:**
```bash
# AWS
aws ce get-cost-and-usage \
  --time-period Start=$(date -v-30d +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --output json

# Trend mese precedente
aws ce get-cost-and-usage \
  --time-period Start=$(date -v-60d +%Y-%m-%d),End=$(date -v-30d +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --output json
```

**Subagent B — Risorse Idle:**
```bash
# Lambda non invocate (lista + ultima modifica)
aws lambda list-functions --query 'Functions[].{Name:FunctionName,LastModified:LastModified,Runtime:Runtime,MemorySize:MemorySize}' --output table

# EBS non attached
aws ec2 describe-volumes --filters Name=status,Values=available --query 'Volumes[].{ID:VolumeId,Size:Size,Type:VolumeType,Created:CreateTime}' --output table

# Snapshot vecchi
aws ec2 describe-snapshots --owner-ids self --query 'Snapshots[?StartTime<`'$(date -v-180d +%Y-%m-%d)'`].{ID:SnapshotId,Size:VolumeSize,Date:StartTime,Desc:Description}' --output table

# RDS instances
aws rds describe-db-instances --query 'DBInstances[].{ID:DBInstanceIdentifier,Class:DBInstanceClass,Engine:Engine,Status:DBInstanceStatus,MultiAZ:MultiAZ}' --output table
```

**Subagent C — Tag Compliance:**
```bash
# Conta risorse per tag Environment
aws resourcegroupstaggingapi get-resources --tag-filters Key=Environment --query 'length(ResourceTagMappingList)'

# Risorse SENZA tag Environment
aws resourcegroupstaggingapi get-resources --query 'ResourceTagMappingList[?!contains(Tags[].Key, `Environment`)].{ARN:ResourceARN}' --output table | head -20

# Ripeti per Team, CostCenter, Repository
```

**Subagent D — Ottimizzazioni:**
```bash
# Compute Optimizer recommendations (se abilitato)
aws compute-optimizer get-ec2-instance-recommendations --query 'instanceRecommendations[].{ID:instanceArn,Finding:finding,Current:currentInstanceType,Recommended:recommendationOptions[0].instanceType}' --output table 2>/dev/null

# DynamoDB billing mode
aws dynamodb list-tables --output json | jq -r '.TableNames[]' | while read t; do
  aws dynamodb describe-table --table-name "$t" --query 'Table.{Name:TableName,BillingMode:BillingModeSummary.BillingMode,ItemCount:ItemCount,SizeBytes:TableSizeBytes}' --output json
done

# S3 lifecycle rules check
aws s3api list-buckets --query 'Buckets[].Name' --output text | tr '\t' '\n' | while read b; do
  rules=$(aws s3api get-bucket-lifecycle-configuration --bucket "$b" 2>/dev/null | jq '.Rules | length' 2>/dev/null || echo "0")
  echo "$b: $rules lifecycle rules"
done
```

### Step 3 — Aggregazione e Report

🟢 SICURO

Aggrega i risultati dei subagent in un report strutturato:

```
FINOPS ANALYSIS REPORT
══════════════════════════════════════════════════════
Cloud:        <AWS / Azure>
Account:      <account-id> (<alias>)
Region:       <region>
Data:         <YYYY-MM-DD>
══════════════════════════════════════════════════════

1. COST OVERVIEW
   ┌─────────────────────────┬────────────┬────────────┬──────────┐
   │ Servizio                │ Mese Corr. │ Mese Prec. │ Delta    │
   ├─────────────────────────┼────────────┼────────────┼──────────┤
   │ <dati reali da CLI>     │ $X         │ $Y         │ +/-$Z    │
   └─────────────────────────┴────────────┴────────────┴──────────┘

2. SPRECHI IDENTIFICATI
   ┌──────────────────┬──────────────┬───────────────┬──────────────┐
   │ Risorsa          │ Tipo Spreco  │ Costo Stimato │ Azione       │
   ├──────────────────┼──────────────┼───────────────┼──────────────┤
   │ <dati reali>     │ <tipo>       │ $X/mese       │ <azione>     │
   └──────────────────┴──────────────┴───────────────┴──────────────┘

3. TAG COMPLIANCE
   Risorse totali analizzate: N
   ┌──────────────┬───────────┬─────────────┐
   │ Tag          │ Conformi  │ % Compliance │
   ├──────────────┼───────────┼─────────────┤
   │ Environment  │ X/N       │ XX%          │
   └──────────────┴───────────┴─────────────┘

4. OTTIMIZZAZIONI RACCOMANDATE
   Priorita' per risparmio stimato:
   1. [azione] → risparmio $X/mese
   2. [azione] → risparmio $Y/mese

══════════════════════════════════════════════════════
RISPARMIO STIMATO TOTALE: $X/mese
══════════════════════════════════════════════════════
```

**Regole report:**
- OGNI numero nel report deve venire da un comando eseguito
- Se un dato non e' disponibile (comando fallito, permessi), scrivi "N/D" con motivo
- Le stime di risparmio devono essere conservative (stima bassa)
- Citare il comando sorgente per ogni dato: `(fonte: aws ce get-cost-and-usage)`

---

## Prerequisiti

### Obbligatori (analisi base)

| Tool | Scopo | Verifica |
|------|-------|----------|
| AWS CLI | Analisi costi e risorse AWS | `aws sts get-caller-identity` |
| Azure CLI | Analisi costi e risorse Azure | `az account show` |
| jq | Parsing JSON output | `jq --version` |

Basta **uno** tra AWS CLI e Azure CLI. L'analisi completa funziona con soli CLI nativi.

### Opzionali (funzionalita' avanzate)

| Tool | Scopo | Quando serve |
|------|-------|-------------|
| Infracost CLI | Stima costi pre-deploy nelle PR | Solo per /forge-cost su repo Terraform |
| Steampipe + MCP | Query SQL interattive | Alternativa piu' potente ad AWS CLI |
| Cloud Custodian | Governance automatizzata | Solo per enforcement policy automatiche |

**Se AWS/Azure CLI non disponibile:** guida setup (`aws configure` / `az login`).

---

## 1. Shift-Left — Stima Costi Pre-Deploy (Infracost)

### Quando usare

Prima di ogni PR che modifica file `.tf` o `terragrunt.hcl`. Stima l'impatto economico
della modifica PRIMA del deploy. Questo e' l'unico tool esterno che serve: AWS CLI non
puo' stimare i costi di un `terraform plan`.

**Prerequisito:** `infracost` CLI + `INFRACOST_API_KEY` (gratuito: `infracost auth login`)

### Flusso manuale (/forge-cost)

```
REQUIRED SUB-SKILL: siae-iac
```

1. Detecta file Terragrunt/Terraform nella directory corrente
2. Esegui `infracost diff --path=. --format=json --out-file=/tmp/infracost.json`
3. Presenta tabella delta costi per risorsa
4. Se delta > $50/mese → warning con suggerimenti da [infracost-patterns.md](reference/infracost-patterns.md)

### Flusso automatico (GitHub Actions)

Reusable workflow in `.github/workflows/infracost.yml`. Ogni PR su repo HCL
riceve automaticamente un commento con la stima costi. Rollout: 5 righe per repo.

Vedi [infracost-patterns.md](reference/infracost-patterns.md) per setup, usage file templates, e soglie.

---

## 2. Tagging Strategy

```
REQUIRED SUB-SKILL: siae-iac
```

### 6 Tag Obbligatori SIAE

| Tag | Scopo | Valori |
|-----|-------|--------|
| `Environment` | Segregazione ambienti | sviluppo, collaudo, certificazione, produzione |
| `Project` | Raggruppamento progetto | diritti, catalogo, sport, ... |
| `ManagedBy` | Drift detection | Terraform |
| `Team` | Chargeback tra factory | digital-factory, core-platforms, data-platform, devops |
| `CostCenter` | Allocazione finanziaria | CC-XXXX |
| `Repository` | Link al repo GitHub | itsiae/repo-name |

Dettagli implementativi in [tagging-strategy.md](reference/tagging-strategy.md).

### Enforcement Chain

```
Terragrunt config.yaml → Terraform _local.tf → Infracost PR → CUR 2.0 dashboard
```


---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi fix per errore | 2 | Fermati. Diagnosi diversa necessaria. |
| File modificati per singolo step | 5 | Se devi toccare piu' file, decomponi in sub-task. |
| Output max per raccomandazione | 200 righe | Prioritizza. Top 5 issue, non lista esaustiva. |

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "AWS costa poco, non serve ottimizzare" | 816 repo x 4 ambienti x risorse idle = sprechi invisibili che sommano |
| "I costi li vedo dalla console" | La console non e' proattiva. Infracost + Steampipe portano i costi dove lavori |
| "Il tagging lo faccio dopo" | Senza tag, i costi sono un blob unico. Impossibile attribuire responsabilita' |
| "Cloud Custodian e' overkill" | 8 policy base coprono l'80% degli sprechi. Non e' overkill, e' igiene |
| "Dev e collaudo costano poco" | Dev/collaudo attivi 24/7 = 128 ore/settimana pagate per 40 ore usate |
| "L'Infracost comment nelle PR e' rumore" | Un developer informato e' un developer responsabile. Il costo non e' rumore |
| "Lo faccio a mano una volta al mese" | Il controllo manuale dura 1 mese. Le policy automatiche durano per sempre |
| "La stima Infracost non e' precisa" | Una stima imprecisa e' infinitamente meglio di zero visibilita' |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| AWS/Azure CLI read-only (describe, list, get-cost) | 🟢 Sicuro | No |
| Query Steampipe (read-only) | 🟢 Sicuro | No |
| Infracost breakdown/diff | 🟡 Medio | Si (API call esterna) |
| Cloud Custodian dry-run | 🟡 Medio | No |
| Cloud Custodian notify | 🟡 Medio | Si |
| Cloud Custodian enforce (stop/delete) | 🔴 Alto | Si |
| Modifica tag su risorse produzione | 🔴 Alto | Si |

---

## Vincoli

1. **NON** inventare dati — ogni numero deve venire da un comando eseguito
2. **NON** eseguire comandi che MODIFICANO risorse (solo read-only durante analisi)
3. **NON** eseguire policy Custodian con azioni distruttive senza pre-flight card 🔴
4. **SEMPRE** verificare credenziali cloud prima di iniziare (aws sts / az account show)
5. **SEMPRE** presentare risultati in tabella markdown con fonte del dato
6. **SEMPRE** usare subagent paralleli per le 4 aree di analisi (cost, idle, tags, optimization)
7. **SE** un comando fallisce, riporta l'errore e prosegui — non bloccare l'intera analisi
8. **PRE-FLIGHT OBBLIGATORIA** per operazioni con rischio >= 🟡

---

## Risorse Aggiuntive

- [reference/infracost-patterns.md](reference/infracost-patterns.md) — Setup Terragrunt, usage file templates, soglie warning
- [reference/tagging-strategy.md](reference/tagging-strategy.md) — Evoluzione tag 3→6 + enforcement chain + CUR 2.0
