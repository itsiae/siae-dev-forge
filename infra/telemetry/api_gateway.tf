# --- REST API ---

resource "aws_api_gateway_rest_api" "devforge" {
  name        = "devforge-telemetry"
  description = "DevForge telemetry ingestion API"

  tags = {
    Project     = "siae-dev-forge"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# --- Resources: /logs (stage provides /v1 prefix) ---

resource "aws_api_gateway_resource" "logs" {
  rest_api_id = aws_api_gateway_rest_api.devforge.id
  parent_id   = aws_api_gateway_rest_api.devforge.root_resource_id
  path_part   = "logs"
}

# --- POST Method ---

resource "aws_api_gateway_method" "post_logs" {
  rest_api_id      = aws_api_gateway_rest_api.devforge.id
  resource_id      = aws_api_gateway_resource.logs.id
  http_method      = "POST"
  authorization    = "NONE"
  api_key_required = true
}

# --- Lambda Integration ---

resource "aws_api_gateway_integration" "lambda" {
  rest_api_id             = aws_api_gateway_rest_api.devforge.id
  resource_id             = aws_api_gateway_resource.logs.id
  http_method             = aws_api_gateway_method.post_logs.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.telemetry_ingest.invoke_arn
}

# --- Deployment & Stage ---

resource "aws_api_gateway_deployment" "devforge" {
  rest_api_id = aws_api_gateway_rest_api.devforge.id

  depends_on = [
    aws_api_gateway_integration.lambda,
  ]

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "v1" {
  rest_api_id   = aws_api_gateway_rest_api.devforge.id
  deployment_id = aws_api_gateway_deployment.devforge.id
  stage_name    = "v1"

  tags = {
    Project     = "siae-dev-forge"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# --- API Key & Usage Plan ---

resource "aws_api_gateway_api_key" "devforge" {
  name    = "devforge-telemetry-key"
  enabled = true

  tags = {
    Project     = "siae-dev-forge"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_api_gateway_usage_plan" "devforge" {
  name = "devforge-telemetry-plan"

  api_stages {
    api_id = aws_api_gateway_rest_api.devforge.id
    stage  = aws_api_gateway_stage.v1.stage_name
  }

  throttle_settings {
    rate_limit  = 100
    burst_limit = 10
  }

  tags = {
    Project     = "siae-dev-forge"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_api_gateway_usage_plan_key" "devforge" {
  key_id        = aws_api_gateway_api_key.devforge.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.devforge.id
}

# --- Lambda Permission for API Gateway ---

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.telemetry_ingest.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.devforge.execution_arn}/*/*"
}
