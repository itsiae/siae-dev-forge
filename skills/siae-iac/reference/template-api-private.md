# Modulo API Private — API Gateway PRIVATE

Responsabilita': API Gateway REST privato, accessibile solo via VPC Endpoint.

## File Structure

```text
modules/api-private/
├── _input.tf           # standard + create_shared_resources, xray_enabled,
│                       #   aws_vpc_endpoint_api_gateway, siae_route53_zone_name
├── _local.tf           # prefix, account_level_prefix
├── api-gateway.tf      # REST API (PRIVATE), /health mock, resource policy (VPC Endpoint only)
├── api-deploy.tf       # Deployment, Stage, method settings (burst=10000, rate=100)
└── route53-record.tf   # CNAME: {module}.{project}.{env}.aws.siae
```

## Dependency

`dependency "vpc"` → `aws_vpc_endpoint_api_gateway`

## IAM

Role CloudWatch: `${account_level_prefix}-apigw-private-service-role`
Creato solo se `create_shared_resources = true` (una volta per account).

## Throttling

| Parametro   | Valore |
|-------------|--------|
| burst_limit | 10000  |
| rate_limit  | 100    |

Logging: ERROR in prod, INFO altrimenti.
