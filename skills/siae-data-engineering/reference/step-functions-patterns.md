# Step Functions Patterns — Orchestrazione ETL

> Basato su pattern reali estratti da `datalake-anagrafica-dipendenti-etl`.

---

## Pattern architetturale

L'orchestrazione ETL usa un pattern **Map con error handling per-branch**:
ogni Glue job gira in parallelo (fino a `MaxConcurrency`), i fallimenti vengono
isolati per-branch, e l'aggregazione finale decide l'esito globale.

```
Lambda RETRIEVE (quali tabelle aggiornare?)
  → Choice (lista vuota? → Succeed)
  → Map (MaxConcurrency=10)
      Per ogni tabella:
        → Adjust timestamp (overlap 1 giorno)
        → Glue Job (.sync)
            [ok] → Lambda UPDATE → EventBridge notify success → {status: SUCCEEDED}
            [ko] → EventBridge notify failure → {status: FAILED}
  → Filtra FAILED
  → Choice (ci sono falliti?)
      → Si → Fail
      → No → Succeed
```

---

## Lambda di coordinamento

La Lambda `silver_updates_manager` gestisce i timestamp per il processing incrementale.

### Mode RETRIEVE

- Input: `silver_mapping` (dizionario tabella → lista tabelle silver)
- Azione: legge da DynamoDB `last_silver_update_time` per ogni tabella
- Output: lista di oggetti con `{table_name, last_silver_update_time, next_silver_update_time}`

### Mode UPDATE

- Input: `{table_name, next_silver_update_time}`
- Azione: scrive `next_silver_update_time` come nuovo `last_silver_update_time` in DynamoDB
- Output: conferma aggiornamento

### Silver mapping

Il mapping e' inlineato nella Step Function definition (template Terraform):

```json
{
  "areedipendenti": ["areedipendenti"],
  "dipendenti": ["dipendenti"],
  "unitaorganizzative": ["unitaorganizzative"]
}
```

