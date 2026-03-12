# Design Doc — Integrazione Moduli Template IaC nella Skill siae-iac

**Data:** 2026-03-12
**Autore:** Lorenzo (AI CC)
**SP stimati:** 5
**Approccio scelto:** A — Sezione monolitica nel siae-iac + reference files

---

## Contesto

Il repo `itsiae/project-template-aws-iac` fornisce moduli Terraform predefiniti
per i progetti SIAE. Attualmente contiene 3 moduli (vpc, api-private, api-public).
Sono in sviluppo 3 nuovi moduli: rds-postgres, dynamodb, cognito.

La skill `siae-iac` del plugin DevForge non menziona il template repo.
Obiettivo: integrare nella skill esistente una sezione dedicata al template,
con blueprint per tutti i moduli (esistenti e nuovi), senza creare nuove skill.

## Decisioni

### Approccio

- **Scelto: A** — Sezione nel SKILL.md (~65 righe) + 6 reference files per i dettagli
- Scartato B (reference doc esterno): due file da mantenere, rischio drift
- Scartato C (solo checklist): non guida sulle scelte architetturali per servizio

### Migration tool per RDS Postgres: Flyway

- SQL puro, language-agnostic (serve 4 stack: Java, Python, TS, HCL)
- Versionamento chiaro: `V{N}__{descrizione}.sql`
- Il modulo TF non esegue migrations — espone endpoint + secret ARN per CI/CD
- Scartato Liquibase: over-engineered per template
- Scartato ORM migrations: accoppia infra a linguaggio specifico

### DynamoDB: Completo

- Billing mode PAY_PER_REQUEST default, PROVISIONED + autoscaling per prod
- GSI/LSI dinamici via `for_each`
- Streams + Lambda trigger opzionali
- Replica globale multi-region via `for_each` su `replica_regions`
- Contributor insights abilitabile per prod
- Table class: STANDARD default, STANDARD_IA per dati storici

### Cognito: 3 scenari via variabile `auth_scenario`

- `"user_pool"`: User Pool classico (signup, signin, MFA, recovery)
- `"user_pool_identity"`: User Pool + Identity Pool (accesso diretto risorse AWS)
- `"federation"`: SSO via SAML/OIDC (Active Directory SIAE), no self-signup
- Risorse condizionali via `count` (Identity Pool) e `for_each` (IdP)
- MFA: OFF dev, OPTIONAL collaudo/cert, ON produzione
- OAuth: Authorization Code + PKCE default, mai implicit

### Pattern template mantenuti

- Tutti i moduli `.disabled` di default
- Variabili standard: `account_id`, `region`, `project`, `env`, `module`, `config`
- Naming: `prefix = "${var.env}-${var.project}-${var.module}"`
- Dipendenze Terragrunt con `mock_outputs`

## File da modificare/creare

### Modifica

| File                       | Azione                                            |
|----------------------------|---------------------------------------------------|
| `skills/siae-iac/SKILL.md` | Aggiungere sezione 7 "Template Repo" (~65 righe) |

### Nuovi file

| File                                                   | Contenuto                        |
|--------------------------------------------------------|----------------------------------|
| `skills/siae-iac/reference/template-vpc.md`            | Blueprint modulo VPC (data lookup) |
| `skills/siae-iac/reference/template-api-private.md`    | Blueprint API Gateway PRIVATE    |
| `skills/siae-iac/reference/template-api-public.md`     | Blueprint API Gateway EDGE       |
| `skills/siae-iac/reference/template-rds-postgres.md`   | Blueprint RDS Postgres + Flyway  |
| `skills/siae-iac/reference/template-dynamodb.md`       | Blueprint DynamoDB completo      |
| `skills/siae-iac/reference/template-cognito.md`        | Blueprint Cognito 3 scenari      |

## Criteri di accettazione

- [ ] SKILL.md sotto 500 righe dopo modifica
- [ ] Sezione 7 nel SKILL.md con tabella moduli e link ai reference
- [ ] 6 reference files con blueprint completi
- [ ] Checklist "come creare un nuovo modulo" nel SKILL.md
- [ ] Nessuna nuova skill creata
- [ ] Test `run-all.sh` passano (structure + catalog)

## Dependency graph moduli template

```text
vpc (root)
├── api-private
├── api-public
└── rds-postgres

dynamodb (standalone)
cognito (standalone)
```

## Sizing per ambiente (riepilogo cross-modulo)

| Risorsa           | Sviluppo    | Collaudo    | Certificazione | Produzione   |
|-------------------|-------------|-------------|----------------|--------------|
| RDS instance      | db.t3.micro | db.t3.small | db.t3.medium   | db.r6g.large |
| RDS multi_az      | false       | false       | true           | true         |
| RDS backup        | 1d          | 3d          | 7d             | 35d          |
| DynamoDB billing  | on-demand   | on-demand   | provisioned    | provisioned  |
| DynamoDB replica  | no          | no          | no             | eu-central-1 |
| Cognito MFA       | OFF         | OPTIONAL    | OPTIONAL       | ON           |
| Cognito security  | OFF         | AUDIT       | AUDIT          | ENFORCED     |

---

```text
REQUIRED SUB-SKILL: siae-writing-plans
```
