# Task 16 — Terraform module: S3 bucket + IAM OIDC

**SP:** 0.5 · **AC mappati:** AC #17, CRITICAL D3+D5 · **Dipendenze:** nessuna (parallel a PR-A o pre-PR-B) · **Wave:** 0

## Goal

Modulo Terraform `infra/terraform/review-evidence-baseline/` che provisiona:
1. **S3 bucket** `itsiae-review-evidence-baseline-prod` (eu-west-1) con lifecycle
2. **IAM OIDC role** trust policy `itsiae/*` per GitHub Actions read+write

CRITICAL D3+D5: baseline cache server-side, no client trust.

## File coinvolti

**Creare:**
- `infra/terraform/review-evidence-baseline/_input.tf`
- `infra/terraform/review-evidence-baseline/_local.tf`
- `infra/terraform/review-evidence-baseline/_output.tf`
- `infra/terraform/review-evidence-baseline/main.tf`
- `infra/terraform/review-evidence-baseline/README.md`
- `tests/test_terraform_review_evidence_baseline.sh` (terraform validate test)

## Step

### Step 1 — `_input.tf` (variables)

```hcl
variable "bucket_name" {
  description = "S3 bucket name for baseline cache"
  type        = string
  default     = "itsiae-review-evidence-baseline-prod"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "github_org" {
  description = "GitHub org allowed by OIDC trust"
  type        = string
  default     = "itsiae"
}

variable "lifecycle_transition_days" {
  description = "Days before GLACIER transition"
  type        = number
  default     = 30
}

variable "lifecycle_expiration_days" {
  description = "Days before deletion (LRU evict)"
  type        = number
  default     = 90
}

variable "common_tags" {
  description = "Common tags"
  type        = map(string)
  default     = {
    Project     = "review-evidence"
    Environment = "prod"
    Owner       = "DevForge"
    ManagedBy   = "Terraform"
  }
}
```

### Step 2 — `_local.tf`

```hcl
locals {
  oidc_provider_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
  oidc_subject      = "repo:${var.github_org}/*:*"
}

data "aws_caller_identity" "current" {}
```

### Step 3 — `main.tf`

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# S3 bucket
resource "aws_s3_bucket" "baseline" {
  bucket = var.bucket_name
  tags   = var.common_tags
}

resource "aws_s3_bucket_versioning" "baseline" {
  bucket = aws_s3_bucket.baseline.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "baseline" {
  bucket = aws_s3_bucket.baseline.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "baseline" {
  bucket                  = aws_s3_bucket.baseline.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "baseline" {
  bucket = aws_s3_bucket.baseline.id
  rule {
    id     = "evict-old-baselines"
    status = "Enabled"
    transition {
      days          = var.lifecycle_transition_days
      storage_class = "GLACIER"
    }
    expiration {
      days = var.lifecycle_expiration_days
    }
  }
}

# IAM OIDC role for GitHub Actions
data "aws_iam_policy_document" "trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [local.oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [local.oidc_subject]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  name               = "review-evidence-baseline-github-actions"
  assume_role_policy = data.aws_iam_policy_document.trust.json
  tags               = var.common_tags
}

data "aws_iam_policy_document" "s3_rw" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.baseline.arn,
      "${aws_s3_bucket.baseline.arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "s3_rw" {
  name   = "s3-rw"
  role   = aws_iam_role.github_actions.id
  policy = data.aws_iam_policy_document.s3_rw.json
}
```

### Step 4 — `_output.tf`

```hcl
output "bucket_arn" {
  description = "ARN of baseline bucket"
  value       = aws_s3_bucket.baseline.arn
}

output "bucket_name" {
  description = "Name of baseline bucket"
  value       = aws_s3_bucket.baseline.id
}

output "github_actions_role_arn" {
  description = "IAM role ARN for GitHub Actions OIDC"
  value       = aws_iam_role.github_actions.arn
}
```

### Step 5 — README

`infra/terraform/review-evidence-baseline/README.md`:

```markdown
# review-evidence-baseline

Provisioning S3 bucket + IAM OIDC role per Review Evidence v2 baseline cache.

## Usage

```bash
cd infra/terraform/review-evidence-baseline
terraform init
terraform plan
terraform apply
```

## Outputs

- `bucket_arn` — usa in env `DEVFORGE_BASELINE_S3_BUCKET`
- `github_actions_role_arn` — configure in GitHub repo secret `AWS_ROLE_ARN`
```

### Step 6 — Test

`tests/test_terraform_review_evidence_baseline.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

TF_DIR="infra/terraform/review-evidence-baseline"

if ! command -v terraform >/dev/null 2>&1; then
    echo "SKIP: terraform not installed"
    exit 0
fi

cd "$(git rev-parse --show-toplevel)/${TF_DIR}"

terraform init -backend=false -input=false
terraform validate
terraform fmt -check

echo "PASS: terraform module valid"
```

### Step 7 — Commit

```bash
chmod +x tests/test_terraform_review_evidence_baseline.sh
bash tests/test_terraform_review_evidence_baseline.sh
# PASS: terraform module valid (or SKIP if terraform missing)

git add infra/terraform/review-evidence-baseline/ \
        tests/test_terraform_review_evidence_baseline.sh
git commit -m "feat(review-evidence-v2): Terraform module S3 + IAM OIDC (#task-16)"
```

## Criteri di accettazione

- [ ] **CRITICAL D3+D5:** S3 bucket + IAM OIDC role provisionati via Terraform
- [ ] Bucket name `itsiae-review-evidence-baseline-prod`, region `eu-west-1`
- [ ] Lifecycle: 30d → GLACIER, 90d → expiration (LRU evict, edge D1 fix)
- [ ] Public access fully blocked
- [ ] Server-side encryption AES256
- [ ] OIDC trust policy limited a `repo:itsiae/*`
- [ ] IAM policy least-privilege: GetObject + PutObject + ListBucket su bucket only
- [ ] `terraform validate` + `terraform fmt -check` PASS
- [ ] 1 integration test (bash script) PASS
- [ ] README.md per modulo
