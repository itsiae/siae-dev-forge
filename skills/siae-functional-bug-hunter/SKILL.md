---
name: siae-functional-bug-hunter
description: >
  Static, multi-repo, cross-stack functional bug hunter. Ingests one or more
  repository roots, detects when additional repos must be pulled in to close
  the dependency graph, generates bug hypotheses from a stack-aware pattern
  matrix, filters them by path feasibility, and emits a deterministic
  qa_report.md grouped by user-journey with minimally-flaky reproduction
  recipes voiced for a human manual QA tester (ISTQB Foundation + 2 years
  experience). Supports Java, TypeScript/JavaScript, Python, Go, Rust, Kotlin,
  Swift, Ruby, .NET/C#, Scala, Flutter/Dart, Terraform/HCL, AWS serverless
  (SAM/CDK/SFN/EventBridge), and data platforms (dbt/Airflow/Spark/SQL), with
  a generic-fallback profile for everything else. Invocation is manual only,
  via the explicit slash command /siae-functional-bug-hunter. No automatic
  hooks, no session-start activation, no natural-language auto-trigger.
  Runtime supports three modes: interactive (TTY, may pause for missing
  scope), strict (CI, never pauses), and report-only (low-confidence partial
  allowed). Excludes SAST-only findings unless they pass the functional
  manifestation test, and excludes generation of automated test code.
allowed-tools: Read, Grep, Glob, Bash, Task
min_model: claude-opus-4-7
skill_semver: 1.1.0
---

# functional-bug-hunter

This skill turns one or more source repositories into a deterministic QA
report describing functional bugs that a human manual tester could plausibly
reproduce. It reads code, manifests, infrastructure-as-code, and event
wiring; it does not execute the application and never writes to the target
repositories. The analysis is framework-agnostic at the core and
stack-specific only at the parsing and entry-point extraction boundary,
dispatched through `references/stacks/INDEX.md`. The report is grounded:
every claim cites a file, a line range, a commit SHA, and a dirty flag.
Ungroundable hypotheses are quarantined in `hypotheses.json` and never
promoted to the primary `qa_report.md`.

## How to invoke

Invocation is manual only. The skill runs when an operator types its slash
command and supplies a JSON argument that respects the Inputs Contract
below. There are no automatic hooks, no session-start activation, and no
natural-language auto-trigger. If the skill is mentioned in conversation
without the slash command, it must not fire. The operator is the only
trigger. Example invocation:

```
/siae-functional-bug-hunter {"roots":["/abs/path/repoA","/abs/path/repoB"],"mode":"interactive","lang":"en"}
```

## When NOT to use

Do not use this skill to generate automated test code in any framework
(Playwright, Cypress, JUnit, pytest, Selenium, Robot Framework, or others);
to report SAST or CVE findings that do not pass the functional manifestation
test defined in `references/qa_inclusion_tree.md`; to audit performance,
load, accessibility, or user experience; to write to or refactor the target
repository; to replace a runtime QA session against a deployed environment.
For those needs, use a different skill or a manual workflow.

## Inputs contract

The skill accepts a single JSON object. The runtime validates inputs before
phase 0 and refuses ill-formed arguments.

```json
{
  "roots": ["/abs/path/repoA", "/abs/path/repoB"],
  "mode": "interactive | strict | report-only",
  "output_dir": "/abs/path/optional",
  "max_wallclock_minutes": 30,
  "max_entry_points_per_repo": 50,
  "lang": "en | it",
  "skip_paths": ["**/generated/**", "**/legacy/**"]
}
```

Each `roots[i]` is an absolute path on the local filesystem; remote URIs are
out of scope for v1. Symlinks are followed once and never transitively. The
default exclusion set covers `.git/`, `node_modules/`, `vendor/`, `target/`,
`dist/`, `build/`, `.terraform/`, and `__pycache__/`. Files larger than five
megabytes are sampled (first two hundred lines) and flagged. Submodules must
appear as separate entries in `roots` to be analyzed; otherwise they are
recorded in `dependency_closure.md` as unresolved boundaries. Monorepo
detection (Nx, Turborepo, Bazel, Gradle multi-project, Go workspace) splits
a single root into multiple analysis units according to
`references/repo_granularity.md`; the subagent fan-out described in phase 3
operates on those units, not on raw `roots`. If `mode` is absent, the
runtime picks `interactive` on TTY sessions and `strict` on non-TTY
sessions. If `output_dir` is absent, the runtime writes to
`.fbh/runs/<ISO8601>-<scope_hash>/` next to the first root, where
`scope_hash` is the SHA-256 of the sorted roots list.

## Runtime modes

