# Pipeline internals

Load-on-demand reference: implementation detail for each phase of the
nine-step pipeline declared in `SKILL.md`. Read this file when you need
to know what a phase produces, what stops it, what its empty-input
fallback is, and which scripts it invokes.

The pipeline has nine ordered phases plus two sub-phases (2.5 and 7.5).
Each phase has canonical artifacts in the output directory, a closed set
of stop triggers, and an explicit empty-input branch.

## Phase 0 — Preflight and mode detection

Runs `scripts/preflight.sh` to confirm Bash 4 or POSIX fallback, Python 3.9,
and either jq 1.6 or the bundled Python helper in `scripts/_json_helpers.py`.
Detects whether `.git` is present (otherwise the grounding policy uses a
content hash and sets `vcs: "none"`), whether the working tree is dirty
(captured per file), and whether the clone is shallow (captured as a
warning). Detects mode and writes the first entry of `audit_log.jsonl`.

The phase acquires the run lock via `scripts/run_lock.py acquire <output_dir>`.
A non-zero exit code from `run_lock.py acquire` MUST abort the run: rc=1
means another live process holds the lock for the same output_dir; rc=2
means an IO error. The orchestrator MUST also wire `scripts/run_lock.py
release <output_dir>` on the EXIT / SIGINT / SIGTERM trap of its driver
shell so the lock is removed on both normal termination and aborts. Stale
locks (JSON `pid` no longer alive on the same host) are auto-removed by
`acquire` with a stderr warning.

Mode dispatch: `scripts/run_lock.py dispatch <mode> <event>` returns the
required action for a given runtime event (`PAUSE`, `CONTINUE`, `DEGRADE`).
See `references/runtime_modes.md` for the full event-to-action matrix.

## Phase 1 — Inventory and stack detection

Walks each root, applies the default and operator-supplied exclusions, and
identifies analysis units. Stack detection consults the manifest
fingerprints listed in `references/stacks/INDEX.md`: among them `pom.xml`,
`build.gradle[.kts]`, `package.json`, `pyproject.toml`, `go.mod`,
`Cargo.toml`, `pubspec.yaml`, Terraform sources, SAM and CDK templates,
serverless framework files, Step Functions definitions, dbt and Airflow
manifests, Helm charts, Kubernetes manifests, OpenAPI and GraphQL schemas,
Gemfile, `.csproj`, `build.sbt`, and `mix.exs`. The `max_files_per_unit`
cap of ten thousand applies; over-cap files are listed in `coverage.md`
with reason `file_count_cap`. The phase emits `inventory.json`. Empty input
branch: when no manifest is detected, the phase emits `inventory.json` with
an empty unit list and the runtime fails fast with a suggestion to pass an
explicit manifest hint.

## Phase 2 — Dependency graph and closure check

Resolves internal versus external dependencies and flags every reference to
a sibling repository, service, or module that is not in `args.roots`.
Examples include Terraform remote state and module sources pointing to
external buckets, Step Functions task ARNs targeting lambdas not in the
roots, gRPC and REST clients with base URLs that match internal naming,
shared protobuf schemas, internal-scope npm and Maven packages, and dbt
`ref()` or `source()` references across projects. The phase builds
`boundary_identifier_registry.json` keyed by (kind, identifier) and emits
`dependency_closure.md` describing what is missing, why it matters for
functional analysis, and which extra roots would close the graph. The STOP
decision runs before subagent dispatch: in interactive mode the runtime
pauses on a closure gap that touches a critical-path entry point; in strict
mode it flags low confidence and continues; in report-only mode it records
the gap and continues.

## Phase 2.5 — Oracle Inventory

Before any pattern matching, enumerate and classify the oracles available
in the repository. See SKILL.md "Oracle inventory" section for the rank
table (A/B/C) and the impact on hypotheses.json (`oracle_status`,
`oracle_ref`).

## Phase 3 — Entry point cartography

Stack-dispatched extraction populates a canonical record per entry point
containing identifier, unit, kind, actor primitive, trigger, inputs,
downstream calls, side effects, and source ref with file, line range, SHA,
and dirty flag. Entry-point kinds are enumerated and stable.

The phase fans out to per-boundary subagents through the Task tool. The
full contract — prompt template, JSON Schema (`SubagentResult` v1.0),
dedup-key strategy, and merge algorithm — lives in
`references/subagent_contract.md` and is the single source of truth.

Every subagent MUST receive `schema_version: "1.0"` in its prompt and
return JSON validated against the `SubagentResult` schema before merge.
The orchestrator does not re-read unit code; it merges subagent return
payloads via the deterministic `dedup_key` defined in the contract and
reconciles cross-unit findings via shared boundary identifiers.

The hard cap is **8 subagents in parallel**. When the runtime does not
support parallel `Task` invocations, the orchestrator falls back to
**sequential dispatch** with the identical prompt, schema, and merge —
trading wall-clock time for compliance. The `max_entry_points_per_unit`
cap applies; overflow is recorded in `open_questions.md` ranked by
descending complexity score. The phase emits `entry_points.json`. Empty
input branch: when no entry points exist, downstream phases are skipped
and the runtime emits a `qa_report.md` whose status is `no_entry_points`.

