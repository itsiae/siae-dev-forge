# SQS Dead Letter Queue for the ingest Lambda — APPLICATIVE DLQ.
# Lambda's native dead_letter_config is ignored for sync invocations
# (API Gateway invokes sync), so the handler writes to SQS explicitly
# when it cannot store the payload on S3 (e.g. S3 throttling, DynamoDB outage).
resource "aws_sqs_queue" "telemetry_dlq" {
  name                      = "devforge-telemetry-dlq"
  message_retention_seconds = 1209600  # 14 days
  visibility_timeout_seconds = 60
  receive_wait_time_seconds  = 20       # long polling

  tags = {
    Project     = "siae-dev-forge"
    Environment = var.environment
    ManagedBy   = "terraform"
    Purpose     = "telemetry-dlq-applicative"
  }
}

# Alarm when DLQ is not empty — indicates ingest Lambda is failing.
# Actions wired to SNS alerts topic (see sns.tf).
resource "aws_cloudwatch_metric_alarm" "dlq_not_empty" {
  alarm_name          = "devforge-telemetry-dlq-not-empty"
  alarm_description   = "Messages present in DevForge telemetry DLQ — ingest Lambda likely failing"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    QueueName = aws_sqs_queue.telemetry_dlq.name
  }

  tags = {
    Project     = "siae-dev-forge"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
