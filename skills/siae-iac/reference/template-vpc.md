# Modulo VPC — Data Lookup

Responsabilita': Lookup risorse VPC enterprise pre-esistenti (NON crea VPC).

## File Structure

```text
modules/vpc/
├── _input.tf      # account_id, region, project, env, vpc_stage, module, config
├── _local.tf      # prefix, global_suffix
├── _output.tf     # vpc_enterprise, data_subnets, server_subnets, aws_vpc_endpoint_api_gateway
├── vpc.tf         # Data source VPC + subnet (a/b/c per data e server)
├── endpoints.tf   # VPC endpoint API Gateway lookup
└── sg.tf          # Security group lookups
```

## Pattern Data Source

Lookup by tag Name: `platform-enterprise-${var.vpc_stage}-vpc`
Subnet naming: `${vpc_name}-data-${az}` e `${vpc_name}-server-${az}`

## Dependency

Root module — nessuna dipendenza. Gli altri moduli dipendono da questo.

## Output esposti

| Output                         | Tipo         | Descrizione                  |
|--------------------------------|--------------|------------------------------|
| `vpc_enterprise`               | object       | VPC data source completo     |
| `data_subnets`                 | list(object) | Subnet data [a, b, c]       |
| `server_subnets`               | list(object) | Subnet server [a, b, c]     |
| `aws_vpc_endpoint_api_gateway` | object {id}  | VPC Endpoint per api-private |
