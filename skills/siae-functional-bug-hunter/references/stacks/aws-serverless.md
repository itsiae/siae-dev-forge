# Stack: AWS serverless

## Stack id

`aws-serverless`

## Manifest fingerprints

- File globs: `**/template.yaml`, `**/template.yml` (SAM); `**/cdk.json`, `**/lib/*-stack.ts`, `**/lib/*-stack.py`, `**/cdk.out/**` (CDK); `**/serverless.yml`, `**/serverless.yaml` (Serverless Framework); `**/*.asl.json`, `**/*.asl.yaml` (Step Functions ASL); `**/samconfig.toml`; `**/*.cloudformation.yaml`, `**/*.cfn.yaml`.
- Content patterns: `AWSTemplateFormatVersion: '2010-09-09'` + `Transform: AWS::Serverless-2016-10-31` (SAM); `"App"` constructs in CDK TS/Python; `States` + `StartAt` top-level keys (ASL).
- Negative match: pure Terraform (`*.tf`) → dispatched to `terraform-hcl.md`.

## Analysis-unit granularity

- **SAM project**: each `template.yaml` is one analysis unit.
- **CDK monorepo**: each stack file is one analysis unit (CDK app may be multiple stacks).
- **Serverless Framework**: each `serverless.yml` is one unit.
- **Step Functions**: each `*.asl.json` / `*.asl.yaml` is treated as a child unit of the SAM / CDK template that references it.
- See [../repo_granularity.md](../repo_granularity.md).

## Parser

- No tree-sitter grammar; YAML / JSON parsed via standard libraries (`yaml.safe_load`, `json.loads`).
- CDK TypeScript / Python: dispatched to `typescript-javascript.md` / `python.md` for the **construct definition code**, then the synthesized template is analyzed here. If synthesis output is not available (no `cdk.out/`), the runtime analyzes the source construct calls directly and records `synthesis-not-available` in `coverage.md`.
- ASL: JSON / YAML parsed; state transitions modeled as a directed graph.

## Entry-point kinds detected

| AWS surface | `entry_point.kind` | Detection signal |
|---|---|---|
| API Gateway REST / HTTP | `http-route` | `AWS::Serverless::Api` / `AWS::ApiGatewayV2::Api` + Function event `Type: Api` / `Type: HttpApi` |
| Lambda Function URL | `http-route` | `AWS::Lambda::Url` resource or `FunctionUrlConfig` in SAM |
| Lambda direct invoke | `cli-command` (from operator) | function with no event source = manual / SDK-invoked only |
| EventBridge schedule | `scheduled-job` | `AWS::Events::Rule` with `ScheduleExpression` |
| EventBridge rule (event pattern) | `event-publisher` (consumed by Lambda) | `AWS::Events::Rule` with `EventPattern` + target |
| SQS-triggered Lambda | `message-consumer` | function event `Type: SQS` |
| SNS-triggered Lambda | `message-consumer` | function event `Type: SNS` |
| Kinesis / DynamoDB Streams | `message-consumer` | function event `Type: Kinesis` / `Type: DynamoDB` |
| Step Functions state machine entry | `sfn-start` | `StartExecution` API surface; ASL `StartAt` state |
| Cognito Lambda triggers | `event-publisher` (Cognito → Lambda) | function event `Type: Cognito` + `Trigger:` |
| AppSync resolver (Lambda data source) | `graphql-resolver` | AppSync schema + resolver mapping pointing to a Lambda |
| S3-triggered Lambda | `event-publisher` | function event `Type: S3` |

## Inputs typing

- API Gateway: input is the event shape (`APIGatewayProxyEvent` v1 or v2); `pathParameters`, `queryStringParameters`, `body` are recorded as separate inputs.
- SQS / SNS / Kinesis: input is the `Records` array; per-record body type is recorded as `unknown` unless a content-based schema is declared (`AWS::Lambda::EventInvokeConfig` schema, or contract-test schemas).
- Step Functions: input is the JSON passed to `StartExecution`; ASL `Parameters` and `InputPath` define the shape per state.
- IAM permissions attached to the function are recorded as `inputs[].validation` hints (e.g. "function can only read this bucket").

## Side-effect detection

- Every IaC resource is a side effect (see also `terraform-hcl.md`).
- Function `Policies:` / `Role:` attachments record which AWS services the function can mutate at runtime.
- ASL `Resource: arn:aws:lambda:...` and `Resource: arn:aws:states:::aws-sdk:...` are recorded as side-effect targets per state.
- `Throttle` / `ReservedConcurrentExecutions` settings are recorded as backpressure hints.

## Cross-stack bridge hints

- Lambda handler ARN → cross-reference with the implementation unit (Java / Python / TS / Go / Rust / .NET) by the `Handler:` field.
- API Gateway route → `http-route` lookup in the implementation unit's framework (e.g. FastAPI `@app.post('/v1/users')`).
- Step Functions task ARN → resolved within this unit OR to an external service (recorded as boundary).
- EventBridge target ARNs → cross-reference with `terraform-hcl` units that may also define the same target.
- See [../cross_stack_bridges.md](../cross_stack_bridges.md).

## Bug-patterns row pointer

See [../bug_patterns.md](../bug_patterns.md) — rows where column
`aws-serverless` = `MUST-if-applicable`. Specifically: API Gateway
authorizer bypassed for a `OPTIONS` preflight route, Lambda timeout
shorter than downstream RDS query timeout (functional manifestation:
user sees 504), DLQ not configured for a critical async function (silent
data loss), Step Functions retry policy with `MaxAttempts: 0` on a
transient-failure-prone task, EventBridge rule with overly-broad pattern
firing the consumer on unintended events, idempotency token missing on
a Lambda triggered by SQS with retries.

## Empty-input branch

If a unit is detected as `aws-serverless` but contains no function / API
/ state machine resources (e.g. only IAM and S3 buckets), the unit is
recorded in `coverage.md` with skip reason `no-entry-points`. Dispatch
to `terraform-hcl.md` is preferred for pure-infrastructure CFN templates.
