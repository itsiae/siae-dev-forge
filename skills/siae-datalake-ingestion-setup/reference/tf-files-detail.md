# Contenuto File Terraform — modules/{dominio}/

Tutti i file vanno creati in `modules/{dominio}/` sostituendo `{dominio}` con il dominio target
e `{DOMINIO_UNDERSCORE}` con il dominio con trattini convertiti in underscore.

---

## _input.tf

```hcl
variable "account_id" { type = string }
variable "region"     { type = string }
variable "project"    { type = string }
variable "env"        { type = string }
variable "module"     { type = string }
variable "log_level"  { type = string }
variable "s3_endpoint_settings"  { type = map(any) }
variable "dms_instance_config"   { type = map(any) }
variable "vpc_stage"             { type = string }
variable "transient_bucket_name" { type = string }
variable "vpc_default_sg_id"     { type = string }
```

## _local.tf

```hcl
locals {
  prefix        = "${var.env}-${var.project}-${var.module}"
  global_suffix = "${var.region}-${var.account_id}"
}
locals {
  tasks_definition  = yamldecode(data.local_file.dms_task_definition.content)
}
locals {
  dms_tasks_by_name = { for task in local.tasks_definition.tasks : task.name => task }
  dms_task_names    = [for task in local.tasks_definition.tasks : task.name]
}
locals {
  dms_task_names_are_unique = length(local.dms_task_names) == length(distinct(local.dms_task_names))
}
```

## _data.tf

```hcl
data "local_file" "dms_task_definition" {
  filename = "${path.module}/dms-task-definitions.yaml"
}
```

## _output.tf

Vuoto — nessun output esposto.

## dms-endpoints.tf

```hcl
resource "aws_dms_endpoint" "{DOMINIO_UNDERSCORE}" {
  database_name                   = "{database-name}"
  endpoint_id                     = "${local.prefix}-source-parquet"
  endpoint_type                   = "source"
  engine_name                     = "postgres"
  secrets_manager_access_role_arn = data.aws_iam_role.dms_role.arn
  secrets_manager_arn             = aws_secretsmanager_secret.rds_credentials.arn
  ssl_mode                        = "require"
}

resource "aws_dms_s3_endpoint" "datalake_transient" {
  endpoint_id             = "${local.prefix}-s3-transient-target-parquet"
  endpoint_type           = "target"
  service_access_role_arn = data.aws_iam_role.dms_role.arn
  tags                    = { Name = "${local.prefix}-s3-transient-target-parquet" }
  bucket_name             = data.aws_s3_bucket.datalake_transient.id
  bucket_folder           = "transient/{DOMINIO_UNDERSCORE}/"

  add_column_name                = var.s3_endpoint_settings.add_column_name
  ssl_mode                       = var.s3_endpoint_settings.ssl_mode
  add_trailing_padding_character = var.s3_endpoint_settings.add_trailing_padding_character
  cdc_inserts_and_updates        = var.s3_endpoint_settings.cdc_inserts_and_updates
  cdc_min_file_size              = var.s3_endpoint_settings.cdc_min_file_size
  data_format                    = var.s3_endpoint_settings.data_format
  timestamp_column_name          = var.s3_endpoint_settings.timestamp_column_name
  glue_catalog_generation        = var.s3_endpoint_settings.glue_catalog_generation
  include_op_for_full_load       = var.s3_endpoint_settings.include_op_for_full_load
  cdc_max_batch_interval         = 300
}
```

## dms-instance.tf

```hcl
resource "aws_dms_replication_instance" "cdc_instance" {
  replication_instance_id      = "${local.prefix}-parquet-cdc-instance"
  auto_minor_version_upgrade   = true
  publicly_accessible          = false
  engine_version               = var.dms_instance_config.engine_version
  preferred_maintenance_window = var.dms_instance_config.preferred_maintenance_window
  multi_az                     = var.dms_instance_config.multi_az
  replication_instance_class   = var.dms_instance_config.instance_type
  allocated_storage            = var.dms_instance_config.allocated_storage
  replication_subnet_group_id  = data.aws_dms_replication_subnet_group.server.id
  apply_immediately            = var.env != "prod"

  vpc_security_group_ids = [data.aws_security_group.default_security_group.id]
  tags = { Name = "${local.prefix}-parquet-cdc", Role = "IngestionServer" }
}
```

## iam.tf

```hcl
data "aws_dms_replication_subnet_group" "server" {
  replication_subnet_group_id = "${var.env}-datalake-shared-server-subnet-group"
}
data "aws_iam_role" "dms_role" {
  name = "${var.env}-datalake-shared-dms-service-role"
}
```

## s3.tf

```hcl
data "aws_s3_bucket" "datalake_transient" {
  bucket = var.transient_bucket_name
}
```

## secrets-manager.tf

```hcl
resource "aws_secretsmanager_secret" "rds_credentials" {
  name        = "${var.env}-data-platform-parameters-{dominio}-enterprise-db-credentials"
  description = "Credentials for the {dominio} database"
  tags        = { Name = "${local.prefix}-secretsmanager-rds-credentials" }
}
```

## security-group.tf

```hcl
data "aws_security_group" "default_security_group" {
  id = var.vpc_default_sg_id
}
data "aws_security_group" "egress_everywhere" {
  tags = { "Name" = "${var.env}-data-platform-vpc-egress-everywhere" }
}
```

## vpc.tf

```hcl
data "aws_vpc" "platform_data" {
  filter { name = "tag:Name"; values = ["platform-data-${var.vpc_stage}-vpc"] }
}
data "aws_subnet" "data_a"   { filter { name = "tag:Name"; values = ["platform-data-${var.vpc_stage}-data-a"] } }
data "aws_subnet" "data_b"   { filter { name = "tag:Name"; values = ["platform-data-${var.vpc_stage}-data-b"] } }
data "aws_subnet" "data_c"   { filter { name = "tag:Name"; values = ["platform-data-${var.vpc_stage}-data-c"] } }
data "aws_subnet" "server_a" { filter { name = "tag:Name"; values = ["platform-data-${var.vpc_stage}-server-a"] } }
data "aws_subnet" "server_b" { filter { name = "tag:Name"; values = ["platform-data-${var.vpc_stage}-server-b"] } }
data "aws_subnet" "server_c" { filter { name = "tag:Name"; values = ["platform-data-${var.vpc_stage}-server-c"] } }
```

## dms-replication-task.tf

Copia identico dal repo di riferimento — contiene solo la `for_each` su `local.dms_tasks_by_name`
e le `replication_task_settings` con il logging dettagliato. Non contiene sostituzioni dominio-specifiche.
