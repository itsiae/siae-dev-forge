# Stack: Scala

## Stack id

`scala`

## Manifest fingerprints

- File globs: `**/build.sbt`, `**/project/build.properties`, `**/project/plugins.sbt`, `**/*.scala`, `**/*.sc`
- Content patterns: `scalaVersion :=` in `build.sbt`; `sbt.version=` in `build.properties`.
- Negative match: `build.gradle.kts` with Scala plugin → dispatched here regardless of Gradle (rare).

## Analysis-unit granularity

- **SBT multi-project**: each `lazy val <name> = project ...` in `build.sbt` is one analysis unit.
- **Mill**: each `module` in `build.sc` is one unit.
- **Single project**: the repo root is one unit.
- See [../repo_granularity.md](../repo_granularity.md).

## Parser

- Tree-sitter grammar: `tree-sitter-scala`.
- Max AST depth: 5.
- Macro-heavy code (Scala 2 macros, Scala 3 inline) is parsed at the call site; macro expansion is not performed.

## Entry-point kinds detected

| Framework / surface | `entry_point.kind` | Detection signal |
|---|---|---|
| Akka HTTP | `http-route` | `path("<segment>") { get { complete(...) } }` route DSL |
| Play Framework | `http-route` | `conf/routes` file entries + matching controller action |
| http4s | `http-route` | `HttpRoutes.of[F] { case GET -> Root / "<path>" => ... }` |
| Tapir | `http-route` | `endpoint.in("<path>").out(jsonBody[T])` |
| ZIO HTTP | `http-route` | `Http.collect { case Method.GET -> !! / "<path>" => ... }` |
| Akka cluster / Pekko | `message-consumer` | `Behaviors.receiveMessage` actor patterns |
| Kafka consumer (Alpakka / fs2-kafka) | `message-consumer` | `Consumer.committableSource(settings, subscription)` |
| Spark batch / streaming job | `batch-runner` | `SparkSession.builder()` + `spark.read` / `streamingDF.writeStream` |
| sbt task | `cli-command` | custom `lazy val <task> = taskKey[Unit]("...")` |
| ZIO HTTP scheduled (cron via `Schedule`) | `scheduled-job` | `Schedule.fixed(<duration>)` + `.repeat` on an effect |

## Inputs typing

- Akka HTTP: `entity(as[T])` directive → `T` is the JSON case class with circe / spray-json codec.
- Play: action `parse.json[T]` → typed; form binding via `Form(mapping(...))`.
- Tapir / http4s: endpoint definition is the source of truth; query/path/body parameters are explicit and statically typed.
- Refined types (`Refined[String, NonEmpty]`) captured as validation constraints.

## Side-effect detection

- Persistence: Slick `db.run(insert / update / delete)`, Doobie `Fragment.update.run` / `.unique`, Quill `run(insert/update/delete)`.
- HTTP clients: sttp, http4s client, Akka HTTP `Http().singleRequest`, ZIO HTTP client.
- Message publishers: fs2-kafka `Producer.produce`, Alpakka Kafka `Producer.plainSink`, AWS SDK Scala (`Aws-Scala`).
- Filesystem: `java.nio.file.Files` (same as Java).
- Future / IO without proper error handling — `.unsafeRunSync()` in production code is flagged.

## Cross-stack bridge hints

- sttp / http4s / ZIO HTTP client URL literals → `http-route` resolution.
- AWS SDK calls → `aws-serverless` lookups.
- Akka HTTP cluster sharding entity ids → cross-actor-system boundary (recorded but rarely resolvable from static analysis).
- See [../cross_stack_bridges.md](../cross_stack_bridges.md).

## Bug-patterns row pointer

See [../bug_patterns.md](../bug_patterns.md) — rows where column `scala`
= `MUST-if-applicable`. Specifically: `Option.get` on `None` (functional
crash), `Future` without `recover` swallowing errors silently,
implicit-resolution picking unexpected typeclass instance leading to
wrong behavior at runtime, partial pattern match raising
`MatchError`, blocking call on `ExecutionContext.global` starving the
thread pool, Spark job non-determinism from missing `orderBy` before
`limit`.

## Empty-input branch

If a unit is detected as `scala` but **zero** entry points are extracted
(e.g. a pure library `.jar`), the unit is recorded in `coverage.md` with
skip reason `no-entry-points`. `src/test/scala` directories are
auto-excluded with `out-of-scope`.
