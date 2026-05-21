---
name: siae-functional-bug-hunter
description: >
  Static, multi-repo, cross-stack functional bug hunter. Ingests repository
  roots, detects missing dependencies, generates bug hypotheses from a
  stack-aware pattern matrix, filters by path feasibility, and emits a
  deterministic qa_report.md grouped by user-journey with minimally-flaky
  reproduction recipes voiced for a manual QA tester (ISTQB Foundation +
  2 years). Supports JVM, JS/TS, Python, Go, Rust, mobile, IaC, AWS
  serverless, data platforms (see references/stacks/INDEX.md), plus a
  generic fallback. Invocation is manual only via slash command
  /siae-functional-bug-hunter — no auto hooks, no session-start, no NL
  trigger. Three runtime modes dispatched: interactive (TTY may pause),
  strict (CI never pauses), report-only (low-confidence partial allowed).
  Excludes SAST-only findings without functional manifestation; excludes
  test-code generation.
allowed-tools: Read, Grep, Glob, Bash, Task
min_model: claude-opus-4-7
skill_semver: 1.2.0
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

## When to use

Use this skill when you need a deterministic, evidence-grounded QA report
of functional bugs reproducible by a human tester (ISTQB Foundation + 2y)
against a codebase you can read statically. Typical triggers: pre-release
regression scoping on a new feature branch, exploratory audit of an
unfamiliar repository, post-incident root-cause investigation when the
runtime is unavailable, cross-repo functional review where the bug may
emerge at the boundary.

## Supported stacks

Tier-1 stacks (full pattern matrix): Java, Kotlin, Scala, TypeScript /
JavaScript, Python, Go, Rust, Swift, Ruby, .NET / C#, Flutter / Dart,
Terraform / HCL, AWS serverless (SAM, CDK, SFN, EventBridge), and data
platforms (dbt, Airflow, Spark, SQL). Tier-2 fallback (`_generic-fallback.md`)
covers Elixir, Clojure, PHP, Perl, Lua, Haskell, OCaml, and anything else
the dispatcher does not recognise. See `references/stacks/INDEX.md` for the
authoritative list and per-stack manifest fingerprints.

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

Nine ordered phases (plus sub-phases 2.5 and 7.5). Each emits canonical
artifacts under `output_dir`, has a closed stop-trigger set, and an
empty-input branch. Full per-phase implementation detail is in
`references/pipeline_internals.md` (load on demand).

| Phase | Purpose | Canonical artifacts | Empty-input branch |
|---|---|---|---|
| 0 — Preflight | Env probe, mode detect, run-lock acquire | `audit_log.jsonl`, `.fbh/run.lock` | abort if `preflight.sh overall_ok=false` |
| 1 — Inventory | Walk roots, detect stacks via manifest fingerprints | `inventory.json` | fail-fast with manifest-hint suggestion |
| 2 — Dep closure | Flag cross-repo / external dependencies | `boundary_identifier_registry.json`, `dependency_closure.md` | STOP per mode (see Stop conditions) |
| 2.5 — Oracle inventory | Classify oracles (rank A/B/C); tag hypotheses | `oracle_inventory.md`; `oracle_status` + `oracle_ref` on each hypothesis | emit empty oracle list with warning |
| 3 — Entry points | Stack-dispatched extraction, fan-out to ≤8 parallel subagents (`subagent_contract.md`) | `entry_points.json` | emit `qa_report.md status=no_entry_points` |
| 4 — Flow | Build call & data flow per entry-point (bounded AST + grep budget 20) | `flow_graphs/<unit>.json` | record degraded in `coverage.md` |
| 5 — Hypothesis gen | Apply `bug_patterns.md` matrix (rows × stacks) | `hypotheses.json` (pre-feasibility) | n/a (always emits at least empty list) |
| 6 — Feasibility filter | `scripts/path_feasibility.py` verdicts each hypothesis | hypothesis verdict on `hypotheses.json` | emit `qa_report.md status=all_hypotheses_filtered` |
| 7 — Repro synthesis | Canonical QA case via `severity_rubric.md` + `repro_voice_guide.md` | finding records (in-memory) | n/a |
| 7.5 — Journey clustering | Deterministic cluster by (actor, entry-kind, top-resource); stable `J-NNN` | journey ids on findings | findings → `J-000-misc` |
| 8 — Report assembly | `qa_report.json` (canonical) + `qa_report.md` (rendered) | `qa_report.json`, `qa_report.md`, `qa_report_overflow.md`, `coverage.md`, `open_questions.md`, `run_manifest.json` | n/a |

### Oracle rank (Phase 2.5)

| Rank | Oracle type | Examples | Reliability |
|---|---|---|---|
| A | Formal spec | OpenAPI/Swagger, Protobuf, JSON Schema, SQL schema with constraints | High — source of truth |
| B | Test / contract | Unit, integration, acceptance criteria in commit/PR, Pact | Medium-high — reveals intent |
| C | Informal docs | README, comments, Javadoc, repo-linked wikis | Medium — must be cross-checked |

Each entry in `hypotheses.json` carries `oracle_status` (`VERIFIED` / `PARTIAL` / `HYPOTHESIS`) and `oracle_ref` (file:line of the oracle, or `null`). `HYPOTHESIS`-status entries are persisted as weak signal, never discarded.

### Hallucination guard (between Phase 8 emission and rendering)

`scripts/hallucination_guard.py qa_report.json` MUST exit 0 before `render_qa_report.py` runs. See `references/hallucination_guard.md` for the 5-check contract and grounding policy.

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

## Hallucination guard

Phase 8 gates emission of `qa_report.md` behind
`scripts/hallucination_guard.py qa_report.json` (exit 0 required). The
guard runs five deterministic checks (HG-01..05) and enforces a grounding
policy on hypothesis construction. Full contract in
`references/hallucination_guard.md`.
