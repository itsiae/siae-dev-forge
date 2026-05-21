# Bug-patterns matrix

This file is the **single source of truth** for hypothesis generation in
phase 5. It is structured as:

1. an **applicability matrix** (rows = patterns, columns = stacks; cells
   are `M` for `MUST-if-applicable`, `D` for `degraded` regex-only on
   `_generic`, `N` for `N/A`),
2. a **pattern catalog** with one entry per row (id, title, description,
   preconditions, functional manifestation, severity hint, related
   actor primitives, false-positive guards).

The runtime applies each pattern row to every analysis unit whose stack
column is `M` (or `D` with low-confidence flagging). A pattern fires
only when the precondition signals are present in the code; otherwise it
is silently skipped (NOT recorded as a finding, NOT recorded in
`hypotheses.json`).

## Applicability matrix

| ID | Pattern | java | kotlin | scala | ts-js | python | go | rust | swift | ruby | dotnet | flutter | tf-hcl | aws-sl | data | _gen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BP-001 | input-validation-gap | M | M | M | M | M | M | M | M | M | M | M | N | M | M | D |
| BP-002 | auth-inversion (functional) | M | M | M | M | M | M | M | M | M | M | N | M | M | N | D |
| BP-003 | state-race-window | M | M | M | M | M | M | M | M | M | M | M | N | M | M | D |
| BP-004 | idempotency-failure | M | M | M | M | M | M | M | N | M | M | M | N | M | M | D |
| BP-005 | retry-timeout-mismatch | M | M | M | M | M | M | M | M | M | M | M | M | M | M | D |
| BP-006 | partial-failure-not-handled | M | M | M | M | M | M | M | M | M | M | M | M | M | M | D |
| BP-007 | off-by-one-pagination | M | M | M | M | M | M | M | M | M | M | M | N | M | M | D |
| BP-008 | timezone-locale-bug | M | M | M | M | M | M | M | M | M | M | M | M | M | M | D |
| BP-009 | money-rounding | M | M | M | M | M | M | M | M | M | M | M | N | M | M | D |
| BP-010 | null-empty-edge | M | M | M | M | M | M | M | M | M | M | M | N | M | M | D |
| BP-011 | concurrent-mutation | M | M | M | M | M | M | M | M | M | M | M | N | M | M | D |
| BP-012 | missing-transactional-boundary | M | M | M | M | M | M | M | M | M | M | M | N | M | M | D |
| BP-013 | broken-back-button | N | N | N | M | N | N | N | M | N | N | M | N | N | N | N |
| BP-014 | double-submit | M | M | M | M | M | M | M | M | M | M | M | N | M | N | D |
| BP-015 | error-message-leakage | M | M | M | M | M | M | M | M | M | M | M | N | M | N | D |
| BP-016 | optimistic-ui-desync | N | N | N | M | N | N | N | M | N | N | M | N | N | N | N |
| BP-017 | feature-flag-collision | M | M | M | M | M | M | M | M | M | M | M | M | M | M | D |
| BP-018 | iac-functional-drift | N | N | N | N | N | N | N | N | N | N | N | M | M | N | N |
| BP-019 | webhook-replay-or-out-of-order | M | M | M | M | M | M | M | N | M | M | N | N | M | N | D |
| BP-020 | cache-invalidation-staleness | M | M | M | M | M | M | M | M | M | M | M | N | M | N | D |
| BP-021 | cursor-pagination-instability | M | M | M | M | M | M | M | M | M | M | M | N | M | M | D |
| BP-022 | dst-scheduler-skip | M | M | M | M | M | M | M | N | M | M | N | N | M | M | D |
| BP-023 | toctou-authorization-revoke | M | M | M | M | M | M | M | M | M | M | N | N | M | N | D |

Legend: `M` = MUST-if-applicable; `D` = degraded regex-only; `N` = N/A.

## Pattern catalog

### BP-001 — input-validation-gap

**Description.** An entry point accepts an input field whose value range,
length, format, or charset is not validated either at the framework
binding layer or in the handler body. A reasonable end-user can submit
a value that bypasses the implicit assumption made downstream.

