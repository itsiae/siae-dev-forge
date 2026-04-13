# DynamoDB table for event deduplication.
# Lambda ingest uses conditional PutItem on event_id to guarantee exactly-once
# delivery: if the item already exists, the event is skipped (already stored).
# TTL attribute auto-expires items after 7 days to keep the table small.
resource "aws_dynamodb_table" "event_dedup" {
  name         = "devforge-event-dedup"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "event_id"

  attribute {
    name = "event_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Project     = "siae-dev-forge"
    Environment = var.environment
    ManagedBy   = "terraform"
    Purpose     = "telemetry-event-dedup"
  }
}
