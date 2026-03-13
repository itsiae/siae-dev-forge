# Cloud Custodian — Policy Library SIAE

> Reference per `siae-finops` skill. 8 policy pronte per c7n/c7n-org multi-account.

---

## 1. Setup c7n + c7n-org

### Installazione

```bash
# Installa Cloud Custodian e il modulo multi-account
pip install c7n c7n-org

# Verifica
custodian version
# Output atteso: 0.9.x

c7n-org version
# Output atteso: 0.6.x
```

### Struttura Directory

```
c7n-org/
├── accounts.yml              # Account AWS + IAM role
├── policies/
│   ├── cost/
│   │   ├── tag-enforcement.yml
│   │   ├── unused-lambda.yml
│   │   ├── idle-dynamodb.yml
│   │   ├── detached-ebs.yml
│   │   ├── old-snapshots.yml
│   │   ├── off-hours-dev.yml
│   │   ├── oversized-rds.yml
│   │   └── glue-runaway.yml
│   └── tags/
│       └── tag-enforcement.yml   # Alias/symlink a cost/
└── Makefile                      # dry-run / apply per ambiente
```

### accounts.yml Template (Multi-Account)

```yaml
# c7n-org accounts configuration
# Ogni account AWS gestito da SIAE
accounts:
  - name: siae-sviluppo
    account_id: "111111111111"
    role: arn:aws:iam::111111111111:role/CloudCustodianRole
    regions:
      - eu-west-1
      - eu-central-1
    tags:
      environment: sviluppo

  - name: siae-collaudo
    account_id: "222222222222"
    role: arn:aws:iam::222222222222:role/CloudCustodianRole
    regions:
      - eu-west-1
      - eu-central-1
    tags:
      environment: collaudo

  - name: siae-certificazione
    account_id: "333333333333"
    role: arn:aws:iam::333333333333:role/CloudCustodianRole
    regions:
      - eu-west-1
      - eu-central-1
    tags:
      environment: certificazione

  - name: siae-produzione
    account_id: "444444444444"
    role: arn:aws:iam::444444444444:role/CloudCustodianRole
    regions:
      - eu-west-1
      - eu-central-1
    tags:
      environment: produzione
```

### IAM Role Template (Trust Policy per Cross-Account)

Creare questo ruolo in **ogni** account AWS target:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::555555555555:role/CloudCustodianOrchestrator"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "siae-c7n-2026"
        }
      }
    }
  ]
}
```

> `555555555555` = account centrale dove gira c7n-org (tipicamente l'account DevOps/tooling).

**Policy IAM minima per il ruolo `CloudCustodianRole`:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CustodianReadOnly",
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "rds:Describe*",
        "dynamodb:Describe*",
        "dynamodb:ListTables",
        "lambda:List*",
        "lambda:GetFunction",
        "ecs:Describe*",
        "ecs:List*",
        "glue:GetJob*",
        "glue:GetJobRun*",
        "glue:BatchGetJobs",
        "tag:GetResources",
        "tag:GetTagKeys",
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:GetMetricData",
        "sns:Publish"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CustodianTagWrite",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateTags",
        "rds:AddTagsToResource",
        "dynamodb:TagResource",
        "lambda:TagResource",
        "ecs:TagResource"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CustodianEnforceActions",
      "Effect": "Allow",
      "Action": [
        "ec2:DeleteVolume",
        "ec2:DeleteSnapshot",
        "rds:StopDBInstance",
        "ecs:UpdateService"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/ManagedBy": "Terraform"
        }
      }
    }
  ]
}
```

### SNS Topic per Notifiche

```bash
# Crea il topic SNS in ogni account (o nel centrale con policy cross-account)
aws sns create-topic --name siae-finops-alerts --region eu-west-1

# Sottoscrivi il canale (email, Slack webhook, etc.)
aws sns subscribe \
  --topic-arn arn:aws:sns:eu-west-1:555555555555:siae-finops-alerts \
  --protocol email \
  --notification-endpoint finops@siae.it
```

---

## 2. Policy 1: tag-enforcement

Filtra risorse AWS senza i 6 tag obbligatori SIAE. Auto-tagga `ManagedBy=Terraform` se mancante, notifica per gli altri.

### YAML

