# Integrazione Moduli Template IaC nella Skill siae-iac — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Arricchire la skill siae-iac con sezione template repo + 6 reference files per i moduli
**Architettura:** Sezione 7 nel SKILL.md (~65 righe) + 6 file in reference/ con blueprint dettagliati
**Stack:** Markdown, Bash (test)
**SP:** 5

---

## Task 1: Crea directory reference e file template-vpc.md

**File coinvolti:**

- Crea: `siae-dev-forge/skills/siae-iac/reference/template-vpc.md`

**Step 1: Crea la directory reference**

```bash
mkdir -p siae-dev-forge/skills/siae-iac/reference
```

**Step 2: Scrivi template-vpc.md**

```markdown
# Modulo VPC — Data Lookup

Responsabilita': Lookup risorse VPC enterprise pre-esistenti (NON crea VPC).

## File Structure

```text
modules/vpc/
├── _input.tf      # account_id, region, project, env, vpc_stage, module, config
├── _local.tf      # prefix, global_suffix
├── _output.tf     # vpc_enterprise, data_subnets, server_subnets, aws_vpc_endpoint_api_gateway
├── vpc.tf         # Data source VPC + subnet (a/b/c per data e server)
├── endpoints.tf   # VPC endpoint API Gateway lookup
└── sg.tf          # Security group lookups
```

## Pattern Data Source

Lookup by tag Name: `platform-enterprise-${var.vpc_stage}-vpc`
Subnet naming: `${vpc_name}-data-${az}` e `${vpc_name}-server-${az}`

## Dependency

Root module — nessuna dipendenza. Gli altri moduli dipendono da questo.

## Output esposti

| Output                           | Tipo         | Descrizione                     |
|----------------------------------|--------------|---------------------------------|
| `vpc_enterprise`                 | object       | VPC data source completo        |
| `data_subnets`                   | list(object) | Subnet data [a, b, c]          |
| `server_subnets`                 | list(object) | Subnet server [a, b, c]        |
| `aws_vpc_endpoint_api_gateway`   | object {id}  | VPC Endpoint per api-private    |
```

**Step 3: Verifica file creato**

```bash
cat siae-dev-forge/skills/siae-iac/reference/template-vpc.md | head -5
```

Output atteso: `# Modulo VPC — Data Lookup`

---

## Task 2: Crea reference/template-api-private.md

**File coinvolti:**

- Crea: `siae-dev-forge/skills/siae-iac/reference/template-api-private.md`

**Step 1: Scrivi template-api-private.md**

```markdown
# Modulo API Private — API Gateway PRIVATE

Responsabilita': API Gateway REST privato, accessibile solo via VPC Endpoint.

## File Structure

```text
modules/api-private/
├── _input.tf           # standard + create_shared_resources, xray_enabled,
│                       #   aws_vpc_endpoint_api_gateway, siae_route53_zone_name
├── _local.tf           # prefix, account_level_prefix
├── api-gateway.tf      # REST API (PRIVATE), /health mock, resource policy (VPC Endpoint only)
├── api-deploy.tf       # Deployment, Stage, method settings (burst=10000, rate=100)
└── route53-record.tf   # CNAME: {module}.{project}.{env}.aws.siae
```

## Dependency

`dependency "vpc"` → `aws_vpc_endpoint_api_gateway`

## IAM

Role CloudWatch: `${account_level_prefix}-apigw-private-service-role`
Creato solo se `create_shared_resources = true` (una volta per account).

## Throttling

| Parametro    | Valore |
|--------------|--------|
| burst_limit  | 10000  |
| rate_limit   | 100    |

Logging: ERROR in prod, INFO altrimenti.
```

---

## Task 3: Crea reference/template-api-public.md

**File coinvolti:**

- Crea: `siae-dev-forge/skills/siae-iac/reference/template-api-public.md`

**Step 1: Scrivi template-api-public.md**

```markdown
# Modulo API Public — API Gateway EDGE

Responsabilita': API Gateway REST pubblico con CDN CloudFront.

## File Structure

```text
modules/api-public/
├── _input.tf       # standard + create_shared_resources, xray_enabled
├── _local.tf       # prefix, account_level_prefix
├── api-gateway.tf  # REST API (EDGE), /health mock
└── api-deploy.tf   # Deployment, Stage, method settings (burst=100, rate=50)
```

## Dependency

`dependency "vpc"` (opzionale, per mock_outputs).

## Differenze da api-private

| Aspetto       | api-private          | api-public        |
|---------------|----------------------|-------------------|
| Endpoint      | PRIVATE              | EDGE (CloudFront) |
| Route53       | Si (CNAME)           | No                |
| VPC Policy    | Si (Endpoint only)   | No                |
| burst_limit   | 10000                | 100               |
| rate_limit    | 100                  | 50                |
```

