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

| Modo                        | Quando                                              |
|-----------------------------|-----------------------------------------------------|
| PAY_PER_REQUEST (on-demand) | Default. Sviluppo, collaudo, workload imprevedibili |
| PROVISIONED + autoscaling   | Produzione con pattern di traffico prevedibile       |

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

| Classe                     | Quando                                            |
|----------------------------|---------------------------------------------------|
| STANDARD                   | Default. Workload con accesso frequente            |
| STANDARD_INFREQUENT_ACCESS | Dati storici, accesso raro, risparmio ~60% storage |

## Security

- Encryption at rest: KMS (`aws/dynamodb` default o CMK dedicata)
- IAM policy granulare esportata (non inline — V1)
- Gateway VPC endpoint consigliato per traffico privato

## Sizing per ambiente

| Param                  | Sviluppo        | Collaudo        | Cert.       | Produzione       |
|------------------------|-----------------|-----------------|-------------|------------------|
| billing_mode           | PAY_PER_REQUEST | PAY_PER_REQUEST | PROVISIONED | PROVISIONED      |
| point_in_time_recovery | false           | false           | true        | true             |
| contributor_insights   | false           | false           | false       | true             |
| table_class            | STANDARD        | STANDARD        | STANDARD    | STANDARD         |
| replica_regions        | []              | []              | []          | ["eu-central-1"] |
| backup_plan            | no              | no              | daily       | daily + PITR     |
