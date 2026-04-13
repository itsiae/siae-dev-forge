data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/handler.py"
  output_path = "${path.module}/lambda/handler.zip"
}

resource "aws_lambda_function" "telemetry_ingest" {
  function_name    = "devforge-telemetry-ingest"
  description      = "Ingest DevForge JSONL telemetry with dedup (DynamoDB) and DLQ (SQS)"
  handler          = "handler.handler"
  runtime          = "python3.12"
  # PR-B: memory 128->256MB per supportare payload 5MB + DynamoDB ops
  memory_size      = 256
  # PR-B: timeout 10->30s per cold starts S3 PUT + DynamoDB check-and-set
  timeout          = 30
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  role             = aws_iam_role.lambda_telemetry.arn

  # NO dead_letter_config: API Gateway invoca sync, dead_letter_config ignorata.
  # DLQ e' APPLICATIVO (handler.py fa sqs.send_message in caso di errore).

  environment {
    variables = {
      BUCKET_NAME   = aws_s3_bucket.telemetry.id
      DEDUP_TABLE   = aws_dynamodb_table.event_dedup.name
      DLQ_QUEUE_URL = aws_sqs_queue.telemetry_dlq.url
    }
  }

  tags = {
    Project     = "siae-dev-forge"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# --- IAM Role ---

resource "aws_iam_role" "lambda_telemetry" {
  name = "devforge-telemetry-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = {
    Project     = "siae-dev-forge"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role_policy" "lambda_s3_put" {
  name = "devforge-telemetry-s3-put"
  role = aws_iam_role.lambda_telemetry.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "s3:PutObject"
      Resource = "${aws_s3_bucket.telemetry.arn}/devforge-logs/*"
    }]
  })
}

# PR-B: DynamoDB dedup policy.
# Lambda fa PutItem con ConditionExpression (check-and-set) per exactly-once.
# GetItem per eventuale look-ahead (non usato oggi, ma safe da includere).
resource "aws_iam_role_policy" "lambda_dynamodb_dedup" {
  name = "devforge-telemetry-dynamodb-dedup"
  role = aws_iam_role.lambda_telemetry.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:PutItem", "dynamodb:GetItem"]
      Resource = aws_dynamodb_table.event_dedup.arn
    }]
  })
}

# PR-B: SQS DLQ send policy (applicative DLQ).
# Lambda fa send_message quando non riesce a scrivere su S3 o DynamoDB.
resource "aws_iam_role_policy" "lambda_sqs_dlq_send" {
  name = "devforge-telemetry-sqs-dlq-send"
  role = aws_iam_role.lambda_telemetry.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "sqs:SendMessage"
      Resource = aws_sqs_queue.telemetry_dlq.arn
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_telemetry.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
