variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "bucket_name" {
  description = "Name of the S3 bucket for DevForge telemetry logs"
  type        = string
  default     = "siae-devforge-telemetry"
}
