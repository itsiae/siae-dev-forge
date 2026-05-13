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
