# Steampipe Queries — Catalogo SQL per FinOps SIAE

> Reference file per `siae-finops`. Ogni query e' pronta per il tool `steampipe_query` MCP.
> Per setup MCP server vedi sezione 1. Per benchmark automatizzato vedi sezione 6.

---

## 1. Setup Steampipe MCP

### 1.1 Installazione Steampipe + Plugin AWS

```bash
# Installa Steampipe
brew install steampipe

# Installa plugin AWS (obbligatorio)
steampipe plugin install aws

# Installa plugin AWS Cost (opzionale, per CUR data)
steampipe plugin install awscost

# Verifica installazione
steampipe --version
steampipe plugin list
```

### 1.2 Configurazione MCP Server per Claude Code

Aggiungere in `~/.claude/mcp_servers.json` (o nella configurazione MCP del progetto):

```json
{
  "steampipe": {
    "command": "npx",
    "args": ["-y", "@turbot/steampipe-mcp"],
    "env": {
      "STEAMPIPE_INSTALL_DIR": "~/.steampipe"
    }
  }
}
```

Dopo la configurazione, riavvia Claude Code. Verifica che il tool `steampipe_query` sia disponibile nella sessione.

### 1.3 Multi-Account Connection Aggregator

SIAE opera su piu' account AWS. Per query cross-account, configura un aggregator in `~/.steampipe/config/aws.spc`:

```hcl
# Account singolo (default)
connection "aws" {
  plugin  = "aws"
  profile = "default"
  regions = ["eu-west-1", "eu-central-1"]
}

# Account produzione
connection "aws_prod" {
  plugin  = "aws"
  profile = "siae-produzione"
  regions = ["eu-west-1"]
}

# Account sviluppo
connection "aws_dev" {
  plugin  = "aws"
  profile = "siae-sviluppo"
  regions = ["eu-west-1"]
}

# Account collaudo
connection "aws_coll" {
  plugin  = "aws"
  profile = "siae-collaudo"
  regions = ["eu-west-1"]
}

# Account certificazione
connection "aws_cert" {
  plugin  = "aws"
  profile = "siae-certificazione"
  regions = ["eu-west-1"]
}

# Aggregator: query su TUTTI gli account contemporaneamente
connection "aws_all" {
  plugin      = "aws"
  type        = "aggregator"
  connections = ["aws_prod", "aws_dev", "aws_coll", "aws_cert"]
}
```

Per usare l'aggregator nelle query, prefissa le tabelle con `aws_all.`:

```sql
SELECT * FROM aws_all.aws_ec2_instance;
```

**Prerequisiti IAM:** ogni account deve avere un profilo AWS CLI configurato con permessi ReadOnly (policy `ReadOnlyAccess` o equivalente). Per CUR data serve anche `ce:GetCostAndUsage`.

---

## 2. Cost Analysis Queries

### 2.1 Top Spender del Mese Corrente

**Nome:** `cost-top-spender-month`

**SQL:**

```sql
SELECT
  service,
  ROUND(SUM(unblended_cost_amount)::numeric, 2) AS cost_usd,
  ROUND(SUM(unblended_cost_amount)::numeric / (SELECT SUM(unblended_cost_amount) FROM aws_cost_by_service_daily WHERE period_start >= date_trunc('month', current_date)) * 100, 1) AS pct_of_total
FROM
  aws_cost_by_service_daily
WHERE
  period_start >= date_trunc('month', current_date)
GROUP BY
  service
ORDER BY
  cost_usd DESC
LIMIT 10;
```

**Output atteso:**

| service | cost_usd | pct_of_total |
|---------|----------|--------------|
| Amazon Relational Database Service | 1234.56 | 35.2 |
| AWS Lambda | 567.89 | 16.2 |
| Amazon DynamoDB | 345.67 | 9.8 |
| ... | ... | ... |

**Azione raccomandata:** Per i servizi con pct > 20%, approfondisci con le query service-specific (sezione 5). Confronta con il mese precedente (query 2.2) per individuare anomalie.

---

### 2.2 Cost Trend Mese-su-Mese (ultimi 6 mesi)

**Nome:** `cost-trend-monthly`

**SQL:**

