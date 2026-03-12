terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region  = "eu-west-1"
  profile = "siae-data-devqa"

  default_tags {
    tags = {
      Project     = "siae-dev-forge"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