```yaml
policies:
  - name: tag-enforcement
    description: |
      Enforce i 6 tag obbligatori SIAE su tutte le risorse.
      Tag richiesti: Environment, Project, ManagedBy, Team, CostCenter, Repository.
      Azione: notifica via SNS + auto-tag ManagedBy=Terraform se mancante.
    resource: aws.ec2
    comment: >
      Applicare anche a aws.rds, aws.dynamodb-table, aws.lambda,
      aws.ecs-service, aws.s3 duplicando la policy con resource diverso.
    filters:
      - or:
          - "tag:Environment": absent
          - "tag:Project": absent
          - "tag:ManagedBy": absent
          - "tag:Team": absent
          - "tag:CostCenter": absent
          - "tag:Repository": absent
    actions:
      - type: notify
        template: default.html
        priority_header: "2"
        subject: "[SIAE FinOps] Risorse con tag obbligatori mancanti - {account}"
        violation_desc: >
          Le seguenti risorse non hanno tutti i 6 tag obbligatori SIAE
          (Environment, Project, ManagedBy, Team, CostCenter, Repository).
        action_desc: >
          Aggiungere i tag mancanti tramite Terraform/Terragrunt.
          Vedi tagging-strategy.md per i valori ammessi.
        to:
          - "resource-owner"
        transport:
          type: sns
          topic: arn:aws:sns:eu-west-1:{account_id}:siae-finops-alerts
      - type: tag
        key: ManagedBy
        value: Terraform
        condition:
          type: value
          key: "tag:ManagedBy"
          value: absent

  # Ripetere per ogni tipo di risorsa:
  - name: tag-enforcement-rds
    description: "Tag enforcement per RDS instances"
    resource: aws.rds
    filters:
      - or:
          - "tag:Environment": absent
          - "tag:Project": absent
          - "tag:ManagedBy": absent
          - "tag:Team": absent
          - "tag:CostCenter": absent
          - "tag:Repository": absent
    actions:
      - type: notify
        template: default.html
        priority_header: "2"
        subject: "[SIAE FinOps] RDS con tag mancanti - {account}"
        violation_desc: "RDS instances senza tag obbligatori SIAE"
        action_desc: "Aggiungere i tag mancanti via Terraform"
        to:
          - "resource-owner"
        transport:
          type: sns
          topic: arn:aws:sns:eu-west-1:{account_id}:siae-finops-alerts
      - type: tag
        key: ManagedBy
        value: Terraform
        condition:
          type: value
          key: "tag:ManagedBy"
          value: absent

  - name: tag-enforcement-lambda
    description: "Tag enforcement per Lambda functions"
    resource: aws.lambda
    filters:
      - or:
          - "tag:Environment": absent
          - "tag:Project": absent
          - "tag:ManagedBy": absent
          - "tag:Team": absent
          - "tag:CostCenter": absent
          - "tag:Repository": absent
    actions:
      - type: notify
        template: default.html
        priority_header: "2"
        subject: "[SIAE FinOps] Lambda con tag mancanti - {account}"
        violation_desc: "Lambda functions senza tag obbligatori SIAE"
        action_desc: "Aggiungere i tag mancanti via Terraform"
        to:
          - "resource-owner"
        transport:
          type: sns
          topic: arn:aws:sns:eu-west-1:{account_id}:siae-finops-alerts
      - type: tag
        key: ManagedBy
        value: Terraform
        condition:
          type: value
          key: "tag:ManagedBy"
          value: absent

  - name: tag-enforcement-dynamodb
    description: "Tag enforcement per DynamoDB tables"
    resource: aws.dynamodb-table
    filters:
      - or:
          - "tag:Environment": absent
          - "tag:Project": absent
          - "tag:ManagedBy": absent
          - "tag:Team": absent
          - "tag:CostCenter": absent
          - "tag:Repository": absent
    actions:
      - type: notify
        template: default.html
        priority_header: "2"
        subject: "[SIAE FinOps] DynamoDB con tag mancanti - {account}"
        violation_desc: "DynamoDB tables senza tag obbligatori SIAE"
        action_desc: "Aggiungere i tag mancanti via Terraform"
        to:
          - "resource-owner"
        transport:
          type: sns
          topic: arn:aws:sns:eu-west-1:{account_id}:siae-finops-alerts
      - type: tag
        key: ManagedBy
        value: Terraform
        condition:
          type: value
          key: "tag:ManagedBy"
          value: absent

  - name: tag-enforcement-s3
    description: "Tag enforcement per S3 buckets"
    resource: aws.s3
    filters:
      - or:
          - "tag:Environment": absent
          - "tag:Project": absent
          - "tag:ManagedBy": absent
          - "tag:Team": absent
          - "tag:CostCenter": absent
          - "tag:Repository": absent
    actions:
      - type: notify
        template: default.html
        priority_header: "2"
        subject: "[SIAE FinOps] S3 con tag mancanti - {account}"
        violation_desc: "S3 buckets senza tag obbligatori SIAE"
        action_desc: "Aggiungere i tag mancanti via Terraform"
        to:
          - "resource-owner"
        transport:
          type: sns
          topic: arn:aws:sns:eu-west-1:{account_id}:siae-finops-alerts
      - type: tag
        key: ManagedBy
        value: Terraform
        condition:
          type: value
          key: "tag:ManagedBy"
          value: absent
```