Cross-stack payloads consumed by Phase 3 subagents are produced by
`scripts/generate_payloads.py` (see contract section "Payloads dir —
producer"). When the payloads dir is absent or empty,
`scripts/list_entry_points.py` prints a warning on stderr and continues
with an empty array; it MUST NOT fail silently.

## Phase 4 — Functional call and data flow reconstruction

For each entry point the runtime builds a directed functional flow from
input through validations, branches, external calls, persisted state, and
response or side effect. Cross-unit hops are resolved via the boundary
registry and the cross-stack bridge table in
`references/cross_stack_bridges.md`, which governs language-agnostic
identifier resolution (for example a TypeScript `fetch("/v1/x")` matched
against a Python `@app.post("/v1/x")`). The analyzer uses bounded AST (tree
sitter depth at most five) where a grammar exists, otherwise a regex
fallback, augmented by at most twenty Grep round trips per entry point.
Beyond that budget the analyzer degrades to grep-only context and notes
the degradation in `coverage.md`. Per-unit graphs are written to
`flow_graphs/<unit>.json`.

## Phase 5 — Bug hypothesis generation

Applies the stacked pattern matrix in `references/bug_patterns.md`. Rows
are patterns, columns are stacks, cells are `MUST-if-applicable` or `N/A`.
A pattern fires for a stack only when the precondition is surfaced by that
stack. Mandatory categories include input validation gaps, authentication
and authorization inversions that pass the functional manifestation test,
state inconsistency and race windows, idempotency failures, retry and
timeout pathologies, partial failure handling, off-by-one and pagination,
timezone and locale, money and rounding, null and empty edge inputs,
concurrent mutation, missing transactional boundaries, broken back-button,
double-submit, error-message leakage, optimistic-UI desync, feature flag
collisions, and IaC misconfigurations that drift the runtime functional
contract. Hypotheses are persisted to `hypotheses.json` regardless of
feasibility outcome.

## Phase 6 — Path feasibility filter

Each hypothesis is challenged against the actual code paths discovered in
phase 4. The filter identifies the shared mutable state touched by the
hypothesis, extracts the minimal code slice from entry point to that
state, enumerates the path predicates encountered on the slice, and
verdicts the hypothesis feasible only when an input exists that satisfies
all predicates and at least one actor primitive can reach the entry point.

The filter is implemented by `scripts/path_feasibility.py` (glob + keyword
matching, no AST). Discarded hypotheses remain in `hypotheses.json` with
the verdict reason. Empty input branch: when all hypotheses are filtered
out, the runtime emits a `qa_report.md` whose status is
`all_hypotheses_filtered`.

## Phase 7 — QA-style reproduction synthesis

For each surviving hypothesis the runtime emits a canonical QA test case
with finding id, back-link to the entry-point id from phase 3, title,
severity assigned through `references/severity_rubric.md` with mandatory
citation of the matched rubric row, preconditions, steps (one actor
primitive per step from the eight allowed primitives documented in
`references/repro_voice_guide.md`), expected and actual result, redacted
evidence excerpt, a one-sentence fix direction, a reproduction-rate
target (eighty percent for race-window categories, ninety-five percent
for the rest), and any cross-unit boundary observations. The schema
mapping from canonical record to QA case is fixed in
`references/qa_report_json_schema.md`.

## Phase 7.5 — User-journey clustering

Findings are clustered into deterministic user journeys keyed by the
tuple (primary actor primitive, entry point kind, top resource id). Each
journey receives a stable ordinal of the form `J-NNN`. Findings without
enough signal land in journey `J-000-misc`. Clustering is performed only
on findings retained from phase 7; the algorithm is deterministic and
re-runnable.

## Phase 8 — Report assembly

The runtime assembles two artifacts side-by-side:

1. **`qa_report.json`** — schema-stable output emitted directly by the
   runtime. This is the canonical, diff-able artifact. The schema is
   declared in `references/qa_report_json_schema.md` (aggregate of the
   per-subagent `SubagentResult` schema plus report-level metadata).
2. **`qa_report.md`** — markdown rendering of `qa_report.json` produced by
   `scripts/render_qa_report.py`. The rendering is deterministic given the
   same JSON: header timestamp is taken from `qa_report.json:generated_at`,
   never from `datetime.now()`. The `.md` MUST NOT be used for byte-a-byte
   diff in CI because free-text fields (title, preconditions, steps,
   suggested_fix_direction) vary across LLM runs.

The hallucination guard MUST run on `qa_report.json` between emission and
rendering. See `references/hallucination_guard.md` for the contract.

Findings are grouped by journey then severity, capped at the configured
maximum (default fifty). Overflow goes to `qa_report_overflow.md` and the
primary report carries an index page listing all findings with link.
`coverage.md` declares which entry points were analyzed and which were
skipped, with skip reason drawn from a closed enumeration (time-budget,
dead-code, generated-code, third-party, no-source-access, unparseable,
out-of-scope, file-count-cap, ep-count-cap). `open_questions.md` lists
items that need runtime evidence. `run_manifest.json` records semantic
version, model id, mode, scope hash, phase durations, finding counts by
severity, exit status, and the network-call counter (which must be zero).
The lock is released. Output language is the value of `args.lang`,
defaulting to English; when `it` is selected the narrative content is
translated while schema field names remain English.
