# SIAE Multi-repo (iac/bff/spa)

> Fonte canonica versionata (REQ-DF-06). Iniettata da `hooks/session-start`.
> Se questo file manca, DICHIARA l'assenza — non indovinare il repo da toccare.

## Ruoli
- **iac** — Infrastructure as Code: modifiche infra (Terraform/terragrunt).
- **bff** — Backend for Frontend: API/backend.
- **spa** — Single Page Application: frontend.

## Regola di routing
- Modifica infra → repo `*-iac`.
- Modifica API/backend → repo `*-bff`.
- Modifica frontend → repo `*-spa`.
- **Mai** applicare modifiche nel repo sbagliato: se il task è cross-cutting,
  ripartire le modifiche coerentemente sui repo giusti (vedi Cross-cutting).

## Naming (verificato su org `itsiae`, 2026-07-01)
Convenzione a suffisso: `*-iac` (50+ repo), `*-bff` (13 repo), `*-spa` (9 repo).
Triple complete di esempio: `jarvis-{iac,bff,spa}`, `rete-eventi-{core-iac,bff,spa}`,
`routing-algorithm-{core-iac,bff,spa}`, `dataplatform-datacatalog-{iac,bff,spa}`.
Segnale secondario (se il nome non basta): iac = `*.tf`/`terragrunt.hcl`;
bff = servizio backend/API; spa = frontend `package.json`+router/build.
Nota: SIAE usa anche i suffissi `-be`/`-fe`/`-service` per i microservizi
SPORT/PAE — non sostituiscono `iac`/`bff`/`spa`, sono una convenzione diversa.

## Cross-cutting
Un cambiamento che tocca infra + backend + frontend (es. nuovo endpoint con
consumo frontend) va ripartito coerentemente sui tre repo, non concentrato in uno solo.