---

## Task 4: Crea reference/template-rds-postgres.md

**File coinvolti:**

- Crea: `siae-dev-forge/skills/siae-iac/reference/template-rds-postgres.md`

**Step 1: Scrivi template-rds-postgres.md**

```markdown
# Modulo RDS Postgres — Database con Flyway Migrations

Responsabilita': RDS PostgreSQL con subnet group, security group,
parameter group, e versionamento schema via Flyway.

## File Structure

```text
modules/rds-postgres/
├── _input.tf              # standard + db_name, engine_version, instance_class,
│                          #   allocated_storage, max_allocated_storage,
│                          #   multi_az, backup_retention_period,
│                          #   deletion_protection, performance_insights_enabled,
│                          #   flyway_enabled, config
├── _local.tf              # prefix, db_identifier, db_final_snapshot_id
├── _output.tf             # db_endpoint, db_port, db_name, db_instance_id,
│                          #   db_secret_arn, db_security_group_id
├── rds-instance.tf        # aws_db_instance (postgres, encryption, monitoring)
├── rds-subnet-group.tf    # aws_db_subnet_group (server subnets da vpc)
├── rds-parameter-group.tf # aws_db_parameter_group (tuning: log_statement,
│                          #   shared_preload_libraries, max_connections)
├── rds-security-group.tf  # aws_security_group (ingress 5432 da server subnets)
├── rds-secret.tf          # aws_secretsmanager_secret + random_password
│                          #   (credenziali master generate, mai in variabili TF)
├── rds-monitoring.tf      # Enhanced monitoring IAM role + CloudWatch alarms
│                          #   (CPUUtilization, FreeStorageSpace, DatabaseConnections)
└── rds-flyway.tf          # (opzionale) Null resource / Lambda per eseguire
                           #   Flyway migrations post-deploy
```

## Dependency

`dependency "vpc"` → `server_subnets`, `vpc_enterprise` (CIDR per SG).

## Versionamento Schema — Pattern Flyway

Il template fornisce la struttura, il progetto che adotta il template
popola la cartella migrations/:

```text
migrations/
├── V1__init_schema.sql
├── V2__add_users_table.sql
└── V3__add_index_on_email.sql
```

Convenzione naming: `V{N}__{descrizione}.sql` (doppio underscore).

Esecuzione:

- **CI/CD:** step Flyway nel workflow GitHub Actions post-deploy
- **Lambda:** `aws_lambda_function` che esegue Flyway migrate in VPC
  (per ambienti dove il CI/CD non ha accesso diretto al DB)

Il modulo Terraform NON esegue migrations direttamente.
Espone output (endpoint, secret ARN) consumati dal pipeline CI/CD.

## Security

- Credenziali master in Secrets Manager (mai in variabili TF — V8)
- Encryption at rest: `aws_kms_key` dedicata
- Encryption in transit: parameter group `rds.force_ssl = 1`
- Deletion protection: `true` in prod/certificazione
- Final snapshot: `${db_identifier}-final-${timestamp}`

## Sizing per ambiente

| Param                  | Sviluppo    | Collaudo    | Certificazione | Produzione   |
|------------------------|-------------|-------------|----------------|--------------|
| instance_class         | db.t3.micro | db.t3.small | db.t3.medium   | db.r6g.large |
| multi_az               | false       | false       | true           | true         |
| backup_retention       | 1           | 3           | 7              | 35           |
| storage                | 20 GB       | 20 GB       | 50 GB          | 100 GB       |
| deletion_protection    | false       | false       | true           | true         |
| performance_insights   | false       | false       | true           | true         |
```

---

## Task 5: Crea reference/template-dynamodb.md

**File coinvolti:**

- Crea: `siae-dev-forge/skills/siae-iac/reference/template-dynamodb.md`

**Step 1: Scrivi template-dynamodb.md**

