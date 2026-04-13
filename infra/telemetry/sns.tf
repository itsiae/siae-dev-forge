# SNS topic for DevForge telemetry alerts (DLQ non-empty, silent users report, etc).
resource "aws_sns_topic" "alerts" {
  name = "devforge-telemetry-alerts"

  tags = {
    Project     = "siae-dev-forge"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Email subscription for the primary owner.
# Owner must confirm via email link before notifications arrive.
resource "aws_sns_topic_subscription" "alerts_owner_email" {
  count     = var.primary_owner_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.primary_owner_email
}