```sql
SELECT
  date_trunc('month', period_start)::date AS month,
  ROUND(SUM(unblended_cost_amount)::numeric, 2) AS total_cost_usd,
  ROUND(
    (SUM(unblended_cost_amount) - LAG(SUM(unblended_cost_amount)) OVER (ORDER BY date_trunc('month', period_start)))
    / NULLIF(LAG(SUM(unblended_cost_amount)) OVER (ORDER BY date_trunc('month', period_start)), 0) * 100
  ::numeric, 1) AS mom_change_pct
FROM
  aws_cost_by_service_daily
WHERE
  period_start >= date_trunc('month', current_date) - interval '6 months'
GROUP BY
  date_trunc('month', period_start)
ORDER BY
  month DESC;
```

**Output atteso:**

| month | total_cost_usd | mom_change_pct |
|-------|----------------|----------------|
| 2026-03-01 | 3500.00 | +5.2 |
| 2026-02-01 | 3325.00 | -2.1 |
| 2026-01-01 | 3396.00 | +12.3 |
| ... | ... | ... |

**Azione raccomandata:** Variazioni > +10% mese-su-mese richiedono investigazione. Usa query 2.1 per identificare quale servizio e' cresciuto, poi approfondisci con sezione 5.

---

### 2.3 Costi per Tag Team (Chargeback tra Factory)

**Nome:** `cost-by-tag-team`

**SQL:**

```sql
SELECT
  CASE
    WHEN tags ->> 'Team' IS NULL THEN '(nessun tag Team)'
    ELSE tags ->> 'Team'
  END AS team,
  ROUND(SUM(unblended_cost_amount)::numeric, 2) AS cost_usd,
  COUNT(DISTINCT service) AS num_services
FROM
  aws_cost_by_tag_daily
WHERE
  period_start >= date_trunc('month', current_date)
GROUP BY
  team
ORDER BY
  cost_usd DESC;
```

**Output atteso:**

| team | cost_usd | num_services |
|------|----------|--------------|
| digital-factory | 1200.00 | 8 |
| core-platforms | 980.00 | 5 |
| data-platform | 750.00 | 4 |
| devops | 320.00 | 3 |
| (nessun tag Team) | 250.00 | 12 |

**Azione raccomandata:** Se `(nessun tag Team)` ha costi significativi, esegui tag audit (sezione 4) per identificare le risorse non taggate. Ogni factory dovrebbe avere visibilita' sui propri costi.

---

### 2.4 Costi per Tag Project

**Nome:** `cost-by-tag-project`

**SQL:**

```sql
SELECT
  CASE
    WHEN tags ->> 'Project' IS NULL THEN '(nessun tag Project)'
    ELSE tags ->> 'Project'
  END AS project,
  ROUND(SUM(unblended_cost_amount)::numeric, 2) AS cost_usd
FROM
  aws_cost_by_tag_daily
WHERE
  period_start >= date_trunc('month', current_date)
GROUP BY
  project
ORDER BY
  cost_usd DESC
LIMIT 15;
```

**Output atteso:**

| project | cost_usd |
|---------|----------|
| diritti | 890.00 |
| catalogo | 650.00 |
| sport | 420.00 |
| (nessun tag Project) | 340.00 |

**Azione raccomandata:** Usa questa vista per allocare costi ai progetti SIAE. Se `(nessun tag Project)` e' alto, applica tagging tramite enforcement chain (vedi tagging-strategy.md).

---

### 2.5 Costi per Account AWS

**Nome:** `cost-by-account`

**SQL:**

```sql
SELECT
  linked_account_id,
  ROUND(SUM(unblended_cost_amount)::numeric, 2) AS cost_usd,
  ROUND(SUM(unblended_cost_amount)::numeric / (SELECT SUM(unblended_cost_amount) FROM aws_cost_by_account_daily WHERE period_start >= date_trunc('month', current_date)) * 100, 1) AS pct_of_total
FROM
  aws_cost_by_account_daily
WHERE
  period_start >= date_trunc('month', current_date)
GROUP BY
  linked_account_id
ORDER BY
  cost_usd DESC;
```

**Output atteso:**

| linked_account_id | cost_usd | pct_of_total |
|-------------------|----------|--------------|
| 123456789012 (produzione) | 2100.00 | 60.0 |
| 234567890123 (collaudo) | 700.00 | 20.0 |
| 345678901234 (sviluppo) | 500.00 | 14.3 |
| 456789012345 (certificazione) | 200.00 | 5.7 |