**Precondition signals.**
- An input field of `String` / `unknown` / `dict` type used in a
  downstream call (DB query, HTTP call, file path construction) without
  passing through a validator (Bean Validation, pydantic, Zod, Yup, Joi,
  `class-validator`, `validator.v10`, Refined, etc.).
- A regex / length / range check missing on the input.

**Functional manifestation.** A QA submits an unexpectedly long string,
an empty string, a Unicode lookalike character, or a value with leading
/ trailing whitespace; the system either crashes, persists garbage,
returns a 500, or sends a malformed downstream call.

**Severity hint.** Major by default; escalate to Critical if the
downstream call is a financial transaction or auth decision.

**Related actor primitives.** `api-caller`, `ui-user`.

**False-positive guards.**
- If the framework's default binding rejects malformed JSON, an
  "unknown" field is NOT a finding by itself.
- If a downstream call wraps the input in a prepared statement / typed
  schema (e.g. SQLAlchemy `.filter(Model.x == input)`), SQL injection
  is not the manifestation — but type-coercion bugs may still be.

### BP-002 — auth-inversion (functional)

**Description.** An authorization decision is inverted by an
operator-controllable input, OR a route bypasses an expected auth
guard. Passes the **functional manifestation test**: a defined actor
performs an observable user journey and the auth weakness changes the
journey's outcome.

**Precondition signals.**
- A route handler that consults `request.user.id` against a resource
  owner BUT uses `==` against a value parsed from the request body (the
  user can lie about their own id).
- A middleware / guard that is registered conditionally (`if env != prod`).
- An IAM policy with `"Resource": "*"` and `"Action": "*"` granted to
  a role that handles user-facing traffic.
- A method-level `@PreAuthorize` / `@RequireAuth` annotation missing on
  a handler whose siblings have it.

**Functional manifestation.** A user A can access / modify a resource
owned by user B by manipulating an input. A non-admin user can perform
an admin-only action.

**Severity hint.** Blocker if it affects > 1% of users; Critical otherwise.

**Related actor primitives.** `api-caller`, `ui-user`.

**False-positive guards.** SAST-only findings without an observable user
journey are excluded by the functional manifestation test.

### BP-003 — state-race-window

**Description.** Two operations read shared state, mutate it, and write
it back without a lock, optimistic version, or transactional boundary.
The race window is observable when concurrent users / requests exist.

**Precondition signals.**
- Read-modify-write on a row without `SELECT ... FOR UPDATE` or
  optimistic version column.
- A check-then-act sequence: `if !exists then create` without unique
  constraint.
- Mutation of a shared in-memory map / cache without synchronization.

**Functional manifestation.** Two simultaneous bookings of the same
resource succeed; a duplicate user is created when two parallel
sign-ups race; a counter is decremented below zero.

**Severity hint.** Critical (default) if the resource is user-visible
state (orders, bookings, inventory). Major otherwise.

**Related actor primitives.** `api-caller`, `ui-user`, `event-publisher`.

**Reproduction-rate target.** This is the `race_window` category — ≥ 80%
over 5 attempts is acceptable.

### BP-004 — idempotency-failure

**Description.** A side-effect-producing operation has no idempotency
token, no natural idempotency from the data, and is invoked from a
retry-capable source.

**Precondition signals.**
- A message-consumer handler that calls a side effect WITHOUT consulting
  an idempotency cache / `Idempotency-Key` header.
- A retry policy (Spring Retry, AWS Lambda async retry, `tenacity`,
  Polly) wrapping the same side effect.
- An HTTP POST handler with no idempotency key support, exposed to
  network retries.

**Functional manifestation.** A retry produces a duplicate order, a
duplicate notification, a double charge.

**Severity hint.** Critical for financial or notification side effects;
Major for inventory or counters.

**Related actor primitives.** `api-caller`, `event-publisher`.

### BP-005 — retry-timeout-mismatch

**Description.** The caller's timeout is shorter than the callee's
worst-case execution, OR the retry budget is configured in a way that
causes cascading failure (no jitter, no exponential backoff).

