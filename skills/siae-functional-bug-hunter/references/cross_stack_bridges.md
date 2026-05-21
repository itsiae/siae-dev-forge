# Cross-stack bridges

This file governs **language-agnostic identifier resolution** across
analysis units. It is the dispatcher that lets a TypeScript
`fetch("/v1/users")` match a Python `@app.post("/v1/users")`, or a
Terraform `aws_sqs_queue.name` match a Java `@SqsListener("orders")`.

## Path Normalization Rules

Before matching paths across stacks, normalize to canonical form: `/v1/users/{id}`.

| Source format     | Stack        | Canonical            |
|-------------------|--------------|----------------------|
| `/v1/users/:id`     | Express/Koa  | `/v1/users/{id}`       |
| `/v1/users/<id>`    | Flask        | `/v1/users/{id}`       |
| `/v1/users/<id:int>`| Flask typed  | `/v1/users/{id}`       |
| `/v1/users/{id}`    | FastAPI/OAS  | `/v1/users/{id}`       |
| `/v1/users/{id:int}`| FastAPI typed| `/v1/users/{id}`       |

Normalization MUST be applied before any bridge match. Type annotations are stripped.
Query params are excluded from bridge path matching.

The reference implementation lives in `scripts/path_normalize.py` and is
imported by `scripts/generate_payloads.py` and (in future) by the
dependency-closure resolver. The unit tests in
`tests/test_path_normalization.py` enumerate all five cases above; they
MUST pass before any change to the normalizer is merged.

Stack-specific files (`stacks/*.md`) contribute **local** bridge hints
(what each stack emits as boundary identifiers); this file contains the
**global** resolution table.

## Bridge identifier types

The `boundary_identifier_registry.json` (built in phase 2) is keyed by
`(kind, identifier)`. The kinds are:

| Kind | Identifier shape | Examples |
|---|---|---|
| `http-path` | `<METHOD> <path-template>` | `POST /v1/users`, `GET /api/orders/{id}` |
| `grpc-service-method` | `<package.Service>/<Method>` | `siae.payments.v1.PaymentService/CreatePayment` |
| `graphql-field` | `<RootType>.<FieldName>` | `Mutation.createOrder`, `Query.user` |
| `queue-name` | `<queue-name>` (literal, after env resolution) | `orders-prod`, `notifications-dlq` |
| `topic-name` | `<topic-name>` (Kafka, SNS, MSK, EventBridge bus) | `user-events`, `arn:aws:sns:eu-west-1:123:user-signup` |
| `bucket-key` | `<bucket-name>` or `<bucket-name>/<key-prefix>` | `siae-pdf-archive`, `siae-pdf-archive/uploads/` |
| `event-bus-source-detail` | `<bus>/<source>/<detail-type>` | `default/siae.payments/PaymentSucceeded` |
| `lambda-arn` | `<function-name>` or full ARN | `payment-processor`, `arn:aws:lambda:eu-west-1:123:function:payment-processor` |
| `sfn-arn` | `<state-machine-name>` or full ARN | `OrderFulfillment` |
| `dbt-source` | `<source>.<table>` | `raw.orders` |
| `db-table` | `<schema>.<table>` | `public.orders`, `dbo.Users` |
| `iam-role-arn` | `<role-name>` or full ARN | `lambda-payment-role` |
| `feature-flag-key` | `<flag-key>` | `new-checkout-flow`, `feature.payments.v2` |

## Resolution rules

The runtime resolves an identifier in three passes:

1. **Literal match**: the identifier appears as a string literal in
   both the producer (caller) and the consumer (handler) unit.
2. **Environment-resolved match**: the identifier is constructed from
   environment variables / config keys; the runtime walks the
   declaration chain (e.g. `process.env.QUEUE_NAME` → `.env.example` →
   IaC `aws_sqs_queue.name`). When the chain has gaps, the runtime
   records a `partial-resolution` flag and continues.
3. **Heuristic match**: the identifier shape strongly suggests a match
   (e.g. a path with `/v1/` segments and matching parameter names).
   Heuristic matches are recorded with `confidence: low_partial`.

## Mapping table (per-language calling patterns)

For each calling pattern, the resolver applies the listed extraction
rule to produce the registry key.

### `http-path`