```markdown
# Modulo DynamoDB — Tabella Completa

Responsabilita': DynamoDB table con GSI/LSI, streams, backup,
replica globale, contributor insights, table class.

## File Structure

```text
modules/dynamodb/
├── _input.tf                # standard + table_name, hash_key, range_key,
│                            #   billing_mode, read_capacity, write_capacity,
│                            #   attributes, global_secondary_indexes,
│                            #   local_secondary_indexes, ttl_attribute,
│                            #   stream_enabled, stream_view_type,
│                            #   point_in_time_recovery, table_class,
│                            #   replica_regions, contributor_insights,
│                            #   server_side_encryption, config
├── _local.tf                # prefix, table_full_name
├── _output.tf               # table_arn, table_name, table_id,
│                            #   stream_arn, table_hash_key
├── dynamodb-table.tf        # aws_dynamodb_table (core: hash/range key,
│                            #   billing, attributes, ttl, encryption,
│                            #   table_class, contributor_insights)
├── dynamodb-gsi.tf          # GSI dinamici via for_each su var.global_secondary_indexes
├── dynamodb-streams.tf      # Stream config + (opzionale) Lambda trigger
├── dynamodb-backup.tf       # aws_dynamodb_table_replica (multi-region)
│                            #   + point_in_time_recovery
│                            #   + aws_backup_plan per backup schedulati
├── dynamodb-autoscaling.tf  # aws_appautoscaling_target + policy
│                            #   (solo se billing_mode = PROVISIONED)
└── dynamodb-iam.tf          # IAM policy document per accesso tabella
                             #   (read-only, read-write, admin)
```

## Dependency

Nessuna dipendenza da vpc (DynamoDB e' fully managed).
Dipendenza opzionale da KMS se si usa CMK per encryption.

## Billing Mode

| Modo                          | Quando                                                       |
|-------------------------------|--------------------------------------------------------------|
| PAY_PER_REQUEST (on-demand)   | Default. Sviluppo, collaudo, workload imprevedibili          |
| PROVISIONED + autoscaling     | Produzione con pattern di traffico prevedibile               |

## Global Secondary Indexes — Pattern

Definiti come lista di oggetti in variabile:

```hcl
global_secondary_indexes = [
  {
    name               = "GSI-email"
    hash_key           = "email"
    range_key          = "created_at"
    projection_type    = "ALL"
    non_key_attributes = []
  }
]
```

Creati dinamicamente via `dynamic "global_secondary_index"` block.
LSI: stessa logica ma definiti inline (range_key diverso, stesso hash_key).

## Replica Globale (Multi-Region)

```hcl
replica_regions = ["eu-central-1"]  # vuoto = no replica
```

Crea `aws_dynamodb_table_replica` per ogni regione via `for_each`.
Streams obbligatori se replica attiva.

## Table Class

| Classe                          | Quando                                             |
|---------------------------------|----------------------------------------------------|
| STANDARD                        | Default. Workload con accesso frequente             |
| STANDARD_INFREQUENT_ACCESS      | Dati storici, accesso raro, risparmio ~60% storage  |

## Security

- Encryption at rest: KMS (`aws/dynamodb` default o CMK dedicata)
- IAM policy granulare esportata (non inline — V1)
- Gateway VPC endpoint consigliato per traffico privato

## Sizing per ambiente

| Param                  | Sviluppo        | Collaudo        | Cert.       | Produzione     |
|------------------------|-----------------|-----------------|-------------|----------------|
| billing_mode           | PAY_PER_REQUEST | PAY_PER_REQUEST | PROVISIONED | PROVISIONED    |
| point_in_time_recovery | false           | false           | true        | true           |
| contributor_insights   | false           | false           | false       | true           |
| table_class            | STANDARD        | STANDARD        | STANDARD    | STANDARD       |
| replica_regions        | []              | []              | []          | ["eu-central-1"] |
| backup_plan            | no              | no              | daily       | daily + PITR   |
```

---

## Task 6: Crea reference/template-cognito.md

**File coinvolti:**

- Crea: `siae-dev-forge/skills/siae-iac/reference/template-cognito.md`

**Step 1: Scrivi template-cognito.md**

