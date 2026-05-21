# Reproduction voice guide

Every step in a QA test case (phase 7 output) MUST be expressed using
exactly **one** of the eight actor primitives defined here. A step that
mixes primitives, omits the primitive, or uses passive voice is a
violation and is rejected by `tools/repro_voice_lint.py`.

The goal is twofold: (a) make every step physically reproducible by a
human manual tester without ambiguity; (b) make the report
language-agnostic at the schema level — Italian and English share the
same primitives.

## The eight actor primitives

| Tag | Display label (EN) | Display label (IT) | Who performs |
|---|---|---|---|
| `ui-user` | UI user | Utente UI | a human using the application UI (web, mobile, desktop) |
| `api-caller` | API caller | Chiamante API | a human or tool issuing HTTP / gRPC / GraphQL calls (Postman, curl, SDK) |
| `event-publisher` | Event publisher | Pubblicatore di eventi | a human or tool publishing a message to a topic / queue / event bus |
| `scheduler` | Scheduler | Schedulatore | a human configuring or triggering a scheduled rule / cron |
| `iac-operator` | IaC operator | Operatore IaC | a human running `terraform apply` / `cdk deploy` / `aws cloudformation deploy` |
| `batch-runner` | Batch runner | Esecutore batch | a human invoking a batch job (Airflow DAG, Glue job, dbt run) |
| `db-operator` | DB operator | Operatore DB | a human running SQL directly on a database |
| `observer` | Observer | Osservatore | a human inspecting state (logs, dashboards, DB state, metrics) — never mutates |

## Step format

Every step in `qa_report.md` follows this exact shape:

```
N. (<tag>) <action sentence in the imperative, active voice>
```

The `<tag>` is one of the eight tags above. The action sentence is:

- in the **imperative** mood (a human is being instructed),
- in the **active** voice,
- **specific**: name the field, button, endpoint, payload, queue, cron
  expression, table, dashboard explicitly,
- **single-action**: one verb + one object per step. Two verbs → split
  into two steps.

## Allowed phrasings (EN + IT examples per primitive)

### `ui-user`

| EN | IT |
|---|---|
| Click the button labeled "<Submit>" | Cliccare sul bottone "<Invia>" |
| Type "<value>" in the field "<name>" | Digitare "<valore>" nel campo "<nome>" |
| Tap the row "<row-title>" | Toccare la riga "<titolo-riga>" |
| Swipe left on the card "<id>" | Strisciare a sinistra sulla card "<id>" |
| Press the system back button | Premere il bottone "indietro" di sistema |
| Open the page "<route>" | Aprire la pagina "<rotta>" |

### `api-caller`

| EN | IT |
|---|---|
| Send HTTP POST /v1/users with body `{...}` | Inviare HTTP POST /v1/users con body `{...}` |
| Send HTTP GET /v1/orders?status=pending | Inviare HTTP GET /v1/orders?status=pending |
| Send gRPC call <Service>.<Method> with proto `{...}` | Inviare chiamata gRPC <Service>.<Metodo> con proto `{...}` |
| Send GraphQL mutation `createOrder(input: {…})` | Inviare mutazione GraphQL `createOrder(input: {…})` |
| Repeat the previous HTTP call within 100 ms | Ripetere la precedente HTTP entro 100 ms |

### `event-publisher`

| EN | IT |
|---|---|
| Publish message `{...}` to SQS queue "<name>" | Pubblicare messaggio `{...}` sulla coda SQS "<nome>" |
| Publish event `{...}` to EventBridge bus "<bus>" with source "<source>" | Pubblicare evento `{...}` sul bus EventBridge "<bus>" con source "<source>" |
| Send Kafka record `{...}` to topic "<topic>", partition <p> | Inviare record Kafka `{...}` sul topic "<topic>", partizione <p> |
| Publish SNS notification `{...}` to topic ARN "<arn>" | Pubblicare notifica SNS `{...}` sul topic ARN "<arn>" |

### `scheduler`

| EN | IT |
|---|---|
| Set EventBridge schedule "<name>" to cron `0 9 * * ? *` | Configurare la schedule EventBridge "<nome>" su cron `0 9 * * ? *` |
| Trigger the scheduled rule "<name>" manually | Triggerare manualmente la rule schedulata "<nome>" |
| Set Airflow DAG "<id>" `schedule_interval` to `@hourly` | Impostare lo `schedule_interval` del DAG Airflow "<id>" a `@hourly` |

### `iac-operator`

| EN | IT |
|---|---|
| Run `terraform apply` against module "<path>" with var `foo=bar` | Eseguire `terraform apply` sul modulo "<path>" con var `foo=bar` |
| Run `cdk deploy <Stack>` with context `--context env=prod` | Eseguire `cdk deploy <Stack>` con `--context env=prod` |
| Run `aws cloudformation deploy --template-file <file> --stack-name <name>` | Eseguire `aws cloudformation deploy --template-file <file> --stack-name <name>` |