**Precondition signals.**
- HTTP client timeout < known downstream latency (DB query timeout,
  Lambda max execution).
- Retry count > 0 without backoff configuration.
- `socket.timeout` in seconds shorter than the load balancer's idle
  timeout.

**Functional manifestation.** Under load, the user sees 504 Gateway
Timeout; client retries amplify the failure into a partial outage.

**Severity hint.** Major.

**Related actor primitives.** `api-caller`, `observer`.

### BP-006 — partial-failure-not-handled

**Description.** A multi-step operation persists step 1 successfully
and fails on step 2 without compensating step 1 OR raising a visible
error.

**Precondition signals.**
- Two side effects in sequence within a non-transactional handler.
- A `try` block catching a broad exception and swallowing it without
  reverting prior writes.
- A `saga` pattern declared but missing compensation handlers for one
  step.

**Functional manifestation.** A user account exists in the auth system
but not in the profile system, and a subsequent login fails.

**Severity hint.** Critical when it creates orphan state visible to
users.

**Related actor primitives.** `api-caller`, `event-publisher`.

### BP-007 — off-by-one-pagination

**Description.** A pagination implementation skips the last record,
double-counts a boundary record, or fails on edge inputs (`offset = 0`,
`limit = 0`, `limit > total`).

**Precondition signals.**
- `OFFSET ?` / `LIMIT ?` without a stable `ORDER BY` clause.
- Cursor-based pagination using the last item's id without uniqueness
  guarantee.
- `for i in range(len(arr))` patterns combined with slicing.

**Functional manifestation.** A user scrolling a list misses items at
page boundaries, or sees a duplicate at the top of each page.

**Severity hint.** Major.

**Related actor primitives.** `api-caller`, `ui-user`.

### BP-008 — timezone-locale-bug

**Description.** A timestamp or locale-sensitive value (currency, date
formatting, sort order) is handled without explicit timezone or locale,
producing user-visible inconsistency.

**Precondition signals.**
- `new Date()` / `datetime.now()` / `time.Now()` without TZ.
- String comparison on dates / numbers without locale-aware collation.
- Currency display using the server's locale rather than the user's.

**Functional manifestation.** A user in Tokyo sees a Monday event on
Sunday; an Italian user sees `1,000.00` displayed as `1.000,00`
inverted.

**Severity hint.** Major.

**Related actor primitives.** `ui-user`, `api-caller`.

### BP-009 — money-rounding

**Description.** Monetary arithmetic performed in floating-point or
with implicit truncation, causing user-visible discrepancy.

**Precondition signals.**
- `Number` / `float` / `f64` arithmetic on currency values.
- Banker's-rounding behavior inconsistent across endpoints.
- Conversion between currencies without rounding policy declared.

**Functional manifestation.** A summed invoice differs by a cent
between the user's display and the server's record.

**Severity hint.** Critical if it affects the user's billing;
Major otherwise.

**Related actor primitives.** `api-caller`, `ui-user`, `observer`.

### BP-010 — null-empty-edge

**Description.** A code path crashes or misbehaves on empty input
(empty string, empty list, null, undefined) when a user can provide
that empty input.

**Precondition signals.**
- Direct deref of an Optional / Nullable without a default branch.
- `arr[0]` access without bound check.
- Regex match `.group(1)` without checking for match success.

**Functional manifestation.** A user submits an empty form / array /
optional field and sees a 500 or a crash.

**Severity hint.** Major.

**Related actor primitives.** `api-caller`, `ui-user`.

### BP-011 — concurrent-mutation

**Description.** A long-running operation reads state, the user
concurrently modifies it via another action, and the long-running
operation overwrites the user's intent.

**Precondition signals.**
- A "save draft" / "submit" flow without optimistic concurrency.
- A workflow that reads aggregate state at start and writes at end
  without revalidating.

**Functional manifestation.** A user updates a field while a background
sync is in progress; the user's update is silently overwritten.

**Severity hint.** Critical when it loses user data.

**Related actor primitives.** `ui-user`, `api-caller`, `batch-runner`.

