# Stack: Go

## Stack id

`go`

## Manifest fingerprints

- File globs: `**/go.mod`, `**/go.sum`, `**/go.work`, `**/*.go`
- Content patterns: `module <name>` directive in `go.mod`; `package <name>` header in `.go` files.
- Negative match: `*_test.go` files are recognized but never produce entry points (skip reason `out-of-scope`).

## Analysis-unit granularity

- **Go workspace** (`go.work`): each `use` directive is one analysis unit.
- **Bazel `go_binary`**: each target is one unit.
- **Single module**: the directory containing `go.mod` is one unit.
- **Multi-module monorepo without workspace**: each `go.mod` is one unit.
- See [../repo_granularity.md](../repo_granularity.md).

## Parser

- Tree-sitter grammar: `tree-sitter-go`.
- Max AST depth: 5.
- Regex fallback for environments without the grammar; `go/ast` from the toolchain is NOT invoked (would require `go` binary on PATH, out of scope for read-only).

## Entry-point kinds detected

| Framework / surface | `entry_point.kind` | Detection signal |
|---|---|---|
| `net/http` stdlib | `http-route` | `http.HandleFunc("<path>", fn)` / `mux.HandleFunc(...)` / `http.Handle(...)` |
| Gin | `http-route` | `router.GET/POST/...("<path>", handler)` |
| Echo | `http-route` | `e.GET/POST/...("<path>", handler)` |
| Chi | `http-route` | `r.Get/Post/...("<path>", handler)` |
| Fiber | `http-route` | `app.Get/Post/...("<path>", handler)` |
| gRPC service impl | `grpc-method` | method implementations on a struct matching the `<Service>Server` interface generated from `.proto` |
| AWS Lambda Go handler | `http-route` for APIGatewayProxyRequest; `message-consumer` for SQS/SNS; `scheduled-job` for CloudWatchEvent | `lambda.Start(handler)` in `main()` |
| Kafka consumer (sarama / segmentio) | `message-consumer` | `ConsumerGroupHandler.ConsumeClaim` implementations |
| NATS subscriber | `message-consumer` | `nc.Subscribe("<subject>", handler)` |
| `cron.v3` scheduled job | `scheduled-job` | `c.AddFunc("<expr>", fn)` |
| CLI entry | `cli-command` | `func main()` + `cobra.Command{...}` / `urfave/cli` registrations |
| Custom resource | `iac-apply-surface` | when used as a Terraform provider plugin (rare; flagged) |

## Inputs typing

- Request decoding via `json.NewDecoder(r.Body).Decode(&dto)` → `inputs[].type` is the `dto` struct, with struct-tag-driven JSON schema.
- `chi.URLParam(r, "id")`, `gin.Param("id")`, `c.Query("name")` → captured as `inputs[]` with `type=string` unless converted with `strconv.Atoi` / `uuid.Parse` etc.
- Generics (`func[T any]`) are recorded with type parameters as `T`; constraint interfaces preserved.
- Validator tags (`validate:"required,min=1,max=100"`) are captured as `inputs[].validation`.

## Side-effect detection

- Persistence: `database/sql` `Exec` / `QueryRow` with non-SELECT; `gorm` `db.Create/Save/Update/Delete`; `sqlx` `NamedExec`; `pgx` `Exec`.
- HTTP clients: `http.Client.Do`, `http.Get/Post`, `resty` calls.
- Message publishers: `kafka-go` `Writer.WriteMessages`, AWS SDK v2 (`sqs.SendMessage`, `sns.Publish`, `eventbridge.PutEvents`), NATS `nc.Publish`.
- Filesystem: `os.WriteFile`, `os.Create`+`Write`.
- Goroutine leaks → not directly a side effect, but flagged when a goroutine writes to a shared map without `sync.Mutex` or `sync.Map`.

## Cross-stack bridge hints

- `http.Get("http://...")` literal → `http-route` lookup across units.
- AWS SDK v2 `lambda.Invoke(FunctionName=...)` → `aws-serverless` resolution.
- `grpc.Dial("<target>")` → `grpc-method` resolution via service descriptor.
- See [../cross_stack_bridges.md](../cross_stack_bridges.md).

## Bug-patterns row pointer

See [../bug_patterns.md](../bug_patterns.md) — rows where column `go` =
`MUST-if-applicable`. Specifically: nil pointer dereference on error path
ignored (`if err != nil { return }` but variable used after), goroutine
data race on shared map, `context.Context` cancellation not propagated,
defer in loop causing late close, time.Now() without timezone, integer
overflow on `int32` arithmetic, JSON unmarshal silently dropping unknown
fields (`DisallowUnknownFields` not set).

## Empty-input branch

If a unit is detected as `go` (`go.mod` present) but **zero** entry points
are extracted (e.g. a pure library module), the unit is recorded in
`coverage.md` with skip reason `no-entry-points`. The unit still
contributes to `dependency_closure.md` when other units import it.