### Esempio Output Dry-Run

```bash
$ custodian run -s /tmp/c7n-output --dry-run policies/cost/tag-enforcement.yml

2026-03-13 10:15:23 custodian.policy:INFO policy:tag-enforcement resource:aws.ec2 count:23
2026-03-13 10:15:23 custodian.policy:INFO policy:tag-enforcement-rds resource:aws.rds count:5
2026-03-13 10:15:24 custodian.policy:INFO policy:tag-enforcement-lambda resource:aws.lambda count:41
2026-03-13 10:15:24 custodian.policy:INFO policy:tag-enforcement-dynamodb resource:aws.dynamodb-table count:12
2026-03-13 10:15:24 custodian.policy:INFO policy:tag-enforcement-s3 resource:aws.s3 count:8
```

Output JSON in `/tmp/c7n-output/tag-enforcement/resources.json`:

```json
[
  {
    "InstanceId": "i-0abc123def456789",
    "InstanceType": "t3.medium",
    "Tags": [
      {"Key": "Environment", "Value": "sviluppo"},
      {"Key": "Project", "Value": "diritti"}
    ],
    "c7n:MatchedFilters": ["tag:ManagedBy", "tag:Team", "tag:CostCenter", "tag:Repository"]
  }
]
```

> **Lettura:** 23 istanze EC2 non hanno tutti i 6 tag. Il campo `c7n:MatchedFilters` indica quali tag mancano.

---

## 3. Policy 2: unused-lambda

Lambda functions non modificate da oltre 90 giorni. Candidati per dismissione o review.

### YAML

```yaml
policies:
  - name: unused-lambda
    description: |
      Identifica Lambda functions non modificate da oltre 90 giorni.
      Indicatore di funzioni potenzialmente inutilizzate o abbandonate.
      Azione: notifica al team owner per review.
    resource: aws.lambda
    filters:
      - type: value
        key: LastModified
        value_type: age
        op: greater-than
        value: 90
    actions:
      - type: notify
        template: default.html
        priority_header: "3"
        subject: "[SIAE FinOps] Lambda inutilizzate >90 giorni - {account}"
        violation_desc: >
          Le seguenti Lambda functions non sono state modificate da oltre 90 giorni.
          Potrebbero essere inutilizzate e generare costi (allocazione, CloudWatch Logs).
        action_desc: >
          Verificare se la funzione e' ancora necessaria. Se non piu' usata,
          rimuoverla dal codice Terraform e fare PR. Se necessaria, aggiornare il
          timestamp con un deploy o documentare il motivo della retention.
        to:
          - "resource-owner"
        transport:
          type: sns
          topic: arn:aws:sns:eu-west-1:{account_id}:siae-finops-alerts
```

### Esempio Output Dry-Run

```bash
$ custodian run -s /tmp/c7n-output --dry-run policies/cost/unused-lambda.yml

2026-03-13 10:16:01 custodian.policy:INFO policy:unused-lambda resource:aws.lambda count:17
```

Output JSON in `/tmp/c7n-output/unused-lambda/resources.json`:

```json
[
  {
    "FunctionName": "diritti-legacy-notifier",
    "FunctionArn": "arn:aws:lambda:eu-west-1:111111111111:function:diritti-legacy-notifier",
    "Runtime": "python3.8",
    "LastModified": "2025-11-15T14:30:00.000+0000",
    "MemorySize": 256,
    "Timeout": 30,
    "Tags": {
      "Environment": "sviluppo",
      "Project": "diritti"
    }
  }
]
```

> **Lettura:** 17 Lambda non modificate da >90 giorni. `diritti-legacy-notifier` usa Python 3.8 (EOL) e non viene toccata da 4 mesi.

---

## 4. Policy 3: idle-dynamodb

DynamoDB tables con consumo di lettura quasi nullo per 14 giorni. Candidati per dismissione o passaggio a on-demand.

### YAML

```yaml
policies:
  - name: idle-dynamodb
    description: |
      Identifica DynamoDB tables con ConsumedReadCapacityUnits < 10 (Sum)
      negli ultimi 14 giorni. Tabelle potenzialmente inutilizzate che generano
      costi di provisioned capacity.
    resource: aws.dynamodb-table
    filters:
      - type: metrics
        name: ConsumedReadCapacityUnits
        statistics: Sum
        period: 86400
        days: 14
        value: 10
        op: less-than
    actions:
      - type: notify
        template: default.html
        priority_header: "3"
        subject: "[SIAE FinOps] DynamoDB idle (<10 RCU in 14gg) - {account}"
        violation_desc: >
          Le seguenti DynamoDB tables hanno consumato meno di 10 Read Capacity Units
          (somma) negli ultimi 14 giorni. Questo indica un utilizzo quasi nullo.
        action_desc: >
          Opzioni: (1) Se la tabella non serve piu', rimuoverla da Terraform.
          (2) Se serve raramente, passare a billing_mode PAY_PER_REQUEST
          per pagare solo l'uso effettivo. (3) Se e' un ambiente dev/test,
          verificare se l'applicazione e' ancora attiva.
        to:
          - "resource-owner"
        transport:
          type: sns
          topic: arn:aws:sns:eu-west-1:{account_id}:siae-finops-alerts
```