### BP-012 — missing-transactional-boundary

**Description.** A handler performs multiple database writes that
logically must commit or roll back together, but no transaction wraps
them.

**Precondition signals.**
- Two ORM `save()` calls without enclosing `with session.begin()` /
  `@Transactional` / `unit of work`.
- A cross-table denormalized update missing transactional grouping.

**Functional manifestation.** A failure between writes leaves the
system in an inconsistent state visible to the user (e.g. an order
exists but the order items don't).

**Severity hint.** Critical.

**Related actor primitives.** `api-caller`, `db-operator`.

### BP-013 — broken-back-button

**Description.** A single-page application or mobile screen mishandles
browser / OS back navigation: state is lost, the user lands on a
different URL than expected, or a modal becomes orphaned.

**Precondition signals.**
- `history.pushState` without matching `popstate` handler.
- React Router / Vue Router / Flutter Navigator without restoration
  logic for deep states.
- Modal opening that doesn't push a history entry.

**Functional manifestation.** A user fills a form, presses back, returns
to the form, and finds the fields cleared.

**Severity hint.** Major.

**Related actor primitives.** `ui-user`.

### BP-014 — double-submit

**Description.** A form / action button can be clicked twice in rapid
succession before the first request completes, producing two side
effects.

**Precondition signals.**
- A submit button without disable-on-click logic.
- No idempotency token from the client.
- No server-side dedupe on a `(user_id, action, timestamp_minute)`
  basis.

**Functional manifestation.** A user double-clicks "Pay" and is charged
twice.

**Severity hint.** Critical for financial actions; Major otherwise.

**Related actor primitives.** `ui-user`, `api-caller`.

### BP-015 — error-message-leakage

**Description.** An error message returned to the user contains
information that should not be exposed: stack trace, internal IP,
SQL fragment, third-party token, user ID of another user.

**Precondition signals.**
- A global error handler that returns `str(exception)` or `error.stack`.
- A 500 response body that includes server-side detail.
- A log line interpolated with sensitive variables that the response
  also includes.

**Functional manifestation.** A user submits a malformed input and
sees a SQL fragment / a colleague's email in the error page.

**Severity hint.** Major (escalate to Critical if the leaked data is
PII or credentials).

**Related actor primitives.** `api-caller`, `ui-user`.

### BP-016 — optimistic-ui-desync

**Description.** The UI updates as if a server action succeeded but the
server actually rejected or partially completed it, leaving the UI in
a state that disagrees with the persisted truth.

**Precondition signals.**
- A client-side state mutation BEFORE awaiting the server response.
- No rollback handler on the failure branch.
- A WebSocket / SSE update path that contradicts the optimistic state
  without reconciliation.

**Functional manifestation.** A user "likes" a post, sees the count go
up, reloads the page, the like is gone.

**Severity hint.** Major.

**Related actor primitives.** `ui-user`.

### BP-017 — feature-flag-collision

**Description.** Two feature flags or two values of the same flag are
read in different code paths within the same request, producing an
incoherent user experience.

**Precondition signals.**
- A feature flag evaluated in middleware AND independently in a
  handler.
- Two different flag names that gate the same feature in different
  layers.
- A flag stored in the client AND on the server with no reconciliation.

**Functional manifestation.** A user sees a button (server flag ON) but
clicking it returns "feature unavailable" (handler flag OFF).

**Severity hint.** Major.

**Related actor primitives.** `ui-user`, `api-caller`.

### BP-018 — iac-functional-drift

**Description.** An IaC change (Terraform, CloudFormation, CDK)
modifies a runtime functional contract — a route disappears, an IAM
permission is removed, a queue's visibility timeout changes — in a way
that a user can observe.

**Precondition signals.**
- `aws_security_group_rule` removed for a port still used by a
  documented user journey.
- `aws_apigatewayv2_route` removed without a matching deprecation in
  the handler code.
- KMS key policy denying a role that a Lambda still assumes.
- `aws_lambda_function.timeout` decreased below the documented worst
  case.

**Functional manifestation.** A user journey that worked yesterday
returns 403 / 504 today.

**Severity hint.** Critical when it breaks a documented user journey.

**Related actor primitives.** `iac-operator`, `api-caller`, `ui-user`.

### BP-019 — webhook-replay-or-out-of-order

**Description.** A handler that processes provider webhook events
(Stripe, GitHub, Shopify, Twilio, etc.) accepts the same event id twice
OR processes events in a causally-invalid order because it does not
verify the prior event in the chain. Out-of-order delivery is a normal
property of at-least-once webhook providers; the handler must defend.

**Precondition signals.**
- A webhook handler that processes events of type `*.completed`,
  `*.captured`, `*.paid`, `*.succeeded` without checking whether the
  causally-prior event (`*.authorized`, `*.created`, `*.requires_action`)
  has already been seen for the same correlation id.
- No idempotency-key store (Redis `SET NX` with TTL, DB unique index on
  `event_id`, idempotency-tokens table) consulted before applying the
  side effect.
- No use of an outbox-pattern table to serialise state transitions.

**Functional manifestation.** A `PaymentCaptured` event arrives before
`PaymentAuthorized` due to network jitter; the system records a captured
payment that has no authorization on record. Or: the same `*.completed`
event is replayed by the provider and the side effect (mail, charge,
provisioning) fires twice.

**Severity hint.** SEV-2 by default; escalate to SEV-1 when the
downstream side effect is financial AND > 10% of transactions are
exposed.

**Related actor primitives.** `event-publisher`, `observer`.

**False-positive guards.**
- A handler that explicitly stores `event.id` in a unique-indexed table
  and short-circuits on hit is NOT a finding (idempotency present).
- Providers that guarantee in-order delivery (rare; document the
  provider's docs link in `oracle_inventory.md`) cancel the
  out-of-order half of this pattern but keep the replay half.

### BP-020 — cache-invalidation-staleness

**Description.** Application logic updates a resource but does not
invalidate / update the correlated cache layer(s) — CDN edge, Redis
cache-aside, Service Worker cache, in-process LRU, ETag/Last-Modified
headers — so users continue to observe stale state for the residual
TTL.

**Precondition signals.**
- A write endpoint (`POST` / `PUT` / `PATCH` / `DELETE`) on a resource
  AND a read endpoint (`GET`) on the same resource where the write does
  NOT emit an explicit invalidation (CDN `PURGE`, `cache.del()`,
  `cacheStorage.delete()`, surrogate-key tag invalidation).
- `Cache-Control: stale-while-revalidate=<N>` set without `max-age=0`.
- Service Worker `Cache.put()` keyed by request URL without versioning.

**Functional manifestation.** A user updates their profile; the CDN
(or another user's Service Worker, or a Redis read replica) still serves
the previous version for minutes/hours; other users observe obsolete
data.

**Severity hint.** SEV-3 in general; SEV-2 when the staleness window is
> 5 minutes AND the data class is auth / financial / PII.

**Related actor primitives.** `ui-user`, `api-caller`.

**False-positive guards.**
- Caches with explicit `max-age=0` or per-request `Vary: Cookie` are
  intentionally not invalidated server-side; mark as PARTIAL only.
- Read-through caches with versioned asset URLs (filename hash) do not
  match this pattern.

### BP-021 — cursor-pagination-instability

**Description.** An API that paginates via opaque cursor orders results
by a non-unique column without a tie-breaker, so the cursor can skip
records or return duplicates across pages when two records share the
sort value.

**Precondition signals.**
- A SQL/ORM query of the form `ORDER BY <col> [DESC]` where `<col>` is
  NOT the primary key and the query also has `LIMIT <n>`.
- A cursor encoding only the last-observed value of `<col>` (no `id`,
  no row uuid).
- Use of offset-based pagination (`OFFSET <n>`) on a mutable table.

**Functional manifestation.** A user paging through `/orders?cursor=...`
sees the same order twice on two consecutive pages, or misses an order
that has the same `created_at` as the cursor boundary.

**Severity hint.** SEV-3 by default; SEV-2 when the missed record is
auth-relevant or financial.

**Related actor primitives.** `api-caller`, `ui-user`.

**False-positive guards.**
- A query with `ORDER BY created_at DESC, id DESC` (composite cursor)
  is correctly tie-broken; not a finding.
- Keyset pagination over a strictly-monotonic primary key (`id > ?`) is
  correctly stable; not a finding.

### BP-022 — dst-scheduler-skip

**Description.** A scheduled job uses a cron expression on **local
time** in a timezone with DST, and the configured hour does not exist
on the spring-forward day; the job is silently skipped.

**Precondition signals.**
- A cron string with a fixed hour in `00:00`–`03:59` declared in code
  that also configures a non-UTC timezone (`Europe/*`, `America/*`,
  `Australia/*`).
- `cron.schedule(..., { timezone: "Europe/Rome" })`, Spring `@Scheduled
  (cron = "0 0 2 * * *", zone = "Europe/Rome")`, APScheduler
  `CronTrigger(hour=2, timezone="Europe/Rome")`, Quartz with a
  timezone-aware trigger.
- `setInterval(...)` / `setTimeout(...)` whose delay is computed from
  local-time wall clock (e.g. `(2 - currentHour) * 3600 * 1000`).

**Functional manifestation.** On the spring-forward Sunday (last Sunday
of March in EU; second Sunday of March in US), the `02:00` job does NOT
fire. Users observe missing emails / reports / aggregations exactly on
that day. The fall-back day (autumn) causes the inverse symptom in the
same family: the job fires twice.

**Severity hint.** SEV-3 by default; SEV-2 when the job underpins a
financial reconciliation or a compliance deadline.

**Related actor primitives.** `scheduler`, `observer`.

**False-positive guards.**
- Schedules expressed in UTC are not affected; not a finding.
- Schedulers that explicitly handle DST ambiguity (e.g. APScheduler
  emits a warning and shifts) require manual inspection of the warning
  channel; mark as PARTIAL when the warning is silenced.

### BP-023 — toctou-authorization-revoke

**Description.** A multi-step flow checks permissions once at the
beginning (TOCHECK) and assumes the grant remains valid through every
subsequent operation (TOUSE), even when the flow spans seconds /
minutes / multiple HTTP requests / asynchronous jobs.

**Precondition signals.**
- Authorization function (`can_user_do_X(user_id)`, `@PreAuthorize`,
  `requireRole("admin")`) called once before a sequence of operations
  that lasts > 1 s OR spans multiple requests OR enqueues async work.
- Chunked upload / chunked download endpoints where the auth check is
  on `start_upload` and subsequent `upload_chunk` calls do not re-check.
- Long-running batch operations where the initiating request validates
  the role but the worker that consumes the queue does not.
- JWT-based auth without a revocation check (no Redis blacklist, no
  short TTL, no introspection callback).

**Functional manifestation.** A user begins an upload of 10 chunks; an
admin revokes the user's token after chunk 3; chunks 4–10 are still
accepted because the auth gate was at the start of the flow. Or: a
batch reconciliation initiated by user A continues to run after A's
account is disabled.

**Severity hint.** SEV-2 by default; SEV-1 when the revoked permission
is auth-bypass-class (impersonation, tenant escape).

**Related actor primitives.** `api-caller`, `ui-user`, `scheduler`.

**False-positive guards.**
- Endpoints with sub-second wall-clock and single-request scope do not
  match this pattern.
- Token-introspection middleware that runs on every chunk / every
  consumer step closes the TOCTOU window; not a finding.
- Short JWT TTL (< 60 s) plus refresh-on-revocation is a partial
  mitigation; surface as PARTIAL rather than VERIFIED.

## Adding a new pattern

To add a new pattern (minor semver bump):

1. Append a new row to the matrix above with an `M` / `D` / `N` value
   in every column. Missing columns are an error.
2. Add a `### BP-NNN — slug` section in the catalog with all the
   required fields.
3. Update the runtime by re-running the unit tests in `eval/` (the
   golden set ensures coverage and false-positive rates remain stable).
4. No edit to `SKILL.md` is required.
