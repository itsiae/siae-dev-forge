# Tagging Strategy SIAE — Evoluzione 3 → 6 Tag

> Reference per skill `siae-finops` — Evoluzione tagging AWS, implementazione Terragrunt,
> enforcement chain, rollout graduale, CUR 2.0 + Athena, dashboard costi.

---

## 1. Tag Attuali vs Nuovi

Evoluzione da 3 tag storici a 6 tag obbligatori per abilitare chargeback, cost allocation e governance.

| Tag | Stato | Scopo | Valori ammessi | Enforcement |
|-----|-------|-------|----------------|-------------|
| `Environment` | Esistente | Segregazione ambienti | `sviluppo`, `collaudo`, `certificazione`, `produzione` | Terragrunt |
| `Project` | Esistente | Raggruppamento progetto | Stringa libera (es. `diritti`, `catalogo`, `sport`) | Terragrunt |
| `ManagedBy` | Esistente | Drift detection | `Terraform` (valore fisso) | Terragrunt |
| `Team` | **NUOVO** | Chargeback tra factory | `digital-factory`, `core-platforms`, `data-platform`, `devops` | Terragrunt + Custodian |
| `CostCenter` | **NUOVO** | Allocazione finanziaria | Formato `CC-XXXX` (es. `CC-1001`) | Terragrunt + Custodian |
| `Repository` | **NUOVO** | Link al repo sorgente | Formato `org/repo-name` (es. `itsiae/diritti-iaac`) | Terragrunt + Custodian |

**Retrocompatibilita':** i 3 tag esistenti restano invariati. I 3 nuovi si aggiungono senza breaking change.

---

## 2. Implementazione Terragrunt

### 2.1 Common Tags in `_local.tf`

Tutti e 6 i tag definiti in un unico blocco `locals`, applicato a ogni risorsa tramite `merge()`:

```hcl
# _local.tf — common_tags per tutti i moduli
locals {
  config = yamldecode(file(find_in_parent_folders("config.yaml")))

  common_tags = {
    Environment = var.env
    Project     = var.project
    ManagedBy   = "Terraform"
    Team        = var.team
    CostCenter  = var.cost_center
    Repository  = var.repository
  }
}
```

Applicazione sulle risorse:

```hcl
resource "aws_s3_bucket" "example" {
  bucket = "${local.prefix}-example"

  tags = merge(local.common_tags, {
    # Tag aggiuntivi specifici della risorsa (opzionali)
    Component = "storage"
  })
}
```

### 2.2 Variabili in `_input.tf` con Validation Block

```hcl
# _input.tf — variabili standard (esistenti)
variable "env" {
  description = "Ambiente di deploy"
  type        = string
}

variable "project" {
  description = "Nome progetto SIAE"
  type        = string
}

# _input.tf — nuove variabili FinOps

variable "team" {
  description = "Factory/team owner della risorsa per chargeback"
  type        = string
  validation {
    condition     = contains(["digital-factory", "core-platforms", "data-platform", "devops"], var.team)
    error_message = "Team deve essere uno tra: digital-factory, core-platforms, data-platform, devops"
  }
}

variable "cost_center" {
  description = "Centro di costo per allocazione finanziaria (formato CC-XXXX)"
  type        = string
  validation {
    condition     = can(regex("^CC-[0-9]{4}$", var.cost_center))
    error_message = "CostCenter deve essere nel formato CC-XXXX (es. CC-1001)"
  }
}

variable "repository" {
  description = "Repository GitHub sorgente nel formato org/repo-name"
  type        = string
}
```

### 2.3 Esempio `config.yaml` con i Nuovi Campi

```yaml
# config.yaml — alla root del repo Terragrunt
project: diritti
aws_region: eu-west-1
repo_name: diritti-iaac

# --- Nuovi campi FinOps ---
team: digital-factory
cost_center: CC-1001
repository: itsiae/diritti-iaac

# --- Per-environment ---
environments:
  sviluppo:
    account_id: "111111111111"
  collaudo:
    account_id: "222222222222"
  certificazione:
    account_id: "333333333333"
  produzione:
    account_id: "444444444444"
```

Lettura nel `terragrunt.hcl`:

```hcl
inputs = {
  env         = local.env
  project     = local.config.project
  team        = local.config.team
  cost_center = local.config.cost_center
  repository  = local.config.repository
}
```

---

## 3. Valori Ammessi

### 3.1 Team — Le 4 Factory SIAE