### `batch-runner`

| EN | IT |
|---|---|
| Invoke Glue job "<name>" with input `{...}` | Invocare il job Glue "<nome>" con input `{...}` |
| Trigger Airflow DAG "<id>" with config `{...}` | Triggerare il DAG Airflow "<id>" con config `{...}` |
| Run `dbt run --select <model>` against the warehouse "<env>" | Eseguire `dbt run --select <model>` sul warehouse "<env>" |
| Submit Spark job "<name>" with arg `--date 2026-05-15` | Sottomettere lo Spark job "<nome>" con arg `--date 2026-05-15` |

### `db-operator`

| EN | IT |
|---|---|
| Execute SQL `INSERT INTO orders (...) VALUES (...)` on database "<db>" | Eseguire SQL `INSERT INTO orders (...) VALUES (...)` sul database "<db>" |
| Execute SQL `UPDATE users SET email=... WHERE id=<id>` on database "<db>" | Eseguire SQL `UPDATE users SET email=... WHERE id=<id>` sul database "<db>" |
| Execute SQL `SELECT * FROM <table>` and confirm row count > 0 | Eseguire SQL `SELECT * FROM <table>` e confermare row count > 0 |

### `observer`

| EN | IT |
|---|---|
| Open CloudWatch log group "<name>" and look for entries with level=ERROR | Aprire il log group CloudWatch "<nome>" e cercare entry con level=ERROR |
| Open the dashboard at <url> and inspect metric "<metric>" for the last 5 minutes | Aprire il dashboard <url> e ispezionare la metrica "<metric>" negli ultimi 5 minuti |
| Open table "<table>" in the database "<db>" and inspect row <id> | Aprire la tabella "<table>" sul database "<db>" e ispezionare la riga <id> |
| Open the UI page "<route>" and inspect the displayed value of "<field>" | Aprire la pagina UI "<rotta>" e ispezionare il valore visualizzato di "<campo>" |

## Forbidden phrasings (lint rules enforced by `tools/repro_voice_lint.py`)

Each rule is checked per step; a violation is reported with the rule id.

| Rule id | Description | Example violation | Why it's wrong |
|---|---|---|---|
| V-001 | Passive voice | "The button is clicked" / "Il bottone viene cliccato" | The actor is implicit; reproducer can't tell who acts |
| V-002 | Modal verbs without instruction | "The system should reject the request" / "Il sistema dovrebbe rifiutare" | Describes expected behavior, not an action |
| V-003 | Missing actor tag | "Click submit" without `(ui-user)` prefix | Reproducer cannot pick the right tool / role |
| V-004 | Multiple verbs / actions per step | "Click submit and wait for response" | Steps must be atomic; split into two |
| V-005 | Vague target | "Click the button" without label | A QA can't find the button |
| V-006 | "Verify internally" | "Verify internally that the cache is invalidated" | "Internally" is unobservable; replace with an `observer` step |
| V-007 | Self-reference without primitive | "Repeat step 2" without specifying the primitive | OK as an `(<inherit>)` only when the next primitive is identical; otherwise spell it out |
| V-008 | Tool-specific where it shouldn't be | "Open Postman" instead of "Send HTTP POST …" | Tooling is the QA's choice; the step is the action |
| V-009 | English / Italian mix in body when `lang` is set | "(ui-user) Premere il button Submit" with `lang=it` | Pick one; mixing breaks i18n |
| V-010 | Time-without-units in race steps | "Wait briefly" | Specify duration with units (e.g. "within 100 ms") |

## Step-count and ordering guidance

- A reproduction must have **between 2 and 12 steps**. Fewer than 2 = the
  bug is unrepro from a user perspective and is moved to
  `hypotheses.json`. More than 12 = the user journey is too complex;
  split into sub-cases or move to `open_questions.md`.
- The **first step** is normally the most-specific actor (an
  `api-caller` for an HTTP-route entry, a `ui-user` for a `ui-screen`
  entry, an `event-publisher` for a `message-consumer` entry).
- The **last step** is normally an `observer` step that names what the
  QA should look at to confirm the bug.
- Steps that involve concurrency (BP-003, BP-011, BP-014) MUST name
  durations with units ("within 100 ms", "within 1 second", "before the
  first call returns") to satisfy rule V-010.

## Localization choice

A run is in exactly one language. When `args.lang = "it"`, every step,
expected result, actual result, suggested fix, and journey title is
Italian; only the actor-primitive **tag** (the parenthesized `(ui-user)`
prefix) and the schema field names remain English. When `args.lang =
"en"`, everything stays English.

The eight tags themselves are **never translated** (they are stable
identifiers consumed by `repro_voice_lint.py`).
