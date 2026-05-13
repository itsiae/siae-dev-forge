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
