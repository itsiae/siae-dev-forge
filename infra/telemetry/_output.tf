output "bucket_name" {
  description = "Name of the telemetry S3 bucket"
  value       = aws_s3_bucket.telemetry.id
}

output "bucket_arn" {
  description = "ARN of the telemetry S3 bucket"
  value       = aws_s3_bucket.telemetry.arn
}

output "api_url" {
  description = "Full URL for the telemetry logs endpoint"
  value       = "${aws_api_gateway_stage.v1.invoke_url}/logs"
}

output "api_key" {
  description = "API key for authenticating telemetry uploads"
  value       = aws_api_gateway_api_key.devforge.value
  sensitive   = true
}