### Esempio Output Dry-Run

```bash
$ custodian run -s /tmp/c7n-output --dry-run policies/cost/idle-dynamodb.yml

2026-03-13 10:17:12 custodian.policy:INFO policy:idle-dynamodb resource:aws.dynamodb-table count:8
```

Output JSON in `/tmp/c7n-output/idle-dynamodb/resources.json`:

```json
[
  {
    "TableName": "catalogo-legacy-events",
    "TableArn": "arn:aws:dynamodb:eu-west-1:111111111111:table/catalogo-legacy-events",
    "TableStatus": "ACTIVE",
    "BillingModeSummary": {
      "BillingMode": "PROVISIONED"
    },
    "ProvisionedThroughput": {
      "ReadCapacityUnits": 5,
      "WriteCapacityUnits": 5
    },
    "Tags": {
      "Environment": "sviluppo",
      "Project": "catalogo"
    },
    "c7n.metrics": {
      "ConsumedReadCapacityUnits": {
        "Sum": 2.0
      }
    }
  }
]
```

> **Lettura:** 8 tabelle con meno di 10 RCU in 14 giorni. `catalogo-legacy-events` e' PROVISIONED con 5 RCU allocate ma ne usa solo 2 in 14 giorni — candidata per PAY_PER_REQUEST o dismissione.

---

## 5. Policy 4: detached-ebs

EBS volumes non collegati a nessuna istanza. Generano costi di storage senza essere utilizzati.

### YAML

```yaml
policies:
  - name: detached-ebs
    description: |
      Identifica EBS volumes nello stato 'available' (non attached a nessuna istanza).
      Generano costi di storage ($0.08-0.125/GB/mese per gp3/gp2) senza utilizzo.
      Azione: notifica immediata + mark per cancellazione in 30 giorni.
    resource: aws.ebs
    filters:
      - type: value
        key: State
        value: available
    actions:
      - type: notify
        template: default.html
        priority_header: "2"
        subject: "[SIAE FinOps] EBS volumes detached - {account}"
        violation_desc: >
          I seguenti EBS volumes non sono collegati a nessuna istanza EC2.
          Generano costi di storage senza essere utilizzati.
        action_desc: >
          Verificare se il volume contiene dati necessari. Se si', creare uno
          snapshot e cancellare il volume. Se no, cancellare direttamente.
          Il volume sara' marcato per cancellazione automatica tra 30 giorni.
        to:
          - "resource-owner"
        transport:
          type: sns
          topic: arn:aws:sns:eu-west-1:{account_id}:siae-finops-alerts
      - type: mark-for-op
        tag: custodian_cleanup
        op: delete
        days: 30
        msg: "Volume EBS detached: schedulato per cancellazione il {op_date}"
```

### Esempio Output Dry-Run

```bash
$ custodian run -s /tmp/c7n-output --dry-run policies/cost/detached-ebs.yml

2026-03-13 10:18:05 custodian.policy:INFO policy:detached-ebs resource:aws.ebs count:14
```

Output JSON in `/tmp/c7n-output/detached-ebs/resources.json`:

```json
[
  {
    "VolumeId": "vol-0abc123def456789a",
    "Size": 100,
    "VolumeType": "gp3",
    "State": "available",
    "CreateTime": "2025-09-01T08:00:00.000Z",
    "AvailabilityZone": "eu-west-1a",
    "Tags": [
      {"Key": "Environment", "Value": "sviluppo"},
      {"Key": "Project", "Value": "diritti"}
    ]
  }
]
```

> **Lettura:** 14 volumi detached. `vol-0abc123def456789a` e' un gp3 da 100GB creato 6 mesi fa — costa ~$8/mese senza fare nulla. 14 volumi simili possono sommare $50-100/mese di spreco.

---

## 6. Policy 5: old-snapshots

EBS snapshots con oltre 180 giorni di vita. Spesso dimenticati dopo migrazioni o backup manuali.

### YAML