**Azione raccomandata:** Sviluppo e collaudo non dovrebbero superare il 40% del totale combinato. Se lo fanno, verifica risorse idle (sezione 3) e off-hours scheduling (vedi custodian-policies.md policy 6).

---

## 3. Idle Resource Detection

### 3.1 Lambda Non Invocate da Oltre 90 Giorni

**Nome:** `idle-lambda-90d`

**SQL:**

```sql
SELECT
  function_name,
  runtime,
  ROUND(memory_size::numeric / 1024, 1) AS memory_gb,
  last_modified::date AS last_modified,
  (current_date - last_modified::date) AS days_since_modified,
  region,
  account_id
FROM
  aws_lambda_function
WHERE
  last_modified < now() - interval '90 days'
ORDER BY
  last_modified ASC;
```

**Output atteso:**

| function_name | runtime | memory_gb | last_modified | days_since_modified | region | account_id |
|---------------|---------|-----------|---------------|---------------------|--------|------------|
| old-migration-fn | python3.8 | 0.5 | 2025-06-15 | 271 | eu-west-1 | 123456789012 |
| test-handler | nodejs16.x | 0.1 | 2025-09-01 | 193 | eu-west-1 | 234567890123 |

**Azione raccomandata:**
- Lambda con runtime deprecato (python3.8, nodejs16.x) → rimuovere o aggiornare runtime
- Lambda non modificate >180gg → candidata per eliminazione. Verificare con il team owner (tag `Team`)
- Lambda in account sviluppo/collaudo → piu' aggressive nella pulizia

---

### 3.2 DynamoDB Tabelle Idle (< 10 RCU per 14 Giorni)

**Nome:** `idle-dynamodb-14d`

**SQL:**

```sql
SELECT
  t.name AS table_name,
  t.billing_mode,
  t.read_capacity,
  t.write_capacity,
  t.table_size_bytes / (1024 * 1024) AS size_mb,
  t.item_count,
  t.region,
  t.account_id,
  t.tags ->> 'Environment' AS environment,
  t.tags ->> 'Team' AS team
FROM
  aws_dynamodb_table AS t
LEFT JOIN
  aws_dynamodb_metric_account_provisioned_read_capacity_utilization AS m
  ON t.account_id = m.account_id AND t.region = m.region
WHERE
  (t.billing_mode = 'PROVISIONED' AND t.read_capacity > 0)
  AND t.item_count < 100
ORDER BY
  t.read_capacity DESC;
```

> **Nota:** Steampipe non ha una metrica diretta ConsumedReadCapacity per tabella individuale. Questa query trova tabelle provisioned con pochi item come proxy. Per un check piu' preciso, usa CloudWatch metrics via query 3.2b.

**Query alternativa 3.2b — via CloudWatch:**

```sql
SELECT
  t.name AS table_name,
  t.billing_mode,
  t.read_capacity AS provisioned_rcu,
  t.item_count,
  t.tags ->> 'Environment' AS environment
FROM
  aws_dynamodb_table AS t
WHERE
  t.billing_mode = 'PROVISIONED'
  AND t.read_capacity >= 10
  AND t.item_count < 1000
ORDER BY
  t.read_capacity DESC;
```

**Output atteso:**

| table_name | billing_mode | provisioned_rcu | item_count | environment |
|------------|-------------|-----------------|------------|-------------|
| legacy-cache-table | PROVISIONED | 100 | 5 | sviluppo |
| old-session-store | PROVISIONED | 50 | 0 | collaudo |

**Azione raccomandata:**
- Tabelle con 0 item → candidata per eliminazione
- Tabelle con item_count < 100 e RCU > 10 → switch a PAY_PER_REQUEST (on-demand)
- Tabelle in sviluppo/collaudo → ridurre RCU o passare a on-demand

---

### 3.3 EBS Volumes Detached (Non Collegati)

**Nome:** `idle-ebs-detached`

**SQL:**

```sql
SELECT
  volume_id,
  volume_type,
  size AS size_gb,
  iops,
  state,
  create_time::date AS created,
  (current_date - create_time::date) AS days_detached,
  ROUND(
    CASE
      WHEN volume_type = 'gp3' THEN size * 0.08
      WHEN volume_type = 'gp2' THEN size * 0.10
      WHEN volume_type = 'io1' THEN size * 0.125 + iops * 0.065
      WHEN volume_type = 'io2' THEN size * 0.125 + iops * 0.065
      WHEN volume_type = 'st1' THEN size * 0.045
      WHEN volume_type = 'sc1' THEN size * 0.015
      ELSE size * 0.10
    END::numeric, 2
  ) AS estimated_monthly_cost_usd,
  region,
  account_id,
  tags ->> 'Team' AS team
FROM
  aws_ebs_volume
WHERE
  state = 'available'
ORDER BY
  estimated_monthly_cost_usd DESC;
```

