# Stack: Java / JVM

## Stack id

`java`

## Manifest fingerprints

- File globs: `**/pom.xml`, `**/build.gradle`, `**/build.gradle.kts`, `**/settings.gradle`, `**/settings.gradle.kts`, `**/*.java`
- Content patterns: `<groupId>` in `pom.xml`; `plugins { id "java" }` or `apply plugin: 'java'` in Gradle scripts
- Negative match: presence of `kotlin` plugin in Gradle → dispatch to `kotlin.md` instead

## Analysis-unit granularity

- Maven multi-module: each `<module>` under the parent `pom.xml` is one analysis unit.
- Gradle multi-project: each `include` in `settings.gradle[.kts]` is one analysis unit.
- Single-module: the repo root is one unit.
- See [../repo_granularity.md](../repo_granularity.md) for the deterministic split algorithm.

## Parser

- Tree-sitter grammar: `tree-sitter-java`
- Max AST depth: 5
- Regex fallback used only when grammar load fails or the file is over 5 MB.

## Entry-point kinds detected

| Framework / surface | `entry_point.kind` | Detection signal |
|---|---|---|
| Spring MVC / WebFlux REST | `http-route` | Annotations `@RestController` / `@Controller` + `@GetMapping` / `@PostMapping` / `@RequestMapping` |
| JAX-RS | `http-route` | Annotations `@Path` + HTTP verb annotations (`@GET`, `@POST`, ...) |
| Spring Cloud Function | `http-route` | `@Bean` returning `Function<T,R>` + `spring.cloud.function.definition` |
| Quarkus REST | `http-route` | `@Path` + Quarkus-specific imports |
| Micronaut REST | `http-route` | `@Controller` + `@Get` / `@Post` from `io.micronaut.http` |
| gRPC service impl | `grpc-method` | Class extending `<ServiceName>ImplBase` generated from `.proto` |
| Kafka consumer | `message-consumer` | `@KafkaListener` (Spring) or `@Incoming` (Quarkus / SmallRye) |
| RabbitMQ consumer | `message-consumer` | `@RabbitListener` |
| JMS consumer | `message-consumer` | `@JmsListener` |
| Scheduled job | `scheduled-job` | `@Scheduled` (Spring), `@Schedule` (Java EE) |
| CLI entry | `cli-command` | `public static void main(String[] args)` in a class outside `src/test` |
| Spring Batch step | `batch-runner` | `StepBuilder` / `JobBuilder` usage |
| JDBC trigger handler | `db-trigger` | rare; flagged when stored proc names appear in `@Procedure` calls |
| GraphQL resolver | `graphql-resolver` | `@QueryMapping` / `@MutationMapping` (Spring GraphQL); `DataFetcher` impls |

## Inputs typing

- Spring: `@RequestBody T body` → `inputs[].type = T` resolved via class lookup; `@PathVariable`, `@RequestParam`, `@RequestHeader` give `name + type`.
- JAX-RS: `@PathParam`, `@QueryParam`, `@HeaderParam`, `@FormParam` carry name; the parameter Java type is the type.
- Records and Lombok `@Data` classes are flattened to field-level inputs.
- Bean Validation annotations (`@NotNull`, `@Size`, `@Pattern`) are captured as `inputs[].validation` hints.

## Side-effect detection

- Persistence: Spring Data repositories (`JpaRepository`, `MongoRepository`, `R2dbcRepository`), Hibernate `EntityManager`, MyBatis mappers.
- HTTP clients: `RestTemplate`, `WebClient`, `FeignClient`, OpenFeign-generated stubs, `HttpClient` (JDK 11+).
- Message publishers: `KafkaTemplate.send`, `RabbitTemplate.convertAndSend`, `JmsTemplate.send`, `SnsClient.publish`, `SqsClient.sendMessage`.
- Filesystem and S3: `Files.write`, `S3Client.putObject`, `MultipartFile.transferTo`.
- Each side effect is recorded as `side_effects[].resource_id` using the resolved bean name, queue name, or bucket name (literal or `@Value`-resolved).

## Cross-stack bridge hints

- `WebClient` / `RestTemplate` URI string → `http-route` lookup across other units (see [../cross_stack_bridges.md](../cross_stack_bridges.md) row "HTTP URI literal").
- `KafkaTemplate.send("<topic>", ...)` → `message-consumer` lookup by topic name.
- `@FeignClient(name="<service-name>")` → DNS-style match against `aws-serverless` or `terraform-hcl` service definitions.

## Bug-patterns row pointer

See [../bug_patterns.md](../bug_patterns.md) — Java-applicable rows include
all rows where column `java` = `MUST-if-applicable`. Specifically relevant:
input validation gaps, authz inversions, transactional-boundary leaks
(`@Transactional` misuse), N+1 query manifestations as user-visible
latency, retry/timeout pathologies (Resilience4j misconfiguration),
optimistic locking version drift, and Bean Validation bypass via DTO
copy.

## Empty-input branch

If a unit is detected as `java` (manifest present) but **zero** entry
points are extracted (e.g. a pure library JAR with no public main or
controller), the unit is recorded in `coverage.md` with skip reason
`no-entry-points` and excluded from phases 4–7. The unit still contributes
to `dependency_closure.md` as a referenced library if other units depend
on it.