```yaml
policies:
  - name: old-snapshots
    description: |
      Identifica EBS snapshots con eta' superiore a 180 giorni.
      Snapshots vecchi sono spesso dimenticati dopo migrazioni, backup manuali,
      o AMI deregistrate. Costo: $0.05/GB/mese.
    resource: aws.ebs-snapshot
    filters:
      - type: age
        days: 180
        op: greater-than
    actions:
      - type: notify
        template: default.html
        priority_header: "3"
        subject: "[SIAE FinOps] Snapshot EBS >180 giorni - {account}"
        violation_desc: >
          I seguenti EBS snapshots hanno piu' di 180 giorni. Potrebbero
          essere obsoleti (backup manuali, migrazioni completate, AMI deregistrate).
        action_desc: >
          Verificare se lo snapshot e' ancora necessario (es. associato a un'AMI
          attiva o richiesto per compliance). Se non necessario, cancellare
          per ridurre i costi di storage S3 sottostante.
        to:
          - "resource-owner"
        transport:
          type: sns
          topic: arn:aws:sns:eu-west-1:{account_id}:siae-finops-alerts
```

### Esempio Output Dry-Run

```bash
$ custodian run -s /tmp/c7n-output --dry-run policies/cost/old-snapshots.yml

2026-03-13 10:19:22 custodian.policy:INFO policy:old-snapshots resource:aws.ebs-snapshot count:31
```

Output JSON in `/tmp/c7n-output/old-snapshots/resources.json`:

```json
[
  {
    "SnapshotId": "snap-0abc123def456789b",
    "VolumeId": "vol-0xyz987654321fedc",
    "VolumeSize": 500,
    "StartTime": "2025-06-15T02:00:00.000Z",
    "State": "completed",
    "Description": "backup manuale pre-migrazione catalogo",
    "Tags": [
      {"Key": "Environment", "Value": "produzione"},
      {"Key": "Project", "Value": "catalogo"}
    ]
  }
]
```

> **Lettura:** 31 snapshot con >180 giorni. `snap-0abc123def456789b` e' un backup manuale da 500GB — costa $25/mese. Descritto come "pre-migrazione catalogo", probabilmente non piu' necessario.

---

## 7. Policy 6: off-hours-dev

Arresta servizi ECS e istanze RDS negli ambienti di sviluppo fuori dall'orario di lavoro (20:00-08:00 CET nei giorni feriali + weekend intero).

### YAML

```yaml
policies:
  # --- ECS Services: scala a 0 task fuori orario ---
  - name: off-hours-dev-ecs
    description: |
      Scala a 0 i servizi ECS negli ambienti sviluppo fuori orario lavorativo.
      Orario attivo: lun-ven 08:00-20:00 CET. Sabato e domenica: spento.
      Risparmio atteso: ~65% (attivo 60h/settimana vs 168h).
    resource: aws.ecs-service
    filters:
      - type: value
        key: "tag:Environment"
        value: sviluppo
      - type: offhour
        tag: custodian_downtime
        default_tz: cet
        offhour: 20
        weekends: true
    actions:
      - type: resize
        desired: 0

  - name: on-hours-dev-ecs
    description: |
      Ripristina i servizi ECS negli ambienti sviluppo all'inizio dell'orario
      lavorativo. I servizi vengono scalati al valore salvato nel tag.
    resource: aws.ecs-service
    filters:
      - type: value
        key: "tag:Environment"
        value: sviluppo
      - type: onhour
        tag: custodian_downtime
        default_tz: cet
        onhour: 8
        weekends: true
    actions:
      - type: resize
        desired: 1

  # --- RDS: stop fuori orario ---
  - name: off-hours-dev-rds
    description: |
      Ferma le istanze RDS negli ambienti sviluppo fuori orario lavorativo.
      Orario attivo: lun-ven 08:00-20:00 CET. Sabato e domenica: spento.
      Risparmio atteso: ~65%.
    resource: aws.rds
    filters:
      - type: value
        key: "tag:Environment"
        value: sviluppo
      - type: offhour
        tag: custodian_downtime
        default_tz: cet
        offhour: 20
        weekends: true
    actions:
      - type: stop

  - name: on-hours-dev-rds
    description: |
      Riavvia le istanze RDS negli ambienti sviluppo all'inizio dell'orario
      lavorativo.
    resource: aws.rds
    filters:
      - type: value
        key: "tag:Environment"
        value: sviluppo
      - type: onhour
        tag: custodian_downtime
        default_tz: cet
        onhour: 8
        weekends: true
    actions:
      - type: start
```

### Esempio Output Dry-Run

```bash
$ custodian run -s /tmp/c7n-output --dry-run policies/cost/off-hours-dev.yml

2026-03-13 20:01:15 custodian.policy:INFO policy:off-hours-dev-ecs resource:aws.ecs-service count:6
2026-03-13 20:01:16 custodian.policy:INFO policy:off-hours-dev-rds resource:aws.rds count:3
```

Output JSON in `/tmp/c7n-output/off-hours-dev-rds/resources.json`:

```json
[
  {
    "DBInstanceIdentifier": "diritti-dev-postgres",
    "DBInstanceClass": "db.t3.medium",
    "DBInstanceStatus": "available",
    "Engine": "postgres",
    "Tags": [
      {"Key": "Environment", "Value": "sviluppo"},
      {"Key": "Project", "Value": "diritti"},
      {"Key": "Team", "Value": "digital-factory"}
    ]
  }
]
```

> **Lettura:** 6 servizi ECS e 3 RDS in sviluppo attivi fuori orario. `diritti-dev-postgres` (db.t3.medium, ~$50/mese) puo' risparmiare ~$32/mese con off-hours. Su 3 RDS + 6 ECS il risparmio totale stimato e' $150-250/mese.

---

## 8. Policy 7: oversized-rds

Istanze RDS con CPU media inferiore al 10% per 14 giorni. Candidati per rightsizing (classe inferiore).

### YAML

```yaml
policies:
  - name: oversized-rds
    description: |
      Identifica istanze RDS con CPUUtilization media < 10% negli ultimi 14 giorni.
      Indica risorse sovradimensionate che possono essere ridotte di classe
      (es. db.r5.xlarge -> db.r5.large) con risparmio ~50%.
    resource: aws.rds
    filters:
      - type: metrics
        name: CPUUtilization
        statistics: Average
        period: 86400
        days: 14
        value: 10
        op: less-than
    actions:
      - type: notify
        template: default.html
        priority_header: "2"
        subject: "[SIAE FinOps] RDS sovradimensionato (CPU <10%) - {account}"
        violation_desc: >
          Le seguenti istanze RDS hanno avuto una CPU media inferiore al 10%
          negli ultimi 14 giorni, indicando sovradimensionamento.
        action_desc: |
          Suggerimento rightsizing per classe:
          - db.r5.2xlarge (8 vCPU) -> db.r5.xlarge (4 vCPU) = -50%
          - db.r5.xlarge  (4 vCPU) -> db.r5.large  (2 vCPU) = -50%
          - db.t3.xlarge  (4 vCPU) -> db.t3.large  (2 vCPU) = -50%
          - db.t3.large   (2 vCPU) -> db.t3.medium (2 vCPU) = -40%

          Procedura:
          1. Verificare picchi di CPU periodici (batch notturni, report mensili)
          2. Se la CPU max degli ultimi 30gg < 30%, il rightsizing e' sicuro
          3. Modificare la classe in Terraform e fare PR
          4. Apply in sviluppo, monitorare 1 settimana, poi promuovere
        to:
          - "resource-owner"
        transport:
          type: sns
          topic: arn:aws:sns:eu-west-1:{account_id}:siae-finops-alerts
```

### Esempio Output Dry-Run

```bash
$ custodian run -s /tmp/c7n-output --dry-run policies/cost/oversized-rds.yml

2026-03-13 10:20:45 custodian.policy:INFO policy:oversized-rds resource:aws.rds count:4
```

Output JSON in `/tmp/c7n-output/oversized-rds/resources.json`:

```json
[
  {
    "DBInstanceIdentifier": "sport-collaudo-mysql",
    "DBInstanceClass": "db.r5.xlarge",
    "DBInstanceStatus": "available",
    "Engine": "mysql",
    "Tags": [
      {"Key": "Environment", "Value": "collaudo"},
      {"Key": "Project", "Value": "sport"},
      {"Key": "Team", "Value": "core-platforms"}
    ],
    "c7n.metrics": {
      "CPUUtilization": {
        "Average": 3.2
      }
    }
  }
]
```

> **Lettura:** 4 RDS con CPU <10%. `sport-collaudo-mysql` e' un db.r5.xlarge (4 vCPU, ~$548/mese) con CPU media 3.2%. Rightsizing a db.r5.large = -$274/mese. Su 4 istanze il risparmio potenziale e' $500-1000/mese.

---

## 9. Policy 8: glue-runaway

Glue jobs in esecuzione da oltre 4 ore. Indicatore di job bloccati o loop infiniti.

### YAML

```yaml
policies:
  - name: glue-runaway
    description: |
      Identifica Glue jobs in esecuzione da oltre 4 ore (14400 secondi).
      Job che superano questo limite sono probabilmente bloccati, in loop,
      o hanno un errore silente. Azione: notifica per investigazione.
    resource: aws.glue-job
    filters:
      - type: value
        key: ExecutionTime
        value: 14400
        op: greater-than
        value_type: integer
    actions:
      - type: notify
        template: default.html
        priority_header: "1"
        subject: "[SIAE FinOps] URGENTE: Glue job in esecuzione >4 ore - {account}"
        violation_desc: >
          I seguenti Glue jobs sono in esecuzione da oltre 4 ore. Questo e'
          anomalo per i job SIAE tipici (bronze-to-silver: ~30 min, aggregazioni: ~1 ora).
          Potrebbe indicare un loop infinito, deadlock, o data skew.
        action_desc: >
          1. Verificare i log del job in CloudWatch Logs
          2. Se il job e' bloccato, fermarlo manualmente dalla console Glue
          3. Investigare la causa (data volume anomalo? query inefficiente?)
          4. Aggiungere un timeout nel job definition Terraform:
             timeout = 240 (4 ore, in minuti)
        to:
          - "resource-owner"
        transport:
          type: sns
          topic: arn:aws:sns:eu-west-1:{account_id}:siae-finops-alerts
```