**Output atteso:**

| volume_id | volume_type | size_gb | state | days_detached | estimated_monthly_cost_usd | team |
|-----------|-------------|---------|-------|---------------|---------------------------|------|
| vol-0abc123 | gp3 | 500 | available | 120 | 40.00 | digital-factory |
| vol-0def456 | io1 | 100 | available | 45 | 19.00 | core-platforms |

**Azione raccomandata:**
- Detached > 30 giorni → creare snapshot e poi eliminare il volume
- Verificare se il volume ha snapshot recenti prima di eliminare
- Volume io1/io2 detached → priorita' alta (costi IOPS elevati anche se non usati)

---

### 3.4 Snapshot EBS Vecchi (> 180 Giorni)

**Nome:** `idle-snapshots-old`

**SQL:**

```sql
SELECT
  snapshot_id,
  volume_id,
  volume_size AS size_gb,
  ROUND((volume_size * 0.05)::numeric, 2) AS estimated_monthly_cost_usd,
  start_time::date AS created,
  (current_date - start_time::date) AS age_days,
  description,
  region,
  account_id,
  tags ->> 'Team' AS team
FROM
  aws_ebs_snapshot
WHERE
  owner_id = (SELECT account_id FROM aws_account LIMIT 1)
  AND start_time < now() - interval '180 days'
ORDER BY
  age_days DESC
LIMIT 50;
```

**Output atteso:**

| snapshot_id | size_gb | estimated_monthly_cost_usd | created | age_days | description |
|-------------|---------|---------------------------|---------|----------|-------------|
| snap-0abc123 | 500 | 25.00 | 2025-03-01 | 377 | Created by... |
| snap-0def456 | 200 | 10.00 | 2025-05-15 | 302 | backup before... |

**Azione raccomandata:**
- Snapshot > 365 giorni → eliminare (salvo policy di retention esplicita)
- Snapshot senza description → probabilmente manuali, candidati per pulizia
- Calcolare risparmio totale: somma `estimated_monthly_cost_usd` di tutti i candidati

---

### 3.5 RDS CPU Media < 10% (Sotto-Utilizzati)

**Nome:** `idle-rds-low-cpu`

**SQL:**

```sql
SELECT
  i.db_instance_identifier,
  i.db_instance_class,
  i.engine,
  i.engine_version,
  i.multi_az,
  ROUND(m.average::numeric, 2) AS avg_cpu_pct,
  ROUND(m.maximum::numeric, 2) AS max_cpu_pct,
  i.tags ->> 'Environment' AS environment,
  i.tags ->> 'Team' AS team,
  i.region,
  i.account_id
FROM
  aws_rds_db_instance AS i
JOIN
  aws_rds_db_instance_metric_cpu_utilization_daily AS m
  ON i.db_instance_identifier = m.db_instance_identifier
  AND i.region = m.region
  AND i.account_id = m.account_id
WHERE
  m.timestamp >= now() - interval '14 days'
GROUP BY
  i.db_instance_identifier, i.db_instance_class, i.engine,
  i.engine_version, i.multi_az, m.average, m.maximum,
  i.tags, i.region, i.account_id
HAVING
  AVG(m.average) < 10
ORDER BY
  m.average ASC;
```

**Output atteso:**

| db_instance_identifier | db_instance_class | engine | avg_cpu_pct | max_cpu_pct | environment | team |
|------------------------|-------------------|--------|-------------|-------------|-------------|------|
| legacy-db-dev | db.r5.xlarge | postgres | 2.3 | 8.1 | sviluppo | core-platforms |
| catalog-staging | db.r6g.large | mysql | 5.1 | 15.2 | collaudo | digital-factory |

**Azione raccomandata:**
- CPU avg < 5% → rightsizing di almeno 1 instance class (es. xlarge → large)
- Multi-AZ in sviluppo/collaudo → disabilitare Multi-AZ (risparmio ~50%)
- RDS in sviluppo con CPU < 10% → candidato per off-hours scheduling (policy Custodian 6)

