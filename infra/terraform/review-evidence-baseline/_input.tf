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
  default = {
    Project     = "review-evidence"
    Environment = "prod"
    Owner       = "DevForge"
    ManagedBy   = "Terraform"
  }
}