### Esempio Output Dry-Run

```bash
$ custodian run -s /tmp/c7n-output --dry-run policies/cost/glue-runaway.yml

2026-03-13 10:21:30 custodian.policy:INFO policy:glue-runaway resource:aws.glue-job count:2
```

Output JSON in `/tmp/c7n-output/glue-runaway/resources.json`:

```json
[
  {
    "Name": "catalogo-bronze-to-silver-etl",
    "Role": "arn:aws:iam::111111111111:role/GlueServiceRole",
    "ExecutionProperty": {
      "MaxConcurrentRuns": 1
    },
    "MaxCapacity": 10.0,
    "NumberOfWorkers": 10,
    "WorkerType": "G.1X",
    "GlueVersion": "4.0",
    "Tags": {
      "Environment": "produzione",
      "Project": "catalogo",
      "Team": "data-platform"
    },
    "ExecutionTime": 21600
  }
]
```

> **Lettura:** 2 job in esecuzione da >4 ore. `catalogo-bronze-to-silver-etl` e' attivo da 6 ore (21600s) con 10 worker G.1X — costo: ~$4.40/ora x 6 ore = $26.40 e in crescita. Investigare immediatamente.

---

## 10. Esecuzione — Dry-Run, Interpretazione, Escalation

### Comandi di Esecuzione

**Dry-run singola policy (nessuna azione eseguita, solo report):**

```bash
# Dry-run su account corrente
custodian run -s /tmp/c7n-output --dry-run policies/cost/tag-enforcement.yml

# Dry-run con output verbose
custodian run -s /tmp/c7n-output --dry-run -v policies/cost/unused-lambda.yml
```

**Dry-run multi-account (c7n-org):**

```bash
# Dry-run su tutti gli account definiti in accounts.yml
c7n-org run -c accounts.yml -s /tmp/c7n-output --dry-run -u policies/cost/tag-enforcement.yml

# Dry-run filtrato per ambiente
c7n-org run -c accounts.yml -s /tmp/c7n-output --dry-run -u policies/cost/off-hours-dev.yml \
  --tags environment:sviluppo
```

**Dry-run di tutte le policy insieme:**

```bash
# Tutte le policy cost in dry-run
custodian run -s /tmp/c7n-output --dry-run policies/cost/*.yml
```

### Interpretazione Output

L'output di ogni policy dry-run include:

| File | Contenuto |
|------|-----------|
| `resources.json` | Lista risorse che matchano i filtri (quelle su cui agirebbe) |
| `metadata.json` | Metadata dell'esecuzione (timestamp, policy name, region) |
| `custodian-run.log` | Log dettagliato dell'esecuzione |

**Come leggere `resources.json`:**

```bash
# Conta risorse trovate
cat /tmp/c7n-output/<policy-name>/resources.json | python -m json.tool | grep -c '"InstanceId"\|"VolumeId"\|"FunctionName"\|"TableName"\|"DBInstanceIdentifier"'

# Estrai nomi/ID per report
cat /tmp/c7n-output/<policy-name>/resources.json | python3 -c "
import json, sys
resources = json.load(sys.stdin)
for r in resources:
    name = r.get('FunctionName') or r.get('DBInstanceIdentifier') or r.get('VolumeId') or r.get('TableName') or r.get('InstanceId') or r.get('SnapshotId') or r.get('Name', 'unknown')
    tags = {t['Key']: t['Value'] for t in r.get('Tags', [])} if isinstance(r.get('Tags'), list) else r.get('Tags', {})
    print(f'{name} | env={tags.get(\"Environment\", \"N/A\")} | project={tags.get(\"Project\", \"N/A\")}')
"
```

### Escalation Graduale

L'enforcement Cloud Custodian segue una progressione obbligatoria:

```
Fase 1: DRY-RUN     →  Solo report, zero azioni
Fase 2: NOTIFY       →  Notifica SNS ai team owner
Fase 3: TAG          →  Tagga risorse (es. custodian_cleanup con data)
Fase 4: STOP/DELETE  →  Azione enforce (solo dopo approvazione esplicita)
```