---

## 4. Tag Audit Queries

I 6 tag obbligatori SIAE sono: `Environment`, `Project`, `ManagedBy`, `Team`, `CostCenter`, `Repository`.

### 4.1 Risorse Senza Tag "Environment"

**Nome:** `tag-audit-environment`

**SQL:**

```sql
SELECT
  arn,
  title,
  region,
  account_id,
  tags
FROM
  aws_tagging_resource
WHERE
  tags ->> 'Environment' IS NULL
ORDER BY
  arn
LIMIT 50;
```

**Output atteso:**

| arn | title | region | account_id | tags |
|-----|-------|--------|------------|------|
| arn:aws:lambda:eu-west-1:123456789012:function:orphan-fn | orphan-fn | eu-west-1 | 123456789012 | {"ManagedBy": "Terraform"} |

**Azione raccomandata:** Il tag `Environment` e' il piu' critico per separare costi per ambiente. Risorse senza questo tag devono essere taggate tramite Terraform (aggiornare `_local.tf`) o tramite Cloud Custodian policy 1 (auto-tag).

---

### 4.2 Risorse Senza Tag "Project"

**Nome:** `tag-audit-project`

**SQL:**

```sql
SELECT
  arn,
  title,
  region,
  account_id,
  tags
FROM
  aws_tagging_resource
WHERE
  tags ->> 'Project' IS NULL
ORDER BY
  arn
LIMIT 50;
```

**Output atteso:** Come 4.1, lista di ARN senza tag `Project`.

**Azione raccomandata:** Senza `Project`, impossibile allocare costi ai progetti SIAE. Aggiornare Terragrunt config per includere `Project` nel blocco `common_tags`.

---

### 4.3 Risorse Senza Tag "ManagedBy"

**Nome:** `tag-audit-managedby`

**SQL:**

```sql
SELECT
  arn,
  title,
  region,
  account_id,
  tags
FROM
  aws_tagging_resource
WHERE
  tags ->> 'ManagedBy' IS NULL
ORDER BY
  arn
LIMIT 50;
```

**Output atteso:** Come 4.1, lista di ARN senza tag `ManagedBy`.

**Azione raccomandata:** Risorse senza `ManagedBy` sono probabilmente create manualmente via console. Importare in Terraform o documentare come eccezione. Cloud Custodian policy 1 puo' auto-taggare con `ManagedBy: manual`.

---

### 4.4 Risorse Senza Tag "Team"

**Nome:** `tag-audit-team`

**SQL:**

```sql
SELECT
  arn,
  title,
  region,
  account_id,
  tags
FROM
  aws_tagging_resource
WHERE
  tags ->> 'Team' IS NULL
ORDER BY
  arn
LIMIT 50;
```

**Output atteso:** Come 4.1, lista di ARN senza tag `Team`.

**Azione raccomandata:** Tag `Team` e' **NUOVO** (v2 tagging). Atteso volume alto di risorse senza questo tag nella fase iniziale. Rollout graduale: prima nuove risorse obbligatorie, poi backfill su risorse esistenti tramite Custodian.

---

### 4.5 Risorse Senza Tag "CostCenter"

**Nome:** `tag-audit-costcenter`

**SQL:**

```sql
SELECT
  arn,
  title,
  region,
  account_id,
  tags
FROM
  aws_tagging_resource
WHERE
  tags ->> 'CostCenter' IS NULL
ORDER BY
  arn
LIMIT 50;
```

**Output atteso:** Come 4.1, lista di ARN senza tag `CostCenter`.

**Azione raccomandata:** Tag `CostCenter` e' **NUOVO** (v2 tagging). Formato atteso: `CC-XXXX`. Coordinare con finance per mappatura team → centro di costo prima del rollout.

---

### 4.6 Risorse Senza Tag "Repository"

**Nome:** `tag-audit-repository`

**SQL:**

```sql
SELECT
  arn,
  title,
  region,
  account_id,
  tags
FROM
  aws_tagging_resource
WHERE
  tags ->> 'Repository' IS NULL
ORDER BY
  arn
LIMIT 50;
```

**Output atteso:** Come 4.1, lista di ARN senza tag `Repository`.

**Azione raccomandata:** Tag `Repository` e' **NUOVO** (v2 tagging). Formato atteso: `itsiae/repo-name`. Permette di tracciare quale repo ha creato quale risorsa. Utile per ownership e troubleshooting.

