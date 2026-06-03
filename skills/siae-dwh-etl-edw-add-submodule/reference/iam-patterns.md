# IAM Patterns — edw-orchestration-role.tf

Pattern ARN wildcard attualmente presenti nella policy `sfn2_edw_statemachine_permissions`
in `modules/edw/edw-orchestration-role.tf`.

## Wildcard attivi

| Pattern | Copre |
|---------|-------|
| `${env}-redshift-gold-edw-*` | SFN gold EDW |
| `${env}-edw-*` | Tutti i sottomoduli EDW (leaf e orchestratori) |
| `${env}-datalake-*` | SFN silver, crawler, etl datalake |
| `${env}-contact-center-*` | Flussi contact center |
| `${env}-sun-*` | Flussi sun |
| `${env}-controllo-corrispettivi-*` | Flussi controllo corrispettivi |

## ARN con nome esplicito (non wildcard)

| ARN esplicita | Motivo |
|---------------|--------|
| `${env}-bm-utilizzazioni-ingestion-orchestration` | `resource_name`=`bm-utilizzazioni` — non coperto da wildcard |
| `${env}-codifica-ingestion-orchestration` | `resource_name`=`codifica` — non coperto da wildcard |

## Regola di verifica

Per ogni nuova `ingestion_sfn`, controlla se il nome inizia con uno dei prefissi wildcard:
- `{env}-edw-` → ✅ coperto
- `{env}-datalake-` → ✅ coperto
- qualsiasi altro prefisso → ⚠️ aggiungi ARN esplicite (stateMachine + execution)

**Pattern da aggiungere:**
```hcl
"arn:aws:states:${var.region}:${var.account_id}:stateMachine:{ingestion_sfn}",
"arn:aws:states:${var.region}:${var.account_id}:execution:{ingestion_sfn}:*"
```
