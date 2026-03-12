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

| Param                | Sviluppo    | Collaudo    | Certificazione | Produzione   |
|----------------------|-------------|-------------|----------------|--------------|
| instance_class       | db.t3.micro | db.t3.small | db.t3.medium   | db.r6g.large |
| multi_az             | false       | false       | true           | true         |
| backup_retention     | 1           | 3           | 7              | 35           |
| storage              | 20 GB       | 20 GB       | 50 GB          | 100 GB       |
| deletion_protection  | false       | false       | true           | true         |
| performance_insights | false       | false       | true           | true         |
