# References — load-on-demand reference material

The skill body in `../SKILL.md` is intentionally lean. Everything below
is loaded on demand by the orchestrator (or by an operator running the
pipeline manually). Each reference is single-purpose; do not load them
all eagerly.

## Load matrix

| Reference file | Loaded by | When |
|---|---|---|
| `stacks/INDEX.md` | Phase 1 (Inventory) | always, to dispatch stack detection |
| `stacks/<stack>.md` | Phase 3 (Entry points) | once per detected stack in the unit |
| `stacks/_generic-fallback.md` | Phase 3 fallback | when no Tier-1 stack matches |
| `repo_granularity.md` | Phase 1 | when monorepo signals present (Nx, Turborepo, Bazel, Gradle multi, Go workspace) |
| `subagent_contract.md` | Phase 3 | always, governs parallel subagent fan-out |
| `cross_stack_bridges.md` | Phase 4 | when ≥2 stacks detected in scope |
| `bug_patterns.md` | Phase 5 | always, the pattern × stack matrix |
| `qa_inclusion_tree.md` | Phase 5 + Phase 6 | always, gates SAST-only vs functional findings |
| `severity_rubric.md` | Phase 7 | always, mandatory rubric citation per finding |
| `repro_voice_guide.md` | Phase 7 | always, eight allowed actor primitives |
| `qa_report_json_schema.md` | Phase 8 | always, canonical-record → QA-case mapping |
| `hallucination_guard.md` | Phase 8 | always, contract for `scripts/hallucination_guard.py` |
| `pipeline_internals.md` | none of the above (operator-facing) | when an operator needs to debug or extend a phase |
| `runtime_modes.md` | Phase 0 + any phase emitting STOP | always, event → action matrix for the 3 runtime modes |
| `lifecycle_playbook.md` | post-run (triage, false-positive feedback loop) | manual, RACI and bump rules |

## Anti-bloat policy

- New reference file MUST have a unique load trigger row in the matrix
  above. If two references would have the same trigger, merge them.
- Single-file soft cap: ≤2500 tokens. The current outlier
  (`bug_patterns.md`, ~5290 tokens) is grandfathered because it serves as
  the canonical matrix and splitting it would fragment the source of truth;
  any *new* reference must respect the cap.
- The `SKILL.md` body MUST NOT duplicate content that exists here. Cite by
  reference path instead.