---

### 4.7 Report Complessivo Tag Compliance

**Nome:** `tag-audit-summary`

**SQL:**

```sql
SELECT
  COUNT(*) AS total_resources,
  COUNT(*) FILTER (WHERE tags ->> 'Environment' IS NULL) AS missing_environment,
  COUNT(*) FILTER (WHERE tags ->> 'Project' IS NULL) AS missing_project,
  COUNT(*) FILTER (WHERE tags ->> 'ManagedBy' IS NULL) AS missing_managedby,
  COUNT(*) FILTER (WHERE tags ->> 'Team' IS NULL) AS missing_team,
  COUNT(*) FILTER (WHERE tags ->> 'CostCenter' IS NULL) AS missing_costcenter,
  COUNT(*) FILTER (WHERE tags ->> 'Repository' IS NULL) AS missing_repository
FROM
  aws_tagging_resource;
```

**Output atteso:**

| total_resources | missing_environment | missing_project | missing_managedby | missing_team | missing_costcenter | missing_repository |
|-----------------|--------------------|-----------------|--------------------|--------------|--------------------|--------------------|
| 1250 | 45 | 120 | 85 | 890 | 950 | 980 |

**Azione raccomandata:** Questa query da' una fotografia complessiva della compliance. Target: tag legacy (Environment, Project, ManagedBy) al 95%+, tag nuovi (Team, CostCenter, Repository) rollout graduale verso 80% in 3 mesi.

---

## 5. Service-Specific Queries

### 5.1 RDS Instance Sizing

**Nome:** `rds-instance-sizing`

**SQL:**

```sql
SELECT
  i.db_instance_identifier,
  i.db_instance_class,
  i.engine,
  i.multi_az,
  i.storage_type,
  i.allocated_storage AS storage_gb,
  ROUND(m_cpu.average::numeric, 2) AS avg_cpu_14d_pct,
  ROUND(m_mem.average::numeric, 2) AS avg_freeable_mem_mb,
  ROUND(m_conn.average::numeric, 0) AS avg_connections,
  i.tags ->> 'Environment' AS environment,
  i.tags ->> 'Team' AS team
FROM
  aws_rds_db_instance AS i
LEFT JOIN
  aws_rds_db_instance_metric_cpu_utilization_daily AS m_cpu
  ON i.db_instance_identifier = m_cpu.db_instance_identifier
  AND i.region = m_cpu.region
  AND m_cpu.timestamp >= now() - interval '14 days'
LEFT JOIN
  aws_rds_db_instance_metric_connections_daily AS m_conn
  ON i.db_instance_identifier = m_conn.db_instance_identifier
  AND i.region = m_conn.region
  AND m_conn.timestamp >= now() - interval '14 days'
LEFT JOIN
  aws_rds_db_instance_metric_freeable_memory_daily AS m_mem
  ON i.db_instance_identifier = m_mem.db_instance_identifier
  AND i.region = m_mem.region
  AND m_mem.timestamp >= now() - interval '14 days'
ORDER BY
  m_cpu.average ASC NULLS LAST;
```

**Output atteso:**

| db_instance_identifier | db_instance_class | engine | avg_cpu_14d_pct | avg_freeable_mem_mb | avg_connections | environment |
|------------------------|-------------------|--------|-----------------|---------------------|-----------------|-------------|
| app-db-dev | db.r5.xlarge | postgres | 3.2 | 28000 | 5 | sviluppo |
| catalog-prod | db.r6g.2xlarge | mysql | 45.1 | 8000 | 120 | produzione |

**Azione raccomandata:**
- CPU < 20% e freeable memory > 50% della classe → rightsizing alla classe inferiore
- Connections < 10 → considerare RDS Proxy o ridurre classe
- Multi-AZ in sviluppo/collaudo → disabilitare (risparmio ~50%)
- storage_type `io1` con basso IOPS usage → migrare a `gp3`

---

### 5.2 Glue Job Capacity e Workers

**Nome:** `glue-job-capacity`

**SQL:**