| Fase | Rischio | Comando | Approvazione |
|------|---------|---------|--------------|
| 1. Dry-run | Nessuno | `custodian run --dry-run ...` | Nessuna |
| 2. Notify | Basso | `custodian run ...` (solo notify action) | Team lead |
| 3. Tag | Medio | `custodian run ...` (tag + notify) | Team lead + Platform |
| 4. Enforce | Alto | `custodian run ...` (stop/delete) | Platform lead + Change Management |

### Pre-Flight Card Template per Enforce

Prima di eseguire **qualsiasi** policy senza `--dry-run`, mostrare:

```
| RISCHIO (livello) — DevForge · siae-finops |
|:---|
| Policy: <nome policy> |
| Account: <account AWS> |
| Risorse impattate: <N risorse da dry-run> |
| Azione: <azione che verra' eseguita> |
| Perche': <motivazione> |
| Se NO: <cosa succede se non si procede> |
```

**Esempio reale:**

```
| ALTO (difficile da annullare) — DevForge · siae-finops |
|:---|
| Policy: detached-ebs |
| Account: siae-sviluppo (111111111111) |
| Risorse impattate: 14 EBS volumes detached |
| Azione: mark-for-op delete in 30 giorni (tag custodian_cleanup) |
| Perche': 14 volumi non attached generano ~$100/mese di spreco |
| Se NO: I volumi restano, il costo continua. Nessun dato perso. |
```

### Makefile per Automazione

```makefile
# c7n-org/Makefile
ACCOUNTS = accounts.yml
OUTPUT   = /tmp/c7n-output
POLICIES = policies/cost

.PHONY: dry-run notify enforce clean

# Fase 1: solo report
dry-run:
	custodian run -s $(OUTPUT) --dry-run $(POLICIES)/*.yml
	@echo "--- Report in $(OUTPUT) ---"
	@for d in $(OUTPUT)/*/; do \
		count=$$(cat "$$d/resources.json" 2>/dev/null | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0); \
		echo "$$(basename $$d): $$count risorse"; \
	done

# Fase 1 multi-account
dry-run-org:
	c7n-org run -c $(ACCOUNTS) -s $(OUTPUT) --dry-run -u $(POLICIES)/*.yml

# Fase 2: notifica (richiede approvazione team lead)
notify:
	@echo "ATTENZIONE: Inviera' notifiche SNS. Confermi? [y/N]" && read ans && [ "$$ans" = "y" ]
	custodian run -s $(OUTPUT) $(POLICIES)/*.yml

# Fase 4: enforce specifico (richiede approvazione platform lead)
enforce-%:
	@echo "ATTENZIONE: Eseguira' enforce su policy $*. Confermi? [y/N]" && read ans && [ "$$ans" = "y" ]
	custodian run -s $(OUTPUT) $(POLICIES)/$*.yml

# Pulizia output
clean:
	rm -rf $(OUTPUT)/*
```

### Schedulazione (Cron / EventBridge)

Per esecuzione periodica automatizzata:

```bash
# Crontab per dry-run giornaliero (08:00 CET)
0 7 * * * cd /opt/c7n-org && make dry-run 2>&1 | mail -s "C7N Daily Report" finops@siae.it

# Off-hours: ogni giorno alle 20:00 e 08:00 CET
0 19 * * 1-5 custodian run -s /tmp/c7n-output policies/cost/off-hours-dev.yml
0 7 * * 1-5 custodian run -s /tmp/c7n-output policies/cost/off-hours-dev.yml
```

Per produzione, preferire **AWS EventBridge + Lambda** che invoca c7n:

```yaml
# EventBridge rule (Terraform)
resource "aws_cloudwatch_event_rule" "c7n_daily" {
  name                = "custodian-daily-audit"
  schedule_expression = "cron(0 7 * * ? *)"
}
```

---

## Riepilogo Policy

| # | Policy | Risorsa | Filtro | Azione | Risparmio Atteso |
|---|--------|---------|--------|--------|------------------|
| 1 | tag-enforcement | EC2, RDS, Lambda, DynamoDB, S3 | Tag SIAE mancanti | notify + auto-tag ManagedBy | Visibilita' costi |
| 2 | unused-lambda | Lambda | LastModified >90gg | notify | $5-20/funzione/mese |
| 3 | idle-dynamodb | DynamoDB | RCU Sum <10 in 14gg | notify | $10-50/tabella/mese |
| 4 | detached-ebs | EBS | state=available | notify + mark delete 30gg | $8-12/volume/mese |
| 5 | old-snapshots | EBS Snapshot | age >180gg | notify | $0.05/GB/mese |
| 6 | off-hours-dev | ECS, RDS | Environment=sviluppo, fuori orario | stop/resize | ~65% costo dev |
| 7 | oversized-rds | RDS | CPU avg <10% in 14gg | notify + rightsizing | ~50% per istanza |
| 8 | glue-runaway | Glue | ExecutionTime >4h | notify | $4-20/ora/job |
