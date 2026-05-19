# Project CLAUDE.md (Lean Example)

Concise project context. Aim: minimum signal needed for Claude to avoid
mistakes. Every line answers "would removing this cause Claude to make
mistakes?" with yes.

## Build

```bash
make build   # compile + lint
make test    # unit + integration
make run     # local server on :8080
```

## Stack

- Java 17 + Spring Boot 3.1
- PostgreSQL 14 (migrations: Liquibase)
- Kafka 3.5 for domain events
- Redis 7 for session/cache

## Module map

- `api/` — REST + gRPC endpoints
- `domain/` — pure aggregates, no Spring
- `infra/` — adapters (DB, Kafka, Redis)
- `batch/` — scheduled jobs

Each module has its own `CLAUDE.md` (L2) loaded on demand.

## Conventions

- Migrations under `infra/src/main/resources/db/changelog/`
- Kafka topic naming: `<domain>.<event-type>`
- Outbox pattern for cross-aggregate events
- RFC 7807 ProblemDetail for error responses

## Risks

- Connection pool sized for 50 concurrent users — reuse, do not open new
  connections per call
- Liquibase lock can stick after crash — `DELETE FROM databasechangeloglock`
  is the documented recovery

## Where Claude tends to break

- Editing Liquibase changesets retroactively (forbidden — append new only)
- Adding Spring annotations into `domain/` (must stay framework-free)
- Bypassing outbox for cross-aggregate writes (race condition)

## Test commands

```bash
mvn -pl domain test           # fast, no Docker
mvn -pl api verify -P it      # spins Testcontainers
```

## Deployment

Helm chart in `deploy/charts/api`. Promote staging → prod via approval
workflow in `.github/workflows/deploy.yml`.

## Pointers

- API contract: `docs/openapi.yaml`
- Event schemas: `docs/avro/`
- Runbook: `docs/runbook.md`
