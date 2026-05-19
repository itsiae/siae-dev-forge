# Project CLAUDE.md (Bloated Example)

This is an intentionally bloated CLAUDE.md fixture used to exercise the
anti-bloat-lint.py script. It must exceed 200 lines to trigger the
`line_count` rule.

## Overview

This project is a large monolithic Java service that handles payments,
reporting, notifications, batch jobs, scheduled tasks, message consumers,
HTTP endpoints, gRPC endpoints, GraphQL endpoints, and more.

The codebase is organised in 12 Maven modules, each of which has its own
domain language, persistence layer, configuration, and bootstrap logic.

## Build commands

```bash
mvn clean install -DskipTests
mvn test
mvn verify -P integration
mvn spring-boot:run -pl api
mvn dependency:tree
mvn versions:display-dependency-updates
mvn versions:display-plugin-updates
mvn javadoc:javadoc
mvn site
mvn deploy -P release
```

## Directory layout

```
src/
  main/
    java/com/example/payments/...
    java/com/example/reporting/...
    java/com/example/notifications/...
    java/com/example/batch/...
    resources/application.yml
    resources/logback.xml
    resources/messages_en.properties
    resources/messages_it.properties
  test/
    java/com/example/payments/...
    java/com/example/reporting/...
    resources/test-application.yml
```

## Tech stack

- Java 17
- Spring Boot 3.1
- PostgreSQL 14
- Liquibase 4.20
- Apache Kafka 3.5
- Redis 7
- ElasticSearch 8.10
- Vault 1.14
- Consul 1.16
- Docker Compose for local dev
- Testcontainers for integration tests
- WireMock for HTTP stubs
- AssertJ + JUnit 5
- Maven 3.9 with toolchain
- GitHub Actions CI

## Coding standards

This section repeats a lot of generic advice that is already covered by
the siae-code-standards skill. Inclusion here is intentional bloat.

- Use meaningful variable names.
- Functions should be small and focused.
- Avoid magic numbers; extract constants.
- Prefer composition over inheritance.
- Use Optional instead of null.
- Wrap checked exceptions with custom unchecked exceptions when crossing
  layer boundaries.
- Log at appropriate levels (DEBUG/INFO/WARN/ERROR).
- Never log secrets or PII.
- Always close resources via try-with-resources.
- Document public API with Javadoc.
- Avoid static mutable state.
- Prefer immutability where possible.
- Use records for DTOs (Java 17).
- Validate inputs at the boundary.
- Return defensive copies of collections.

## Spring profiles

- `local` — H2 in-memory DB, no Kafka.
- `dev` — Dockerized infra via docker-compose.
- `staging` — Pre-production AWS environment.
- `prod` — Production AWS environment, blue-green.

## Database conventions

Liquibase changesets live under `src/main/resources/db/changelog/`.
Naming: `YYYYMMDD_HHMM__short-description.xml`.
Use `databaseChangeLog` root element with author = jira ticket.

## Kafka topics

- `payments.events` — domain events from payment aggregate
- `payments.commands` — incoming commands
- `reporting.events` — read-model events
- `notifications.outbox` — outbox pattern
- `dlq.payments` — dead letter queue

Producer keys: aggregate id. Partitions: 12 in prod. Retention: 7 days.

## Redis keys

- `session:{userId}` — user session
- `idempotency:{key}` — idempotency lock
- `cache:user:{id}` — user cache, TTL 5min

## Endpoints (REST)

- `POST /api/v1/payments` — create payment
- `GET /api/v1/payments/{id}` — fetch payment
- `POST /api/v1/payments/{id}/refund` — refund payment
- `GET /api/v1/reports/daily` — daily report
- `POST /api/v1/notifications` — send notification

## Endpoints (gRPC)

- `PaymentService.Create`
- `PaymentService.Get`
- `PaymentService.Refund`
- `ReportingService.Daily`

## Endpoints (GraphQL)