| mode | TTY behavior | STOP behavior | typical use |
|---|---|---|---|
| interactive | may pause and ask the user | PAUSE on STOP triggers | exploratory analysis on a developer workstation |
| strict | never pauses | STOP triggers translate to FAIL markers in `run_manifest.json`; continues to phase 8 with disclaimer | CI, batch, scheduled jobs |
| report-only | never pauses | STOP triggers logged, run continues; confidence flagged as `low_partial`, gaps listed in `open_questions.md` | first scan of an unfamiliar codebase, where partial signal is better than no signal |

A run is locked through `.fbh/run.lock` (PID plus ISO8601 timestamp).
Parallel runs against the same `output_dir` are refused. Parallel runs
against distinct `output_dir` are safe.

## Pipeline overview

The pipeline has nine ordered phases. Each phase has canonical artifacts in
the output directory, a closed set of stop triggers, and an explicit
empty-input branch.

### Phase 0 — Preflight and mode detection

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

### Phase 1 — Inventory and stack detection

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

### Phase 2 — Dependency graph and closure check

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

### Phase 2.5 — Oracle Inventory

Before any pattern matching, enumerate and classify the oracles
available in the repository.

#### Oracle Rank

| Rank | Oracle type                  | Examples                                              | Reliability |
|------|------------------------------|-------------------------------------------------------|-------------|
| A    | Formal specification         | OpenAPI/Swagger YAML, Protobuf .proto, JSON Schema, SQL schema with constraints | High — source of truth |
| B    | Test and contract            | Unit tests, integration tests, acceptance criteria in commit/PR, contract tests (Pact) | Medium-high — reveals intent |
| C    | Informal documentation       | README, comments, Javadoc, wikis linked from the repo  | Medium — must be cross-checked against code |

#### Output: oracle_inventory.md