```sql
SELECT
  name AS job_name,
  max_capacity,
  number_of_workers,
  worker_type,
  glue_version,
  timeout AS timeout_minutes,
  last_modified_on::date AS last_modified,
  ROUND(
    CASE
      WHEN worker_type = 'G.1X' THEN number_of_workers * 0.44
      WHEN worker_type = 'G.2X' THEN number_of_workers * 0.88
      WHEN worker_type = 'G.4X' THEN number_of_workers * 1.76
      WHEN worker_type = 'G.8X' THEN number_of_workers * 3.52
      WHEN worker_type = 'Z.2X' THEN number_of_workers * 0.22
      ELSE COALESCE(max_capacity, 2) * 0.44
    END::numeric, 2
  ) AS cost_per_hour_usd,
  tags ->> 'Team' AS team,
  tags ->> 'Project' AS project
FROM
  aws_glue_job
ORDER BY
  cost_per_hour_usd DESC;
```

**Output atteso:**

| job_name | max_capacity | number_of_workers | worker_type | cost_per_hour_usd | team | project |
|----------|-------------|-------------------|-------------|-------------------|------|---------|
| bronze-to-silver-etl | - | 20 | G.2X | 17.60 | data-platform | diritti |
| daily-aggregation | - | 5 | G.1X | 2.20 | data-platform | catalogo |

**Azione raccomandata:**
- Workers > 10 con G.2X → valutare se G.1X e' sufficiente (meta' costo)
- Job senza timeout → aggiungere timeout (evita runaway, vedi Custodian policy 8)
- Glue 2.0/3.0 → migrare a 4.0 per performance migliori
- Job batch non time-critical → usare FLEX execution class (risparmio ~35%)
- last_modified > 180gg → verificare se il job e' ancora necessario

---

### 5.3 ECS Service Utilization

**Nome:** `ecs-service-utilization`

**SQL:**

```sql
SELECT
  s.service_name,
  s.cluster_arn,
  s.launch_type,
  s.desired_count,
  s.running_count,
  s.pending_count,
  td.cpu AS task_cpu,
  td.memory AS task_memory_mb,
  s.tags ->> 'Environment' AS environment,
  s.tags ->> 'Team' AS team
FROM
  aws_ecs_service AS s
LEFT JOIN
  aws_ecs_task_definition AS td
  ON s.task_definition = td.task_definition_arn
ORDER BY
  s.desired_count DESC;
```

**Output atteso:**

| service_name | launch_type | desired_count | running_count | task_cpu | task_memory_mb | environment |
|--------------|-------------|---------------|---------------|----------|----------------|-------------|
| api-gateway | FARGATE | 4 | 4 | 1024 | 2048 | produzione |
| worker-service | FARGATE | 2 | 2 | 512 | 1024 | produzione |
| api-dev | FARGATE | 2 | 2 | 512 | 1024 | sviluppo |

**Azione raccomandata:**
- Servizi con `desired_count` > `running_count` → problemi di scheduling, investigare
- Servizi in sviluppo/collaudo con desired_count > 1 → ridurre a 1 fuori orario lavorativo
- Servizi Fargate → valutare Fargate Spot per workload fault-tolerant (risparmio ~70%)
- Task con CPU/memory sovradimensionati → ridurre basandosi su CloudWatch Container Insights

---

### 5.4 Lambda Memory e Duration Optimization

**Nome:** `lambda-memory-duration`

**SQL:**

```sql
SELECT
  function_name,
  runtime,
  memory_size AS configured_memory_mb,
  timeout AS timeout_seconds,
  code_size / (1024 * 1024) AS code_size_mb,
  architectures,
  ROUND((memory_size * 0.0000166667 / 1024 * 1000000)::numeric, 2) AS cost_per_1m_invocations_usd,
  last_modified::date AS last_modified,
  tags ->> 'Environment' AS environment,
  tags ->> 'Team' AS team
FROM
  aws_lambda_function
ORDER BY
  memory_size DESC;
```

**Output atteso:**

| function_name | runtime | configured_memory_mb | timeout_seconds | cost_per_1m_invocations_usd | environment | team |
|---------------|---------|---------------------|-----------------|---------------------------|-------------|------|
| heavy-processor | python3.11 | 3008 | 900 | 50.11 | produzione | data-platform |
| api-handler | nodejs20.x | 512 | 30 | 8.53 | produzione | digital-factory |
| simple-trigger | python3.12 | 128 | 10 | 2.13 | sviluppo | devops |

