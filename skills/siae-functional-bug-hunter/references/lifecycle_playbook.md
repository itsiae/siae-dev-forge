# Lifecycle playbook

This file governs everything that happens **after** the skill emits a
`qa_report.md`: triage, ownership, false-positive feedback, calibration
of the severity rubric and the QA inclusion tree, and the rules for
bumping `skill_semver`.

## Invocation policy (DO NOT use as a hook)

**This skill is invocable only via the explicit slash command
`/siae-functional-bug-hunter`.**

Do NOT register this skill in `settings.json` as a `SessionStart`,
`PreToolUse`, `PostToolUse`, `UserPromptSubmit`, or `Stop` hook. Do NOT
wrap it in a wrapper skill that fires automatically.

Reasons:

- The skill performs static analysis whose cost is non-trivial (up to
  30 minutes wallclock per medium repo); auto-firing it would cause
  surprise expense.
- The output requires a human triage owner; auto-firing without an
  owner produces orphan reports.
- The interactive runtime mode pauses on STOP conditions; a hook
  fired in a non-TTY context would silently degrade to strict mode
  with potentially incomplete results.

If a recurring scan is desired, schedule it via a CI job that
explicitly invokes `/siae-functional-bug-hunter` in `strict` mode and
that has an explicit triage owner declared in the job config.

## Triage SLA

| Severity | First-triage SLA | First-decision SLA |
|---|---|---|
| Blocker | 1 business day | 3 business days |
| Critical | 3 business days | 10 business days |
| Major | 5 business days | 20 business days |
| Minor | 10 business days | next-quarter review |

"First triage" = the assignee reviews the finding and either accepts,
rejects (as false positive), or reassigns. "First decision" = a fix is
planned, deferred, or the finding is closed as known-and-accepted.

## RACI matrix (default)

| Role | Responsibility |
|---|---|
| **R** (Responsible) — QA lead | Reviews each finding, ensures the reproduction recipe works on a real environment, ingests into Jira/Xray |
| **A** (Accountable) — engineering manager of the owning service | Owns the decision to fix / defer / accept-known. Final accountability for SLA. |
| **C** (Consulted) — security team | Consulted when the finding touches auth/authz, PII, or secrets (rows R-Blocker-02, R-Critical-02, R-Critical-04 of the severity rubric) |
| **C** (Consulted) — product manager | Consulted when the fix changes user-visible behaviour (e.g. error-message wording, pagination semantics) |
| **I** (Informed) — runtime / SRE on-call | Informed of all Blocker and Critical findings; receives the link to the finding's Jira issue |

The "owning service" is determined by walking the entry-point's
`unit_id` back to the repository's `CODEOWNERS` file, falling back to
the git author of the most recent commit touching the entry-point file
when `CODEOWNERS` is absent or stale.

## Jira / Xray ingestion mapping

For each finding in `qa_report.md`, the recommended one-to-one mapping
to a Jira issue (or Xray test) is:

| qa_report.md field | Jira / Xray field |
|---|---|
| `finding_id` | Jira custom field `fbh-finding-id` (immutable) |
| `entry_point_id` | Jira custom field `fbh-entry-point-id` |
| `journey` | Jira component (`J-NNN`) or label (`fbh:J-NNN`) |
| `title` | Jira `Summary` |
| `severity` | Jira `Priority` mapped 1:1 (Blocker → P0, Critical → P1, Major → P2, Minor → P3) — adjust per project priority scheme |
| `severity_rubric_row` | Jira custom field `fbh-rubric-row` |
| `pattern_id` | Jira label `fbh:<BP-NNN>` |
| `preconditions` + `steps` + `expected_result` + `actual_result` | Jira `Description` (or Xray `Manual Test` body) |
| `evidence` | Jira `Description` evidence block (file paths and SHA preserved as plain text) |
| `confidence` | Jira label `fbh:confidence-<value>` |
| `suggested_fix_direction` | Jira comment by the bot identity |
| `reproduction_rate_target` | Xray `Test Repeats` field (when ≥80%, set `Test Repeats = 5`; when ≥95%, set `Test Repeats = 1`) |
| `boundary_observations` | Jira `Issue Links` (one link per other unit referenced) |

Automation is the operator's responsibility — the skill emits
machine-readable `qa_report.md` and an optional `qa_report.json` (when
`args.emit_json=true` is supported in a future minor version). The
skill does NOT call Jira / Xray APIs directly (no outbound network in
v1; see SKILL.md "Quality and determinism").

## False-positive feedback loop

The skill improves over runs only when triagers feed information back.
The contract:

