# review-evidence-baseline

Provisioning S3 bucket + IAM OIDC role per Review Evidence v2 baseline cache.

## Usage

```bash
cd infra/terraform/review-evidence-baseline
terraform init
terraform plan
terraform apply
```

## Outputs

- `bucket_arn` — usa in env `DEVFORGE_BASELINE_S3_BUCKET`
- `github_actions_role_arn` — configure in GitHub repo secret `AWS_ROLE_ARN`
