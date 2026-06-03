# Functional bug report

- **Run id**: example-terraform
- **Scope hash**: 7d2a91f4
- **Skill semver**: 1.0.0
- **Model id**: claude-opus-4-7
- **Mode**: interactive
- **Confidence (global)**: high
- **Findings**: 1 SEV-1 · 1 SEV-2 · 0 SEV-3 · 0 SEV-4
- **Lang**: en

## Index

| Finding | Journey | Severity | Title | Entry point |
|---|---|---|---|---|
| F-0001 | J-001 | SEV-1 | Health endpoint becomes unreachable after security-group apply | terragrunt:envs/prod/vpc-sg |
| F-0002 | J-002 | SEV-2 | Lambda role grants wildcard DynamoDB write to user-facing table | terragrunt:envs/prod/iam-roles |

## Journey J-001 — Health probe traffic

### F-0001 — Health endpoint becomes unreachable after security-group apply

- **Severity**: SEV-1 (rubric row R-SEV1-04)
- **Pattern**: BP-018
- **Entry point**: terragrunt:envs/prod/vpc-sg
- **Confidence**: high

**Preconditions**

- The pull request modifies `aws_security_group_rule.api_ingress` and
  removes port 443 ingress from the SG attached to the ALB.
- The documented health-probe endpoint is https://api.example.com/v1/health on port 443.

**Steps**

1. (iac-operator) Run `terraform apply` against module "envs/prod/vpc-sg" with var `environment=prod`
2. (api-caller) Send HTTP GET https://api.example.com/v1/health
3. (observer) Inspect the response status and report whether the request times out or returns

**Expected result**

The request returns `200 OK` within 1 second with body `{"status":"ok"}`.

**Actual result**

The request times out after 30 seconds with no TCP handshake completion.

**Evidence**

- `envs/prod/vpc-sg/main.tf:42-56` @ `f0c12ab` (excerpt)
  > resource "aws_security_group_rule" "api_ingress" {
- `envs/prod/vpc-sg/main.tf:48-52` @ `f0c12ab` (excerpt)
  > from_port = 0
- `docs/runbooks/health.md:11-14` @ `f0c12ab` (excerpt)
  > Health probe targets port 443 on the public ALB.

**Suggested fix direction**

Restore the explicit port-443 ingress rule, or migrate the runbook to
the new port and validate end-to-end before merging the IaC change.

**Reproduction rate target**

`>=95%`

**Boundary observations**

- terragrunt:envs/prod/vpc-sg → bucket-key `aws-loadbalancer-controller` → terragrunt:envs/prod/ingress

## Journey J-002 — Order management

### F-0002 — Lambda role grants wildcard DynamoDB write to user-facing table

- **Severity**: SEV-2 (rubric row R-SEV2-02)
- **Pattern**: BP-002
- **Entry point**: terragrunt:envs/prod/iam-roles
- **Confidence**: high

**Preconditions**

- The Lambda `order-processor` is invoked by API Gateway path `POST /v1/orders`.
- The attached role grants `dynamodb:PutItem` with `Resource = "*"`.
- A tenant-scoped condition on the role is documented but not enforced.

**Steps**

1. (iac-operator) Run `terraform apply` against module "envs/prod/iam-roles"
2. (api-caller) Send HTTP POST /v1/orders with body `{"tenant_id":"tenant-B","amount":100}` using a session token issued to tenant-A
3. (observer) Open the table "orders" on database "siae-orders-prod" and report the row that has tenant_id="tenant-B" inserted in the last minute

**Expected result**

The response is `403 Forbidden`; no row is inserted in "orders" for `tenant_id=tenant-B`.

**Actual result**

The response is `201 Created`; a row exists in "orders" with `tenant_id=tenant-B` although the caller is tenant-A.

**Evidence**

- `envs/prod/iam-roles/main.tf:18-30` @ `f0c12ab` (excerpt)
  > resource "aws_iam_role_policy" "order_processor" {
- `envs/prod/iam-roles/main.tf:35-44` @ `f0c12ab` (excerpt)
  > Action = ["dynamodb:PutItem"]
- `lambda/order_processor/handler.py:55-62` @ `f0c12ab` (excerpt)
  > table.put_item(Item={"tenant_id": body["tenant_id"], ...})

**Suggested fix direction**

Tighten the IAM policy to scope `Resource` to the specific table ARN
and add a `dynamodb:LeadingKeys` condition pinned to the caller's
tenant id; enforce the same check in the Lambda handler.

**Reproduction rate target**

`>=95%`

**Boundary observations**

- terragrunt:envs/prod/iam-roles → iam-role-arn `order-processor-role` → aws-serverless:envs/prod/order-processor
