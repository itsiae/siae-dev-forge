# Stack: Terraform / HCL

## Stack id

`terraform-hcl`

## Manifest fingerprints

- File globs: `**/*.tf`, `**/*.tf.json`, `**/*.tfvars`, `**/*.tfvars.json`, `**/terragrunt.hcl`, `**/.terraform-version`, `**/.tflint.hcl`
- Content patterns: `terraform { required_providers { ... } }` block; `provider "aws" { ... }`; `module "x" { source = ... }`.
- Negative match: HCL files in `packer/` directories (Packer is out of scope in v1).

## Analysis-unit granularity

- **Terragrunt monorepo**: each directory containing `terragrunt.hcl` is one analysis unit.
- **Plain Terraform**: each directory containing one or more `.tf` files with a `terraform` block is one unit (a root module).
- **Module library** (`modules/<x>/`): each module is a unit but flagged as `library-only` (not directly applied); it contributes to dependency closure only.
- See [../repo_granularity.md](../repo_granularity.md).

## Parser

- Tree-sitter grammar: `tree-sitter-hcl`.
- Max AST depth: 5.
- JSON variants (`*.tf.json`) parsed as JSON.
- Terragrunt-specific functions (`find_in_parent_folders`, `read_terragrunt_config`) are recognized but not evaluated; their references are recorded as cross-unit boundaries.

## Entry-point kinds detected

For IaC, an "entry point" is a surface where a human operator triggers a
state change that has runtime functional consequences. The skill records:

| IaC surface | `entry_point.kind` | Detection signal |
|---|---|---|
| `terraform apply` against a root module | `iac-apply-surface` | The presence of `terraform { backend "<type>" { ... } }` in a directory marks it as a root module |
| Module instantiation (`module "x" { source = "..." }`) | NOT an entry point by itself | recorded as `downstream_calls[]` of the parent root module |
| Resource that creates a runtime endpoint (API Gateway, ALB listener, CloudFront distribution, Route53 record) | bridged to `http-route` via [../cross_stack_bridges.md](../cross_stack_bridges.md) | resource type matches a registered "endpoint-producing" type |
| Resource that creates an event source (EventBridge rule, SQS queue, SNS topic, Kafka topic via MSK) | bridged to `message-consumer` source | resource type matches a registered "queue / topic / rule" type |
| Resource that creates a scheduled trigger (EventBridge schedule, CloudWatch event with `schedule_expression`) | bridged to `scheduled-job` source | resource attributes match the schedule pattern |
| IAM policy that grants runtime auth | functional auth gate | `aws_iam_policy_document` / `aws_iam_role_policy` blocks |

## Inputs typing

- IaC inputs are `variable "x" { type = ... default = ... validation { ... } }` blocks; the `type` is the input type, the `validation` block is the constraint hint.
- Workspace-bound vars (`*.tfvars` files) are recorded but their values are NOT inlined into the entry-point record (the bug pattern is the absence of validation, not the value).
- `data` blocks are NOT inputs; they are external state references.

## Side-effect detection

- Every `resource` block IS a side effect by definition (it creates / updates / destroys infrastructure).
- The runtime classifies side effects by resource type:
  - persistence-creating: `aws_dynamodb_table`, `aws_rds_cluster`, `aws_s3_bucket`, etc.
  - endpoint-creating: `aws_apigatewayv2_api`, `aws_lb_listener`, `aws_cloudfront_distribution`.
  - auth-affecting: `aws_iam_*`, `aws_cognito_*`, `aws_kms_key`.
  - message-creating: `aws_sqs_queue`, `aws_sns_topic`, `aws_eventbridge_rule`, `aws_msk_cluster`.
- `lifecycle { prevent_destroy = true }` is recorded as a safety hint.

## Cross-stack bridge hints

- `aws_lambda_function.function_name` → `aws-serverless` Lambda lookup.
- `aws_apigatewayv2_route.route_key` literal (e.g. `"POST /v1/users"`) → `http-route` resolution against any unit that hosts that path.
- `aws_iam_policy_document.statement.actions` → cross-reference with `data-platform` jobs that need those actions.
- `aws_sqs_queue.name` → message-consumer in the application layer (Java / Python / TS).
- See [../cross_stack_bridges.md](../cross_stack_bridges.md).

## Bug-patterns row pointer

See [../bug_patterns.md](../bug_patterns.md) — rows where column
`terraform-hcl` = `MUST-if-applicable`. Specifically: IAM wildcard
policies passing functional manifestation test (privilege escalation
that affects a real user journey), `prevent_destroy = false` on
production-critical resources, missing `lifecycle` ignore-changes on
auto-managed attributes causing drift, `count` / `for_each` with a
dynamic value re-creating resources on every apply, `aws_security_group`
egress / ingress rules that block a documented user journey, KMS key
rotation disabled on a key that protects user-visible data.

## Empty-input branch

If a unit is detected as `terraform-hcl` but contains no `terraform {}`
block (i.e. it is a module library, not a root module), the unit is
recorded in `coverage.md` with skip reason `library-only` (a custom
reason in addition to the closed enum, prefixed with `iac:`). The unit
still contributes to `dependency_closure.md` when other root modules
declare `source = "..."` pointing here.
