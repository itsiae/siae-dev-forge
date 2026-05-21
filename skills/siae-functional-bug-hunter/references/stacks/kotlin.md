# Stack: Kotlin

## Stack id

`kotlin`

## Manifest fingerprints

- File globs: `**/build.gradle.kts` containing the kotlin plugin, `**/*.kt`, `**/*.kts`
- Content patterns: `plugins { kotlin("jvm") }` / `plugins { kotlin("multiplatform") }` / `plugins { kotlin("android") }` in Gradle Kotlin DSL.
- Negative match: a Java-only Gradle script in the same multi-project → that submodule dispatches to `java.md`.

## Analysis-unit granularity

- **Gradle multi-project**: each `include` in `settings.gradle.kts` is one analysis unit; the runtime checks per-module plugins to decide kotlin vs java dispatch.
- **Kotlin Multiplatform (KMP)**: each target (`jvm`, `js`, `iosArm64`, ...) is treated as a sub-unit only when source sets diverge.
- See [../repo_granularity.md](../repo_granularity.md).

## Parser

- Tree-sitter grammar: `tree-sitter-kotlin`.
- Max AST depth: 5.
- DSL-heavy code (Gradle build scripts) is parsed only for plugin / dependency declaration extraction, not for entry-point detection.

## Entry-point kinds detected

| Framework / surface | `entry_point.kind` | Detection signal |
|---|---|---|
| Spring (Kotlin) REST | `http-route` | `@RestController` + `@GetMapping` etc. — same as `java.md` |
| Ktor server | `http-route` | `routing { get("<path>") { ... } }` / `post("<path>") { ... }` |
| Micronaut Kotlin | `http-route` | `@Controller` + `@Get` / `@Post` |
| http4k | `http-route` | `routes("<path>" bind <Method> to handler)` |
| gRPC Kotlin | `grpc-method` | class extending `<ServiceName>CoroutineImplBase` |
| Kafka consumer | `message-consumer` | `@KafkaListener` (Spring) or coroutine-based `KafkaConsumer.poll` in a flow |
| AWS Lambda Kotlin | depends on event | `RequestHandler<I, O>` impl referenced in IaC |
| Android Activity / Fragment | `ui-screen` | class extending `AppCompatActivity` / `Fragment` with `onCreate` + intent filter in `AndroidManifest.xml` |
| Coroutine scheduled task | `scheduled-job` | `launch { while (isActive) { delay(...) ; doWork() } }` patterns OR `ScheduledExecutorService.scheduleAtFixedRate` |
| Kotlin Multiplatform shared module | varies | exported `expect`/`actual` functions called from platform UI |

## Inputs typing

- Spring Kotlin: same as `java.md`, with Kotlin data classes preferred over POJOs; nullability from `?` types is a first-class validation hint.
- Ktor: `call.receive<DTO>()` resolves to `DTO`; `call.parameters["<name>"]` is `String?`.
- Validation: `kotlinx.serialization` `@Serializable` + `@SerialName` captured; `javax.validation` annotations preserved.
- Nullable vs non-null types are recorded as a strict typing hint (a non-null parameter from a nullable source is a bug-pattern row trigger).

## Side-effect detection

- Persistence: Spring Data Kotlin, Exposed (`Table.insert/update/deleteWhere`), Ktorm, JOOQ Kotlin.
- HTTP clients: Ktor client (`HttpClient().get / post`), OkHttp, Retrofit interfaces.
- Message publishers: Kafka same as Java; coroutine-based `Flow.emit` to a hot flow is recorded only when the flow is a `MutableSharedFlow` bound to an external producer.
- Filesystem and S3: `java.nio.file.Files`, AWS SDK same as Java.
- Coroutine launch without supervisor / structured concurrency is flagged for "swallowed exception" pattern.

## Cross-stack bridge hints

- Ktor client / OkHttp / Retrofit base URLs → `http-route` resolution.
- AWS SDK Kotlin → `aws-serverless` lookups.
- Android `Intent` with explicit class names → resolved to other Android units only.
- See [../cross_stack_bridges.md](../cross_stack_bridges.md).

## Bug-patterns row pointer

See [../bug_patterns.md](../bug_patterns.md) — rows where column `kotlin`
= `MUST-if-applicable`. Specifically: nullable propagation to non-null
field, coroutine cancellation losing work, `runBlocking` on a request
thread (deadlock), Compose recomposition state desync, sealed class
exhaustive `when` missing a branch leading to silent fall-through,
Kotlin Flow buffer dropping under load.

## Empty-input branch

If a unit is detected as `kotlin` but **zero** entry points are extracted
(e.g. a shared KMP library with no platform binding), the unit is
recorded in `coverage.md` with skip reason `no-entry-points`. Android
units without an `AndroidManifest.xml` intent filter for the activity are
recorded with `no-entry-points` as well, since the activity is
unreachable from the user.