```markdown
# Modulo Cognito — Autenticazione Multi-Scenario

Responsabilita': Cognito User Pool, Identity Pool e Federation,
configurabili per 3 scenari di autenticazione.

## Scenari Supportati

| Scenario                    | Risorse create                                  | Caso d'uso                                    |
|-----------------------------|-------------------------------------------------|-----------------------------------------------|
| A — User Pool classico      | User Pool, App Client, Domain                   | Login utenti (signup, signin, MFA, recovery)  |
| B — User Pool + Identity    | Tutto di A + Identity Pool, IAM roles            | Login + accesso diretto risorse AWS           |
| C — Federation only         | User Pool (no signup), SAML/OIDC IdP, App Client | SSO via Active Directory SIAE o IdP aziendale |

Selezione via variabile `auth_scenario`: `"user_pool"` | `"user_pool_identity"` | `"federation"`

## File Structure

```text
modules/cognito/
├── _input.tf                  # standard + auth_scenario, user_pool_name,
│                              #   password_policy, mfa_configuration,
│                              #   auto_verified_attributes, callback_urls,
│                              #   logout_urls, identity_providers,
│                              #   identity_pool_name,
│                              #   allow_unauthenticated, config
├── _local.tf                  # prefix, pool_name, domain_prefix
├── _output.tf                 # user_pool_id, user_pool_arn, app_client_id,
│                              #   app_client_secret_arn, identity_pool_id,
│                              #   user_pool_endpoint, hosted_ui_url
├── cognito-user-pool.tf       # aws_cognito_user_pool (schema attributes,
│                              #   password policy, MFA, account recovery,
│                              #   email verification, lambda triggers)
├── cognito-app-client.tf      # aws_cognito_user_pool_client
│                              #   (OAuth flows, scopes, callback/logout URLs,
│                              #   token validity, secret in Secrets Manager)
├── cognito-domain.tf          # aws_cognito_user_pool_domain
│                              #   (prefix-based o custom domain)
├── cognito-identity-pool.tf   # aws_cognito_identity_pool (solo scenario B)
│                              #   + IAM roles authenticated/unauthenticated
│                              #   count = var.auth_scenario == "user_pool_identity" ? 1 : 0
├── cognito-idp.tf             # aws_cognito_identity_provider (solo scenario C)
│                              #   SAML: metadata_url da IdP aziendale
│                              #   OIDC: issuer, client_id, client_secret
│                              #   for_each = var.auth_scenario == "federation" ? var.identity_providers : {}
├── cognito-lambda-triggers.tf # (opzionale) Lambda triggers per:
│                              #   pre_sign_up, post_confirmation,
│                              #   pre_token_generation, custom_message
└── cognito-iam.tf             # IAM roles per Identity Pool (scenario B):
                               #   authenticated_role, unauthenticated_role
```

## Dependency

Nessuna dipendenza da vpc (Cognito e' fully managed).
Dipendenza opzionale: se Lambda triggers → security group da vpc per VPC Lambda.

## Password Policy (default template)

| Param                              | Valore |
|------------------------------------|--------|
| minimum_length                     | 12     |
| require_lowercase                  | true   |
| require_uppercase                  | true   |
| require_numbers                    | true   |
| require_symbols                    | true   |
| temporary_password_validity_days   | 7      |

## MFA Configuration

| Modo     | Quando                         |
|----------|--------------------------------|
| OFF      | Sviluppo (solo per debug)      |
| OPTIONAL | Collaudo, certificazione       |
| ON       | Produzione — obbligatorio      |

MFA methods: `SOFTWARE_TOKEN_MFA` (TOTP) come default.
SMS_MFA opzionale (richiede SNS + spend limit).

## OAuth Flows

| Flow               | Quando                                         |
|--------------------|-------------------------------------------------|
| code (PKCE)        | Default — SPA, mobile, server-side apps         |
| implicit           | MAI — deprecato, insicuro                       |
| client_credentials | Machine-to-machine (API-to-API)                 |

## Federation — Scenario C

```hcl
identity_providers = {
  "SIAE-AD" = {
    provider_type = "SAML"
    metadata_url  = "https://adfs.siae.it/federationmetadata/..."
    attribute_mapping = {
      email    = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
      name     = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"
      username = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn"
    }
  }
}
```

User Pool con `allow_admin_create_user_only = true` (no self-signup).

## Token Validity

| Token         | Sviluppo | Produzione |
|---------------|----------|------------|
| Access token  | 1 ora    | 15 minuti  |
| ID token      | 1 ora    | 15 minuti  |
| Refresh token | 30 giorni | 7 giorni  |

## Security

- Client secret in Secrets Manager (mai in variabili TF — V8)
- HTTPS-only callback URLs (no `http://` in prod)
- Prevent user existence errors: `ENABLED`
- Advanced security mode: `ENFORCED` in prod (adaptive auth, compromised credentials)

## Sizing per ambiente

| Param              | Sviluppo | Collaudo | Cert.    | Produzione |
|--------------------|----------|----------|----------|------------|
| mfa_configuration  | OFF      | OPTIONAL | OPTIONAL | ON         |
| advanced_security  | OFF      | AUDIT    | AUDIT    | ENFORCED   |
| token_validity     | estesa   | estesa   | standard | restrittiva |
| deletion_protection | false   | false    | true     | true       |
| lambda_triggers    | {}       | {}       | opzionali | attivi    |
```

---

## Task 7: Aggiungi sezione 7 al SKILL.md

**File coinvolti:**

- Modifica: `siae-dev-forge/skills/siae-iac/SKILL.md` (dopo riga 211)

**Step 1: Aggiungi sezione 7 "Template Repo"**

Appendi in coda al file, prima della chiusura, la sezione:

```markdown