The phase emits `oracle_inventory.md` containing:
- a table of discovered oracles (file path, rank, estimated coverage);
- a list of oracles expected but absent (e.g. "no OpenAPI spec found for
  the gateway").

#### Impact on hypotheses.json

Each entry in `hypotheses.json` MUST include two additional fields:
- `oracle_status`: one of `VERIFIED` (oracle rank A/B seen during this
  session), `PARTIAL` (oracle rank C), or `HYPOTHESIS` (no oracle, inferred
  from code).
- `oracle_ref`: file path plus line of the oracle used, or `null` when
  `oracle_status` is `HYPOTHESIS`.

Hypotheses with `oracle_status: HYPOTHESIS` are NOT discarded — they are
persisted in `hypotheses.json` as a weak signal for subsequent runs.

### Phase 3 — Entry point cartography

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

### Phase 4 — Functional call and data flow reconstruction

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

### Phase 5 — Bug hypothesis generation

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

### Phase 6 — Path feasibility filter

Each hypothesis is challenged against the actual code paths discovered in
phase 4. The filter identifies the shared mutable state touched by the
hypothesis, extracts the minimal code slice from entry point to that
state, enumerates the path predicates encountered on the slice, and
verdicts the hypothesis feasible only when an input exists that satisfies
all predicates and at least one actor primitive can reach the entry point.
Discarded hypotheses remain in `hypotheses.json` with the verdict reason.
Empty input branch: when all hypotheses are filtered out, the runtime
emits a `qa_report.md` whose status is `all_hypotheses_filtered`.

### Phase 7 — QA-style reproduction synthesis

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

### Phase 7.5 — User-journey clustering

Findings are clustered into deterministic user journeys keyed by the
tuple (primary actor primitive, entry point kind, top resource id). Each
journey receives a stable ordinal of the form `J-NNN`. Findings without
enough signal land in journey `J-000-misc`. Clustering is performed only
on findings retained from phase 7; the algorithm is deterministic and
re-runnable.

### Phase 8 — Report assembly

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

The hallucination guard (`scripts/hallucination_guard.py`) MUST run on
`qa_report.json` between emission and rendering; a non-zero exit code
blocks the pipeline. Findings are grouped by journey then severity,
capped at the configured maximum (default fifty). Overflow goes to
`qa_report_overflow.md` and the primary report carries an index page
listing all findings with link. `coverage.md` declares which entry
points were analyzed and which were skipped, with skip reason drawn from
a closed enumeration (time-budget, dead-code, generated-code,
third-party, no-source-access, unparseable, out-of-scope, file-count-cap,
ep-count-cap). `open_questions.md` lists items that need runtime
evidence. `run_manifest.json` records semantic version, model id, mode,
scope hash, phase durations, finding counts by severity, exit status,
and the network-call counter (which must be zero). The lock is released.
Output language is the value of `args.lang`, defaulting to English; when
`it` is selected the narrative content is translated while schema field
names remain English.

## Stop conditions

| trigger | interactive | strict | report-only |
|---|---|---|---|
| dependency_closure incomplete on critical_path | PAUSE+ask | mark low-confidence, continue | mark + continue |
| findings count > 5 critical OR > 1 blocker (post-phase-6, cumulative, primary report only — does NOT include hypotheses.json) | PAUSE+offer summary | continue + flag in run_manifest | continue silently |
| wallclock > max_wallclock_minutes | PAUSE+ask extension | abort phase, emit partial | abort phase, emit partial |
| dirty working tree on critical files | PAUSE+ask | flag dirty, continue | flag dirty, continue |
| ambiguous scope (>1 plausible interpretation of args.roots) | PAUSE+ask | pick first by lexicographic order | pick first |

## Output contract (summary)

Every emitted file lives under the output directory; the target repository
is never written to. Canonical files: `inventory.json`,
`dependency_closure.md`, `oracle_inventory.md`, `entry_points.json`,
`flow_graphs/<unit>.json`, `hypotheses.json` (pre-feasibility, persisted,
including `oracle_status` and `oracle_ref` fields per Phase 2.5), `qa_report.md`
(post-feasibility, primary), `qa_report_overflow.md` (only when the
finding cap is exceeded), `coverage.md`, `open_questions.md`,
`run_manifest.json`, and `audit_log.jsonl`. A `.fbh/latest` symlink always
points to the most recent run. Retention is ninety days unless an operator
pins a run with `retain_forever`. Every evidence excerpt is a single line
and passes `scripts/redact_pii.py` against a regex catalog covering email
addresses, IPv4 and IPv6 literals, JWTs, AWS keys, Italian fiscal codes
and IBAN, and generic hex strings of length thirty-two or above. Redacted
tokens are replaced by typed placeholders; original content is never
persisted.

## Reference dispatch

The skill body is intentionally lean; substantive material lives in the
following references and is loaded on demand: `references/stacks/INDEX.md`
plus one file per Tier-1 stack and a `_generic-fallback.md` for everything
else; `references/bug_patterns.md` for the patterns × stacks matrix;
`references/qa_report_json_schema.md` for the canonical record to QA-case
schema mapping; `references/repro_voice_guide.md` for the eight actor
primitives with English and Italian examples; `references/severity_rubric.md`
for the four-tier rubric with κ target; `references/cross_stack_bridges.md`
for language-agnostic identifier resolution; `references/repo_granularity.md`
for monorepo detection rules; `references/qa_inclusion_tree.md` for the
four-node decision tree that defines what a QA could reasonably surface;
and `references/lifecycle_playbook.md` for triage, RACI, and the false
positive feedback loop.

## Quality and determinism

A run is deterministic on `qa_report.json`: re-running on the same SHA,
args, model id, and `skill_semver` produces a JSON whose structured
fields (`dedup_key`, `severity`, `category`, `entry_point_id`,
`reproduction_rate_target`) are stable and diff-able in CI. The
`qa_report.md` is a deterministic *rendering* of the JSON (same JSON →
byte-identical markdown via `scripts/render_qa_report.py`), but free-text
fields vary across LLM runs and the `.md` MUST NOT be used for byte-a-byte
diff in CI. Timestamps appear only in `run_manifest.json` and in the
`generated_at` field of `qa_report.json`; the markdown header pulls
`generated_at` from the JSON, never from `datetime.now()`. Findings are
sorted by severity descending (SEV-1 first), then `dedup_key` ascending.
The skill
performs no outbound network calls; the manifest asserts `network_calls: 0`.
The minimum recommended model is `claude-opus-4-7`; lower-tier invocations
are allowed but mark the report header with `confidence: low_model_tier`.
Versioning, bump rules, and the false-positive feedback loop are governed
by `references/lifecycle_playbook.md`.

## Hallucination Guard (machine-enforced)

After generating `qa_report.json`, run:

    python scripts/hallucination_guard.py qa_report.json

A non-zero exit code MUST block the pipeline. Do not proceed to
`render_qa_report.py` until `hallucination_guard.py` exits 0.

The script enforces five deterministic checks against the JSON report:

| Check | Rule |
|---|---|
| HG-01 | every finding has a non-empty `preconditions` array (≥1 item) |
| HG-02 | every finding has a `steps` array with ≥2 items |
| HG-03 | `dedup_key` is unique across the report (no duplicates) |
| HG-04 | `reproduction_rate_target` is one of `deterministic` / `95%` / `80%` / `<80%-needs-harness` |
| HG-05 | no two findings share an identical `title` (case-insensitive) |

Violations are printed as one line per offender in the format
`FINDING:<dedup_key>:HG-0N:<description>` so they are grep-able by CI.
The script supersedes the prose 5-checkbox guard from previous versions,
which degraded on reports with 30+ findings.

### Grounding policy (Phase 3 / Phase 4)

The machine-enforced HG above sits AFTER finding emission. The earlier
grounding policy still applies during finding *construction*: never cite
a line that was not seen in a grep/Read output; never assume framework
from package naming when a manifest is available; never promote a
hypothesis to a finding without a citable evidence excerpt. These are
operator obligations the LLM must respect when populating the JSON;
hallucination_guard.py only catches the structural symptoms.