| Valore tag | Factory | Descrizione | Repo tipici |
|------------|---------|-------------|-------------|
| `digital-factory` | Digital Factory | Servizi digitali rivolti al pubblico (diritti, catalogo, sport) | ~200 repo |
| `core-platforms` | Core Platforms | Piattaforme core enterprise (anagrafica, contabilita', HR) | ~150 repo |
| `data-platform` | Data Platform | Data lake, ETL, analytics, ML pipelines | ~100 repo |
| `devops` | DevOps | Infrastruttura condivisa, CI/CD, monitoring, IAM | ~50 repo |

### 3.2 CostCenter — Formato e Mappatura

**Formato:** `CC-XXXX` dove `XXXX` e' un codice numerico a 4 cifre.

| Team | CostCenter | Note |
|------|------------|------|
| `digital-factory` | `CC-1001` | Centro di costo Digital Factory |
| `core-platforms` | `CC-1002` | Centro di costo Core Platforms |
| `data-platform` | `CC-1003` | Centro di costo Data Platform |
| `devops` | `CC-1004` | Centro di costo DevOps (infra condivisa) |

> I codici sopra sono esemplificativi. I codici reali vanno allineati con l'ufficio
> amministrazione/finance. La mappatura 1:1 team-to-cost-center e' il caso base;
> in futuro un team potrebbe avere piu' cost center per sotto-progetto.

### 3.3 Repository — Formato

**Formato:** `org/repo-name` (es. `itsiae/diritti-iaac`)

- `org` = organizzazione GitHub (sempre `itsiae` per SIAE)
- `repo-name` = nome esatto del repository GitHub
- Deve corrispondere al repository che contiene il codice IaC che genera le risorse

---

## 4. Enforcement Chain

Diagramma testuale del flusso di enforcement end-to-end:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ENFORCEMENT CHAIN                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. Terragrunt config.yaml                                              │
│     │  Definisce: team, cost_center, repository                        │
│     │  Validation: Terraform variable validation block                  │
│     ▼                                                                   │
│  2. Terraform _local.tf                                                 │
│     │  Applica: common_tags su OGNI risorsa AWS                        │
│     │  Check: terraform plan mostra tag in output                       │
│     ▼                                                                   │
│  3. Infracost PR Comment                                                │
│     │  Segnala: risorse create senza tag obbligatori                   │
│     │  Label: cost-impact se delta > threshold                          │
│     ▼                                                                   │
│  4. Cloud Custodian (post-deploy)                                       │
│     │  Policy: tag-enforcement                                          │
│     │  Azione: notify → auto-tag → escalate                            │
│     ▼                                                                   │
│  5. CUR 2.0 (Cost & Usage Report)                                       │
│     │  GroupBy: Team, CostCenter, Project, Environment                  │
│     │  Output: dati in S3 → Athena → dashboard                         │
│     ▼                                                                   │
│  6. Dashboard Costi                                                     │
│        Visualizza: spesa per team, progetto, ambiente, trend            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Flusso sintetico:**

```
Terragrunt config.yaml → Terraform _local.tf → Infracost PR → Cloud Custodian → CUR 2.0
```

Ogni livello aggiunge una rete di sicurezza. Se un tag manca a livello Terragrunt, viene catturato da Custodian post-deploy. Se Custodian non lo cattura, il CUR lo segnala come "untagged" nel report costi.

---

## 5. Rollout Graduale

### v1 — Tag Opzionali (non breaking)

**Timeline suggerita:** settimane 1-4

| Attivita' | Descrizione | Owner |
|-----------|-------------|-------|
| Documentazione | Pubblicare questa reference, comunicare ai team | DevOps |
| Template update | Aggiornare `project-template-aws-iac` con i 3 nuovi campi in `config.yaml` | DevOps |
| Awareness | Workshop 30 min per factory lead: perche' i tag, come configurarli | DevOps + FinOps |
| Adozione volontaria | I team aggiungono `team`, `cost_center`, `repository` in `config.yaml` | Tutti i team |
| Custodian notify-only | Policy `tag-enforcement` in dry-run: notifica Slack per risorse senza tag | DevOps |
| Infracost PR | Abilitare il reusable workflow su 5 repo pilota | DevOps |

**Nessun breaking change.** I repo senza i nuovi campi continuano a funzionare. Le variabili in `_input.tf` hanno `default = null` in v1.

Variabili v1 (con default per retrocompatibilita'):

```hcl
variable "team" {
  description = "Factory/team owner della risorsa per chargeback"
  type        = string
  default     = null  # Opzionale in v1, obbligatorio in v2

  validation {
    condition     = var.team == null || contains(["digital-factory", "core-platforms", "data-platform", "devops"], var.team)
    error_message = "Team deve essere uno tra: digital-factory, core-platforms, data-platform, devops"
  }
}

variable "cost_center" {
  description = "Centro di costo per allocazione finanziaria (formato CC-XXXX)"
  type        = string
  default     = null  # Opzionale in v1, obbligatorio in v2

  validation {
    condition     = var.cost_center == null || can(regex("^CC-[0-9]{4}$", var.cost_center))
    error_message = "CostCenter deve essere nel formato CC-XXXX (es. CC-1001)"
  }
}

variable "repository" {
  description = "Repository GitHub sorgente nel formato org/repo-name"
  type        = string
  default     = null  # Opzionale in v1, obbligatorio in v2
}
```

### v2 — Tag Obbligatori (enforcement)

**Timeline suggerita:** settimane 5-8 (dopo che almeno 80% dei repo ha adottato i tag)

| Attivita' | Descrizione | Owner |
|-----------|-------------|-------|
| Rimuovi default | Rimuovere `default = null` dalle variabili — i tag diventano obbligatori | DevOps |
| CI check | Aggiungere step CI che verifica presenza tag in `config.yaml` | DevOps |
| Custodian enforce | Policy `tag-enforcement` passa da notify a auto-tag + escalate | DevOps |
| Infracost rollout | Estendere workflow a tutti i 44 repo HCL | DevOps |
| Dashboard go-live | Attivare dashboard costi con groupBy sui nuovi tag | FinOps |
| Audit mensile | Report mensile risorse senza tag — target: 0 entro settimana 12 | FinOps |

**Breaking change controllato.** I repo che non hanno aggiunto i tag in v1 falliranno il `terraform plan`. Mitigazione: PR automatica con i valori da aggiungere al `config.yaml` (script di migrazione).

---

## 6. CUR 2.0 + Athena

### 6.1 Configurazione Cost & Usage Report

Configurare CUR 2.0 con FOCUS format dall'AWS Billing console:

| Parametro | Valore |
|-----------|--------|
| Report name | `siae-cur-focus` |
| Format | FOCUS 1.0 |
| Time granularity | Daily |
| S3 bucket | `siae-finops-cur-reports` |
| S3 prefix | `cur/` |
| Compression | Parquet |
| Integration | Amazon Athena |
| Include resource IDs | Si |
| Include user-defined cost allocation tags | Si (`Team`, `CostCenter`, `Repository`) |

> **Importante:** i tag `Team`, `CostCenter` e `Repository` devono essere attivati come
> "Cost Allocation Tags" nella console AWS Billing → Cost Allocation Tags → Activate.
> I tag compaiono nel CUR solo dopo l'attivazione (ritardo fino a 24h).

### 6.2 Struttura Tabella Athena

Dopo la configurazione, AWS crea automaticamente un database Athena con la tabella CUR. Colonne rilevanti:

```sql
-- Colonne principali della tabella CUR FOCUS
line_item_usage_account_id    -- Account AWS
line_item_product_code        -- Servizio AWS (AmazonEC2, AmazonS3, ...)
line_item_unblended_cost      -- Costo non blended
line_item_usage_start_date    -- Data inizio uso
line_item_resource_id         -- ARN risorsa

-- Colonne tag (user-defined cost allocation tags)
resource_tags_user_team          -- Tag Team
resource_tags_user_cost_center   -- Tag CostCenter
resource_tags_user_repository    -- Tag Repository
resource_tags_user_environment   -- Tag Environment
resource_tags_user_project       -- Tag Project
```

### 6.3 Query Athena — Esempi

**Costi per Team (mese corrente):**

```sql
SELECT
  resource_tags_user_team AS team,
  SUM(line_item_unblended_cost) AS total_cost,
  COUNT(DISTINCT line_item_resource_id) AS resource_count
FROM siae_cur_focus.cur_data
WHERE line_item_usage_start_date >= date_trunc('month', current_date)
  AND line_item_line_item_type = 'Usage'
GROUP BY resource_tags_user_team
ORDER BY total_cost DESC;
```

**Costi per CostCenter + Project (mese corrente):**

```sql
SELECT
  resource_tags_user_cost_center AS cost_center,
  resource_tags_user_project AS project,
  SUM(line_item_unblended_cost) AS total_cost
FROM siae_cur_focus.cur_data
WHERE line_item_usage_start_date >= date_trunc('month', current_date)
  AND line_item_line_item_type = 'Usage'
GROUP BY resource_tags_user_cost_center, resource_tags_user_project
ORDER BY total_cost DESC;
```

**Risorse senza tag Team (untagged):**

```sql
SELECT
  line_item_product_code AS service,
  line_item_resource_id AS resource_arn,
  SUM(line_item_unblended_cost) AS cost_last_30d
FROM siae_cur_focus.cur_data
WHERE line_item_usage_start_date >= current_date - interval '30' day
  AND (resource_tags_user_team IS NULL OR resource_tags_user_team = '')
  AND line_item_line_item_type = 'Usage'
  AND line_item_unblended_cost > 0
GROUP BY line_item_product_code, line_item_resource_id
ORDER BY cost_last_30d DESC
LIMIT 50;
```

**Trend mensile per Team (ultimi 6 mesi):**

```sql
SELECT
  date_trunc('month', line_item_usage_start_date) AS month,
  resource_tags_user_team AS team,
  SUM(line_item_unblended_cost) AS monthly_cost
FROM siae_cur_focus.cur_data
WHERE line_item_usage_start_date >= current_date - interval '6' month
  AND line_item_line_item_type = 'Usage'
GROUP BY 1, 2
ORDER BY month DESC, monthly_cost DESC;
```

---

## 7. Dashboard Costi

Struttura suggerita per la dashboard FinOps (QuickSight, Grafana, o tool equivalente) alimentata da CUR 2.0 + Athena.

### 7.1 Vista per Team (Chargeback)

| Widget | Tipo | Query groupBy |
|--------|------|---------------|
| Costo totale per team | Bar chart | `resource_tags_user_team` |
| Percentuale spesa per team | Pie chart | `resource_tags_user_team` |
| Top 10 risorse per team | Table | `resource_tags_user_team`, `line_item_resource_id` |
| Trend mensile per team | Line chart | `month`, `resource_tags_user_team` |

### 7.2 Vista per Project

| Widget | Tipo | Query groupBy |
|--------|------|---------------|
| Costo per progetto | Bar chart | `resource_tags_user_project` |
| Costo per progetto + servizio | Stacked bar | `resource_tags_user_project`, `line_item_product_code` |
| Progetti sopra budget | Table con threshold | `resource_tags_user_project` con filtro costo |

### 7.3 Vista per Environment

| Widget | Tipo | Query groupBy |
|--------|------|---------------|
| Costo per ambiente | Bar chart | `resource_tags_user_environment` |
| Rapporto dev/prod | KPI | `resource_tags_user_environment` (sviluppo+collaudo vs produzione) |
| Risorse dev attive off-hours | Table | `resource_tags_user_environment = 'sviluppo'` + orario |

> **Target:** il rapporto costi dev+collaudo / produzione dovrebbe essere < 40%.
> Se superiore, le risorse non-prod sono sovradimensionate o attive 24/7.

### 7.4 Trend Mensile

| Widget | Tipo | Note |
|--------|------|------|
| Spesa totale mese-su-mese | Line chart | Ultimi 12 mesi |
| Delta mese corrente vs precedente | KPI (+/-%) | Evidenziare anomalie > 10% |
| Top 5 servizi in crescita | Table | Servizi con delta % maggiore |
| Forecast prossimo mese | Line chart proiettata | Basato su trend ultimi 3 mesi |

### 7.5 Vista Untagged

| Widget | Tipo | Note |
|--------|------|------|
| % risorse con tutti i 6 tag | KPI gauge | Target: 100% |
| Costo risorse untagged | KPI ($) | Costo che non puo' essere attribuito |
| Top risorse untagged per costo | Table | Priorita' di remediation |
| Trend tag compliance | Line chart | Percentuale compliance nel tempo |

---

## Riferimenti

- Design doc: `docs/plans/2026-03-13-finops-suite-design.md` (sezione 5 — Evoluzione Tagging)
- Skill IaC: `skills/siae-iac/SKILL.md` (vincolo V7 — tag obbligatori)
- Custodian policy: `skills/siae-finops/reference/custodian-policies.md` (policy 1 — tag-enforcement)
- AWS CUR docs: https://docs.aws.amazon.com/cur/latest/userguide/what-is-cur.html
- FOCUS format: https://focus.finops.org/