---

## 7. Template Repo — project-template-aws-iac

Reference: `itsiae/project-template-aws-iac`

Template infrastrutturale SIAE con moduli predefiniti per i casi d'uso piu' comuni.
I progetti che adottano il template eseguono merge via `npm run update:template`.

### Struttura

```text
live/                              modules/
├── terragrunt.hcl (root)          ├── vpc/
├── _envs/                         ├── api-private/
│   └── prod.tmpl                  ├── api-public/
├── vpc/                           ├── rds-postgres/
├── api-private/                   ├── dynamodb/
├── api-public/                    └── cognito/
├── rds-postgres/
├── dynamodb/
└── cognito/
    └── terragrunt.hcl.disabled
```

### Convenzioni template

| Regola            | Dettaglio                                                                 |
|-------------------|---------------------------------------------------------------------------|
| Stato default     | `.disabled` — rinomina senza suffisso per attivare                        |
| Variabili standard | `account_id`, `region`, `project`, `env`, `module`, `config`             |
| Naming locals     | `prefix = "${var.env}-${var.project}-${var.module}"`                      |
| Dipendenze        | `dependency` block Terragrunt con `mock_outputs` per plan/validate        |
| Config globale    | `config.yaml` alla root, env-specific in `live/_envs/{env}.yaml`          |
| Remote state      | S3 `${env}-${repo_name}-terraform-state` + DynamoDB lock                  |
| CI/CD             | GitHub Actions: plan per env, deploy manuale, release-please              |

### Moduli disponibili

| Modulo       | Responsabilita'                                          | Dipendenze     | Reference                                                     |
|--------------|----------------------------------------------------------|----------------|---------------------------------------------------------------|
| vpc          | Data lookup VPC enterprise, subnets, endpoints, SG       | Nessuna (root) | [template-vpc.md](reference/template-vpc.md)                  |
| api-private  | API Gateway REST PRIVATE (VPC Endpoint only)             | vpc            | [template-api-private.md](reference/template-api-private.md)  |
| api-public   | API Gateway REST EDGE (CloudFront)                       | vpc (opz.)     | [template-api-public.md](reference/template-api-public.md)    |
| rds-postgres | RDS PostgreSQL + Flyway migrations                       | vpc            | [template-rds-postgres.md](reference/template-rds-postgres.md) |
| dynamodb     | DynamoDB completo (GSI, streams, replica, autoscaling)   | Nessuna        | [template-dynamodb.md](reference/template-dynamodb.md)        |
| cognito      | Cognito User Pool / Identity Pool / Federation           | Nessuna        | [template-cognito.md](reference/template-cognito.md)          |

### Checklist — Creare un nuovo modulo nel template

1. Crea `modules/{nome-modulo}/` con: `_input.tf`, `_local.tf`, `_output.tf`, `{risorsa}.tf`
2. Variabili standard obbligatorie: `account_id`, `region`, `project`, `env`, `module`, `config`
3. Locals obbligatori: `prefix = "${var.env}-${var.project}-${var.module}"`
4. Crea `live/{nome-modulo}/terragrunt.hcl.disabled` con inputs e dependency
5. Se dipende da vpc: `dependency "vpc"` con `mock_outputs` per init/validate/plan
6. Aggiungi variabili environment-specific in `prod.tmpl`
7. Aggiorna README con descrizione modulo
8. Crea reference file in `skills/siae-iac/reference/template-{nome-modulo}.md`
```

**Step 2: Verifica conteggio righe**

```bash
wc -l siae-dev-forge/skills/siae-iac/SKILL.md
```

Output atteso: ~280 (sotto il limite 500)

**Step 3: Commit**

```bash
git add siae-dev-forge/skills/siae-iac/SKILL.md siae-dev-forge/skills/siae-iac/reference/
git commit -m "feat(siae-iac): aggiungi sezione template repo + 6 reference moduli"
```

---

## Task 8: Esegui test suite

**Step 1: Esegui tutti i test**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```

Output atteso: tutti i test passano (structure + catalog + skill-triggering)

**Step 2: Se falliscono, correggi e ri-esegui**

I test verificano struttura file, catalogo skill, e trigger. Possibili failure:
- Struttura reference/ non attesa → verificare test structure
- Conteggio righe SKILL.md → assicurarsi < 500