La struttura a lista `["nome"]` supporta mapping 1:N (una sorgente → piu' tabelle silver),
anche se al momento il mapping e' 1:1.

---

## Map State — Parallelismo controllato

```json
{
  "Type": "Map",
  "MaxConcurrency": 10,
  "ItemsPath": "$.result",
  "Iterator": { ... },
  "ResultPath": "$.map_results"
}
```

- **MaxConcurrency**: controlla quanti Glue job girano in parallelo (default 10)
- **Non fail-fast**: un branch fallito non blocca gli altri. Ogni branch imposta `{status: "FAILED"}` o `{status: "SUCCEEDED"}` e termina
- **ResultPath**: i risultati di tutti i branch vengono aggregati in `$.map_results`

---

## Error handling per-branch

Dentro il Map, ogni branch ha la sua gestione errori:

```json
{
  "Type": "Task",
  "Resource": "arn:aws:states:::glue:startJobRun.sync",
  "Parameters": {
    "JobName": "${job_prefix}-${table_name}",
    "Arguments": {
      "--last_silver_update_time.$": "$.last_silver_update_time",
      "--next_silver_update_time.$": "$.next_silver_update_time",
      "--force_no_window": "${force_no_window}"
    }
  },
  "ResultPath": null,
  "Catch": [{
    "ErrorEquals": ["States.ALL"],
    "Next": "NotifyETLError",
    "ResultPath": "$.error"
  }]
}
```

**Punti chiave:**
- `ResultPath: null` — l'output del Glue job viene scartato, l'input viene propagato
- `Catch` con `States.ALL` — qualsiasi errore viene catturato
- Il branch fallito procede a `NotifyETLError` → `SetFailedStatus` (non termina il Map)

---

## Aggregazione finale

Dopo il Map, i risultati vengono filtrati per trovare i falliti:

```json
{
  "Type": "Pass",
  "Parameters": {
    "failed_jobs.$": "$.map_results[?(@.status == 'FAILED')]"
  },
  "Next": "CheckForFailures"
}
```

Il Choice successivo controlla se `failed_jobs[0]` esiste:
- **Esiste** → `Fail` state con `Error: GlueJobFailed`
- **Non esiste** → `Succeed`

---

## EventBridge notifications

### Successo

```json
{
  "Type": "Task",
  "Resource": "arn:aws:states:::events:putEvents",
  "Parameters": {
    "Entries": [{
      "EventBusName": "${silver_notification_eventbus_name}",
      "Source": "${source}",
      "DetailType.$": "States.Format('silver-notification/${scope}/{}', $.table_name)",
      "Detail": {
        "table_name.$": "$.table_name",
        "status": "SUCCEEDED"
      }
    }]
  }
}
```

### Failure

```json
{
  "Type": "Task",
  "Resource": "arn:aws:states:::events:putEvents",
  "Parameters": {
    "Entries": [{
      "EventBusName": "${dataplatform_errors_eventbus_name}",
      "Source": "${source}",
      "DetailType": "silver-${scope}-glue-failure",
      "Detail": {
        "table_name.$": "$.table_name",
        "error.$": "$.error.Cause"
      }
    }]
  }
}
```

---

## AdjustUpdateTime — Overlap di sicurezza

```json
{
  "Type": "Choice",
  "Choices": [{
    "Variable": "$.last_silver_update_time",
    "StringEquals": "0",
    "Next": "KeepOriginalTime"
  }],
  "Default": "AdjustUpdateTime"
}
```

- Se `last_silver_update_time == "0"` (prima esecuzione), non sottrarre nulla
- Altrimenti, sottrai 86400 secondi (1 giorno) per overlap di sicurezza

```json
{
  "Type": "Pass",
  "Parameters": {
    "last_silver_update_time.$": "States.Format('{}', States.MathAdd(States.StringToJson($.last_silver_update_time), -86400))"
  }
}
```

---

## Terraform integration

La Step Function definition e' un template Terraform in `orchestration/silver-etl.json`:

```hcl
resource "aws_sfn_state_machine" "silver_batch_orchestration" {
  name     = "${local.prefix}-silver-orchestration"
  role_arn = aws_iam_role.silver_batch_orchestration.arn
  definition = templatefile("${path.module}/orchestration/silver-etl.json", {
    env                                  = var.env
    account_id                           = var.account_id
    job_prefix                           = "${local.prefix}"
    scope                                = "anagrafica-dipendenti"
    silver_updates_manager_lambda_arn    = var.silver_updates_manager_lambda_arn
    silver_notification_eventbus_name    = var.eventbridge_datalake_bus.name
    dataplatform_errors_eventbus_name    = var.eventbridge_dataplatform_errors.name
    force_no_window                      = var.config.stepfunction_force_no_window
    source                               = "${var.env}-${var.project}"
  })
}
```

I placeholder `${...}` sono variabili Terraform, non Step Functions nativi.

---

## IAM roles

La Step Function usa **due IAM roles** distinti:

| Role | Trust policy | Permessi |
|------|-------------|----------|
| `silver_batch_orchestration` | `states.amazonaws.com` | `glue:*` su job del progetto, `events:PutEvents` su entrambi i bus, `lambda:InvokeFunction`, XRay |
| `silver_batch_trigger_orchestration` | `events.amazonaws.com` | `states:StartExecution` sulla state machine |

Il primo e' usato dalla state machine per eseguire operazioni.
Il secondo e' usato da EventBridge per avviare la state machine.

---

## Checklist nuova Step Function ETL

- [ ] Definisci il `silver_mapping` con tutte le tabelle del dominio
- [ ] Usa Map state con `MaxConcurrency` appropriato (default 10)
- [ ] Catch per-branch (non globale) — ogni job deve poter fallire indipendentemente
- [ ] Aggregazione finale per contare i falliti
- [ ] EventBridge notify su entrambi i bus (successo + errore)
- [ ] Lambda RETRIEVE/UPDATE per gestione timestamp
- [ ] AdjustUpdateTime con overlap 1 giorno (tranne prima esecuzione)
- [ ] Template Terraform con `templatefile()` per parametrizzazione
- [ ] Due IAM roles separati (execution + trigger)
- [ ] `ResultPath: null` sui task Glue (non propagare output inutile)
