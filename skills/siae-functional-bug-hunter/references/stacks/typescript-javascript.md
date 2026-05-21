# Stack: TypeScript / JavaScript

## Stack id

`typescript-javascript`

## Manifest fingerprints

- File globs: `**/package.json`, `**/tsconfig.json`, `**/*.ts`, `**/*.tsx`, `**/*.mts`, `**/*.cts`, `**/*.js`, `**/*.jsx`, `**/*.mjs`, `**/*.cjs`
- Content patterns: `"main"` / `"module"` / `"exports"` keys in `package.json`; `"compilerOptions"` in `tsconfig.json`.
- Negative match: presence of `flutter` SDK in `pubspec.yaml` sibling → dispatch is to `flutter-dart.md` for `.dart` files only; `.ts` files in the same repo still dispatch here.

## Analysis-unit granularity

- **Nx**: `nx.json` + `project.json` in each package → each package is one analysis unit.
- **Turborepo**: `turbo.json` + workspaces from `package.json` (`workspaces` field) → each workspace is one unit.
- **pnpm workspace**: `pnpm-workspace.yaml` → each package is one unit.
- **Single package**: the repo root is one unit.
- See [../repo_granularity.md](../repo_granularity.md).

## Parser

- Tree-sitter grammars: `tree-sitter-typescript` for `.ts` / `.tsx`; `tree-sitter-javascript` for `.js` / `.jsx`.
- Max AST depth: 5.
- JSX expressions are traversed only for routing components (e.g. React Router `<Route element=... />`); render trees are not deeply analyzed.

## Entry-point kinds detected

| Framework / surface | `entry_point.kind` | Detection signal |
|---|---|---|
| Express | `http-route` | `app.get/post/put/...('<path>', handler)` or router-level equivalents |
| Fastify | `http-route` | `fastify.route({ method, url, handler })` / `fastify.get(...)` |
| Koa + @koa/router | `http-route` | `router.get/post/...('<path>', handler)` |
| NestJS controller | `http-route` | `@Controller()` class with `@Get/@Post/...` decorated methods |
| Next.js App Router | `http-route` | `app/**/route.ts` exporting `GET` / `POST` / `PUT` / `DELETE` |
| Next.js Pages Router | `http-route` | `pages/api/**/*.ts` default export handler |
| Remix loader/action | `http-route` | `loader` / `action` exports in `routes/**` |
| AWS Lambda handler (TS/JS) | `http-route` if `APIGatewayProxyEvent`; `message-consumer` if `SQSEvent`/`KinesisEvent`; `scheduled-job` if `ScheduledEvent` | exported `handler` function whose first parameter type matches |
| GraphQL resolver | `graphql-resolver` | Apollo `resolvers = { Query: ..., Mutation: ... }`; Nexus / Pothos `t.field` |
| gRPC service impl | `grpc-method` | `server.addService(serviceDefinition, impl)` |
| BullMQ / agenda worker | `message-consumer` | `new Worker('<queue>', processor)` |
| node-cron / agenda scheduled | `scheduled-job` | `cron.schedule('<expr>', fn)` / `agenda.define(...)` |
| CLI entry | `cli-command` | `bin` field in `package.json`; `commander` / `yargs` command registrations |
| Vue / React / Svelte route | `ui-screen` | router config entries (`vue-router` `routes`, React Router `<Route>`, SvelteKit `+page.svelte`) |
| Service Worker | `event-publisher` (from UI side) | `self.addEventListener('fetch'/'push', ...)` in `sw.ts` |

## Inputs typing

- TypeScript: parameter types from function signatures; Zod / Yup / Joi schemas are first-class — when present, the schema is the source of truth for `inputs[].type` and `inputs[].validation`.
- JavaScript: no static types — `inputs[].type = "unknown"`, with hints from JSDoc `@param` if present.
- Express / Fastify request shape (`req.body`, `req.params`, `req.query`) is split into three named inputs.
- NestJS `@Body() dto: CreateUserDto` resolves to the DTO class fields with `class-validator` decorators captured as validation hints.

## Side-effect detection

- Persistence: Prisma (`prisma.<model>.create/update/delete`), TypeORM (`repository.save`), Sequelize (`model.create`), Mongoose (`Model.save`), Drizzle, Knex query builders ending in `.insert/.update/.delete`.
- HTTP clients: `fetch`, `axios`, `got`, `undici`, `node-fetch`, GraphQL clients (Apollo, urql).
- Message publishers: `kafkajs` `producer.send`, `aws-sdk` `SQS.sendMessage` / `SNS.publish` / `EventBridge.putEvents`, BullMQ `queue.add`.
- Filesystem and S3: `fs/promises` `writeFile`, `@aws-sdk/client-s3` `PutObjectCommand`.
- DOM side effects (UI): `localStorage`, `sessionStorage`, `cookie` writes, `history.pushState`.

## Cross-stack bridge hints

- `fetch("/api/v1/x")` literal in TS → `http-route` lookup in any unit (typical bridge to a Python FastAPI or Java Spring backend).
- `axios.create({ baseURL: process.env.X })` → environment-resolved; the bridge points to whatever `terraform-hcl` or `aws-serverless` defines for `X`.
- SDK calls (`SQSClient.send`, `SNSClient.publish`) → resolved against queue / topic ARNs in `aws-serverless` and `terraform-hcl` units.
- See [../cross_stack_bridges.md](../cross_stack_bridges.md) rows "HTTP URI literal", "AWS SDK resource ARN", "Environment variable indirection".

## Bug-patterns row pointer

See [../bug_patterns.md](../bug_patterns.md) — rows where column
`typescript-javascript` = `MUST-if-applicable`. Specifically: client-side
validation only (server-side missing), optimistic-UI desync, broken
back-button (SPA routing), double-submit, race windows on `useEffect`
dependency arrays, error swallowing in `try/catch` without rethrow,
timezone bugs from `new Date()` without TZ, money rounding from `Number`
vs `BigInt`/`Decimal.js`.

## Empty-input branch

If a unit is detected as `typescript-javascript` (manifest present) but
**zero** entry points are extracted (e.g. a type-only declarations
package), the unit is recorded in `coverage.md` with skip reason
`no-entry-points`. Pure type-declaration units (`*.d.ts` only) are
auto-detected and skipped silently with skip reason `out-of-scope`.