- `query { payment(id: ID!): Payment }`
- `mutation { createPayment(input: PaymentInput!): Payment }`

## Common workflows

### Add a new payment method

1. Add enum entry in `PaymentMethod.java`
2. Add factory in `PaymentMethodFactory.java`
3. Add Liquibase changeset
4. Add integration test in `PaymentMethodIT.java`
5. Update documentation in `docs/payment-methods.md`

### Add a new Kafka consumer

1. Create class extending `AbstractKafkaConsumer`
2. Annotate with `@KafkaListener(topics = "...")`
3. Add error handler bean
4. Add integration test using `EmbeddedKafka`

### Add a new report

1. Define DTO in `reporting/dto/`
2. Add query method in `ReportingRepository`
3. Add service in `ReportingService`
4. Add controller endpoint
5. Add OpenAPI docs

## Local development setup

1. Clone repo
2. Run `make up` to start docker-compose stack
3. Run `make migrate` to apply Liquibase changes
4. Run `make seed` to load test data
5. Run `mvn spring-boot:run -pl api -Dspring-boot.run.profiles=local`
6. Test with `curl http://localhost:8080/actuator/health`

## Deployment

Pipeline: `.github/workflows/deploy.yml`.
Stages: lint → test → build → push to ECR → deploy via Helm.
Approval required for staging and prod.
Rollback via `helm rollback {release} {revision}`.

## Monitoring

- Prometheus scrape: `/actuator/prometheus`
- Grafana dashboards: see `monitoring/dashboards/`
- Alertmanager rules: see `monitoring/alerts/`
- Sentry DSN configured via env var
- ElasticSearch APM via APM agent jar

## Security

- All endpoints behind OAuth2 (Cognito JWT)
- mTLS between services in mesh
- Vault for secrets at rest
- Cognito groups map to Spring authorities
- CSRF disabled for stateless API
- CORS configured per-environment

## Caching strategy

- Read-through cache for user profile
- Write-through cache for product catalog
- TTL of 5 minutes for hot data
- TTL of 24 hours for warm data
- Cache invalidation via Kafka events

## Batch jobs

- `nightly-report` — runs at 02:00 UTC
- `cleanup-expired-sessions` — runs every hour
- `reconciliation` — runs at 04:00 UTC, downstream of nightly-report
- `archive-old-payments` — runs on the 1st of each month at 03:00 UTC

## Error handling

- All exceptions caught at controller advice
- Mapped to ProblemDetail (RFC 7807) responses
- Trace ID propagated via `X-Trace-Id` header
- Sentry integration captures stack traces
- Sensitive data scrubbed before logging

## Testing strategy

- Unit tests: pure Java, mock dependencies
- Integration tests: Testcontainers (Postgres, Kafka, Redis)
- Contract tests: Pact between services
- E2E tests: Playwright against staging
- Load tests: Gatling, run weekly in CI

## Performance considerations

- JVM tuning: G1GC, heap 4GB in prod
- Connection pool: HikariCP, max 50
- Kafka batch size: 100 records
- Redis pipeline for bulk ops
- Async logging via Logback AsyncAppender

## Observability

- Logs in JSON via Logback encoder
- Correlation ID in MDC
- Metrics via Micrometer + Prometheus
- Tracing via OpenTelemetry
- Logs shipped to ElasticSearch via Filebeat

## Internationalization

- Messages in `messages_{locale}.properties`
- Supported locales: en, it, es, fr, de
- Number/date formatting via Spring locale resolver
- Accept-Language header parsed by interceptor

## Known issues

- Connection pool starvation under high load
- Occasional Kafka rebalance storms
- Redis OOM if cache TTL not enforced
- Liquibase lock not released on crash (manual fix needed)

## Future work

- Migrate to Java 21 virtual threads
- Adopt Kotlin for new modules
- Replace Liquibase with Flyway
- Move from Kafka to Pulsar
- Add GraphQL federation