1. Triagers mark `false_positive: true` (Jira custom field) when a
   finding is rejected as not a real bug.
2. A nightly job in the triage organization appends one line per
   rejected finding to `eval/feedback.jsonl` with shape:

```json
{"ts":"2026-05-15T11:23:00Z","finding_id":"F-0042","run_id":"<scope-hash>","pattern_id":"BP-002","reason":"intended behaviour - documented in <link>","reviewer":"<name>"}
```

3. The skill maintainers re-run `eval/` against the cumulative
   feedback corpus monthly and adjust the bug-patterns matrix /
   inclusion tree / severity rubric accordingly.
4. Changes to the patterns / tree / rubric MUST be accompanied by a
   test in `eval/golden_set/` that pins the new behaviour. The κ
   target stays ≥ 0.7.

The skill itself does NOT consume `eval/feedback.jsonl` at runtime
(determinism rule: the same input must always produce the same
output). Feedback is metadata, not input.

## Closed-loop metrics (quarterly)

The following metrics are tracked in `eval/metrics.md` and published
quarterly:

| Metric | Definition | Target |
|---|---|---|
| Precision | fraction of findings NOT marked `false_positive` after triage | ≥ 0.75 |
| Recall (vs golden set) | fraction of golden-set bugs detected by a clean run | ≥ 0.70 |
| Time-to-first-triage (P50) | median wall-clock from report emission to first triage entry | ≤ SLA per severity |
| Fix rate | fraction of accepted findings that result in a merged code change within 30 days | ≥ 0.50 for Blocker+Critical |
| κ (severity) | Cohen's κ between two reviewers on severity assignment | ≥ 0.70 |
| κ (inclusion) | Cohen's κ between two reviewers on the QA inclusion tree | ≥ 0.70 |
| Mean wallclock (medium repo) | mean phase 0–8 duration on `eval/medium_repo/` | ≤ 5 min |

When a metric falls below target two quarters in a row, the playbook
triggers a corrective action:

- precision low → tighten the bug-patterns row(s) with the worst FP rate
  (add false-positive guards),
- recall low → review golden-set hypotheses that were missed; loosen
  detection signals,
- κ low → re-calibration workshop on the rubric / inclusion tree,
- wallclock slow → review `max_grep_round_trips_per_ep` and tree-sitter
  depth budgets.

## Versioning &amp; bump rules

`skill_semver` follows semantic versioning with the following bump
policy:

| Change class | Bump |
|---|---|
| Additive: new Tier-1 stack file, new bug-pattern row, new bridge kind, new monorepo rule, new severity-rubric row | **Minor** (1.X.0) |
| Backwards-compatible internal: improved subagent prompt, prompt-engineering tweak that does NOT change the output schema | **Patch** (1.0.X) |
| Breaking output: change to `qa_report.md` schema, change to canonical_record schema, change to severity-rubric semantics that re-classifies existing findings, removal of a stack / pattern | **Major** (X.0.0) |
| Calibration: rubric row split / merge that does NOT reclassify on the golden set | **Minor** |
| Calibration: rubric row split / merge that DOES reclassify on the golden set | **Major** |

Every run records the exact `skill_semver` in `run_manifest.json` so
historical runs remain reproducible.

## Retention &amp; pinning

OUTPUT_DIR runs are auto-pruned after **90 days**. To pin a run forever
(e.g. for a compliance audit, an incident retrospective, or a baseline
comparison), copy the run directory outside `.fbh/runs/` or set
`args.retain_forever: true` at invocation time.

The `.fbh/latest` symlink always points to the most recent run. The
symlink itself is harmless to delete; it is recreated on the next run.

## Hand-off to an operator new to the skill

A new operator can become productive on this skill in three steps:

1. Read `SKILL.md` end-to-end (10 minutes).
2. Run the skill against `eval/golden_set/medium_repo/` in
   `report-only` mode and read the emitted `qa_report.md` (15 minutes).
3. Read this playbook (5 minutes) and confirm the RACI fits the
   operator's team.

Total onboarding: 30 minutes for a baseline understanding. Deeper
knowledge of individual stacks / patterns comes from the
`references/stacks/` and `references/bug_patterns.md` files as needed,
NOT in advance.

## Out-of-band escalation

When the skill emits a `qa_report.md` containing a Blocker finding on
production code, the operator MUST notify the on-call rotation within
the Blocker SLA (1 business day). The notification channel is the
team's incident-management Slack channel or equivalent; the link to
the Jira issue (created from the finding via the mapping above) is
sufficient context. The skill itself does NOT send notifications.