**Azione raccomandata:**
- Memory > 1024 MB → eseguire AWS Lambda Power Tuning per trovare il punto ottimale costo/performance
- Runtime x86_64 → migrare a arm64 (Graviton2, risparmio ~20%)
- Timeout > 300 secondi → verificare se il workload e' adatto a Lambda o meglio ECS/Step Functions
- code_size > 50 MB → ottimizzare dipendenze (Lambda Layers o container image)

---

## 6. AWS Thrifty Benchmark

### 6.1 Installazione Powerpipe + AWS Thrifty

```bash
# Installa Powerpipe (gestisce benchmark Steampipe)
brew install turbot/tap/powerpipe

# Clona o installa il mod AWS Thrifty
mkdir -p ~/powerpipe-mods && cd ~/powerpipe-mods
powerpipe mod init
powerpipe mod install github.com/turbot/steampipe-mod-aws-thrifty

# Verifica installazione
powerpipe --version
```

### 6.2 Eseguire il Benchmark

```bash
# Benchmark completo (55 check, ~5-10 minuti)
cd ~/powerpipe-mods
powerpipe benchmark run aws_thrifty.benchmark.aws_thrifty --output=brief

# Solo sezione specifica
powerpipe benchmark run aws_thrifty.benchmark.ebs --output=brief
powerpipe benchmark run aws_thrifty.benchmark.rds --output=brief
powerpipe benchmark run aws_thrifty.benchmark.lambda --output=brief
powerpipe benchmark run aws_thrifty.benchmark.dynamodb --output=brief
powerpipe benchmark run aws_thrifty.benchmark.ecs --output=brief

# Output dettagliato in JSON (per analisi)
powerpipe benchmark run aws_thrifty.benchmark.aws_thrifty --output=json > /tmp/thrifty-results.json

# Output HTML (per condivisione)
powerpipe benchmark run aws_thrifty.benchmark.aws_thrifty --output=html > /tmp/thrifty-report.html
```

### 6.3 Interpretare l'Output

L'output brief mostra:

```
BENCHMARK: aws_thrifty.benchmark.aws_thrifty
  BENCHMARK: aws_thrifty.benchmark.ebs
    CONTROL: aws_thrifty.control.ebs_volume_unused ............... 3 alarms, 0 ok
    CONTROL: aws_thrifty.control.ebs_snapshot_max_age ........... 12 alarms, 45 ok
    ...
```

| Stato | Significato |
|-------|-------------|
| `ok` | Risorsa conforme (nessuna azione) |
| `alarm` | Risorsa non conforme (azione raccomandata) |
| `skip` | Check non applicabile |
| `error` | Errore nell'esecuzione del check |

### 6.4 Benchmark Disponibili in AWS Thrifty

| Benchmark | Descrizione | Check principali |
|-----------|-------------|-----------------|
| `ebs` | Volumi e snapshot EBS | Volume unused, snapshot age, gp2→gp3 migration |
| `rds` | Database RDS | Instance idle, old engine, Multi-AZ non-prod |
| `lambda` | Funzioni Lambda | Excessive timeout, high error rate |
| `dynamodb` | Tabelle DynamoDB | Unused tables, over-provisioned |
| `ecs` | Servizi ECS/Fargate | Over-provisioned tasks |
| `ec2` | Istanze EC2 | Idle instances, old AMI, previous gen |
| `s3` | Bucket S3 | Missing lifecycle, versioning cost |
| `cloudwatch` | Log groups | Log retention non configurato |
| `cost_explorer` | Costi generali | Forecast vs budget |

### 6.5 Prioritizzazione dei Finding

Dopo aver eseguito il benchmark, prioritizza con questa matrice:

| Priorita' | Criterio | Azione |
|-----------|----------|--------|
| **P0 — Immediata** | Risorse idle con costo > $100/mese | Eliminare/ridimensionare entro 1 settimana |
| **P1 — Alta** | Risorse sovradimensionate in produzione | Rightsizing nel prossimo sprint |
| **P2 — Media** | Tag mancanti su risorse esistenti | Backfill graduale tramite Custodian |
| **P3 — Bassa** | Ottimizzazioni minori (gp2→gp3, arm64) | Pianificare nel backlog |

**Workflow consigliato:**

1. Esegui benchmark completo → salva output JSON
2. Filtra finding per account/environment (produzione prima)
3. Ordina per costo stimato (usa query sezione 3 per dettagli)
4. Crea ticket JIRA per P0/P1 con owner = tag `Team`
5. Ri-esegui benchmark dopo 2 settimane per misurare progresso