| Caller stack | Pattern | Extraction |
|---|---|---|
| ts-js | `fetch("/v1/x", { method: "POST" })`, `axios.post("/v1/x", ...)`, `httpClient.get<T>("/v1/x")` | `<METHOD> <literal-path>` |
| java | `restTemplate.postForObject("/v1/x", ...)`, `WebClient.get().uri("/v1/x")` | `<METHOD> <literal-path>` |
| python | `requests.post("/v1/x", ...)`, `httpx.AsyncClient().get("/v1/x")` | `<METHOD> <literal-path>` |
| go | `http.NewRequest("POST", "/v1/x", body)` | `<METHOD> <literal-path>` |
| rust | `reqwest::Client::post(url + "/v1/x")` | `<METHOD> <literal-path>` |
| ruby | `Net::HTTP.post(URI("/v1/x"), ...)`, `Faraday.get("/v1/x")` | `<METHOD> <literal-path>` |
| dotnet | `httpClient.PostAsync("/v1/x", ...)` | `<METHOD> <literal-path>` |
| flutter-dart | `dio.post("/v1/x", data: ...)`, `http.get(Uri.parse("/v1/x"))` | `<METHOD> <literal-path>` |
| terraform-hcl | `aws_apigatewayv2_route.route_key = "POST /v1/x"` | `<route_key>` (already in shape) |
| aws-serverless | SAM `Path: /v1/x` + `Method: post` | `POST /v1/x` |

Handlers are extracted symmetrically (e.g. `@app.post("/v1/x")` →
`POST /v1/x`).

### `queue-name`

| Stack | Producer pattern | Consumer pattern |
|---|---|---|
| java | `sqsClient.sendMessage(SendMessageRequest.builder().queueUrl(QUEUE).build())` | `@SqsListener("orders-prod")` |
| python | `boto3.client('sqs').send_message(QueueUrl=q, ...)` | Lambda handler with SQS event source |
| ts-js | `new SendMessageCommand({ QueueUrl: q, ... })` | Lambda handler typed `SQSEvent` |
| go | `sqsClient.SendMessage(ctx, &sqs.SendMessageInput{QueueUrl: &q, ...})` | Lambda handler typed `events.SQSEvent` |
| terraform-hcl | `aws_sqs_queue.x.name` (declaration) | — (declaration only) |
| aws-serverless | `SqsEventProperties` / `events.Sqs` (declaration of consumer wiring) | — (consumer link) |

The runtime resolves a queue name across units by:

1. literal queue-name string equality (case-sensitive),
2. environment-variable indirection (the queue URL var is looked up in
   IaC outputs and `.env*` files),
3. ARN suffix match (queue name is the ARN's last `:` segment).

### `lambda-arn`

| Caller pattern | Source |
|---|---|
| `lambdaClient.Invoke(FunctionName: "payment-processor")` | any stack |
| Step Functions ASL `Resource: arn:aws:lambda:...:function:payment-processor` | aws-serverless |
| `aws_lambda_invocation.function_name = "payment-processor"` | terraform-hcl |

Handler-side resolution: the SAM template / CDK code / Terraform
`aws_lambda_function` declares `function_name` and `handler`. The
runtime joins on `function_name` and then resolves `handler` to the
implementation unit (Java / Python / TS / Go / Rust / .NET).

### `topic-name` (Kafka / SNS / MSK / EventBridge bus)

The runtime treats SNS topics and Kafka topics symmetrically. EventBridge
buses are joined by `<bus>/<source>/<detail-type>` triple.

| Caller pattern | Source |
|---|---|
| `snsClient.publish(...).topicArn(arn)` | aws sdk (any) |
| `kafkaProducer.send(new ProducerRecord("topic", ...))` | java / ts-js / python / go |
| `eventBridgeClient.putEvents([{ Source, DetailType, Detail }])` | aws sdk (any) |

Handler patterns mirror these via subscription / consumer-group / rule.

### `feature-flag-key`

A feature flag is a cross-cutting identifier. The runtime resolves it
across stacks when:

- the same string literal appears in two units (BP-017 condition),
- two flag SDK clients (LaunchDarkly, ConfigCat, Flagsmith, Unleash,
  AWS AppConfig) check the same key.

Flag resolution does NOT require IaC; it is purely string-based.

### `dbt-source`

dbt `source('raw', 'orders')` resolves to a producer in `aws-serverless`
(a Lambda writing to S3) or in any stack that writes to the same
warehouse table. The bridge key is `raw.orders` (after combining the
two arguments).

## Environment-variable indirection

When a caller uses `process.env.X` (TS), `os.environ['X']` (Python),
`@Value("${x}")` (Java), `viper.GetString("x")` (Go), etc., the runtime
attempts to resolve `X` by:

1. searching for a literal assignment in the same unit (`.env`,
   `.env.example`, `application.yaml`, `appsettings.json`),
2. searching IaC files for a matching output / `Environment` block,
3. searching the closure registry for any unit that declares `X` as
   an environment variable (with a literal value).

When resolution fails completely, the bridge is recorded with
`confidence: low_partial` and surfaced in `open_questions.md`.

## Adding a new bridge kind

To add a new bridge kind (minor semver bump):

1. Append a row to the "Bridge identifier types" table above.
2. Add a per-stack pattern in the "Mapping table" section.
3. Update `scripts/dependency_closure.py` so the registry includes the
   new kind.
4. Add at least one entry in `eval/golden_set/` exercising the new
   bridge.
