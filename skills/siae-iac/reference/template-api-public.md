# Modulo API Public — API Gateway EDGE

Responsabilita': API Gateway REST pubblico con CDN CloudFront.

## File Structure

```text
modules/api-public/
├── _input.tf       # standard + create_shared_resources, xray_enabled
├── _local.tf       # prefix, account_level_prefix
├── api-gateway.tf  # REST API (EDGE), /health mock
└── api-deploy.tf   # Deployment, Stage, method settings (burst=100, rate=50)
```

## Dependency

`dependency "vpc"` (opzionale, per mock_outputs).

## Differenze da api-private

| Aspetto     | api-private        | api-public        |
|-------------|--------------------|--------------------|
| Endpoint    | PRIVATE            | EDGE (CloudFront) |
| Route53     | Si (CNAME)         | No                |
| VPC Policy  | Si (Endpoint only) | No                |
| burst_limit | 10000              | 100               |
| rate_limit  | 100                | 50                |
