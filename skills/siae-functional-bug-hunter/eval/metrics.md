# Metrics

This file documents the metrics computed against the golden set and
the cumulative triage feedback. It is the source of truth for the
Quality Bar in `SKILL.md` and the calibration loop in
`references/lifecycle_playbook.md`.

## Metric definitions

| Metric | Definition | Source | Target |
|---|---|---|---|
| Precision | `matched_findings / total_reported_findings` | golden set run + `eval/feedback.jsonl` triage marks | ≥ 0.75 |
| Recall | `matched_findings / total_expected_findings` | golden set run vs `expected_findings.json` | ≥ 0.70 |
| Time-to-first-triage P50 | median(first_triage_ts - run_emit_ts) | triage system (Jira) | ≤ severity SLA in `lifecycle_playbook.md` |
| Fix-rate (Blocker + Critical) | `fixed_within_30d / accepted_findings` | triage system | ≥ 0.50 |
| κ (severity) | Cohen's κ on a 4-class label (Blocker / Critical / Major / Minor) between two annotators | golden set re-label | ≥ 0.70 |
| κ (inclusion) | Cohen's κ on a binary label (included / excluded by the 4-node tree) between two annotators | golden set re-label | ≥ 0.70 |
| Mean wallclock (medium_repo) | mean of `run_manifest.elapsed_seconds` over the last 10 runs against `medium_repo/` | run manifests | ≤ 300 s |
| Reproduction rate (race) | for BP-003 / BP-011 / BP-014 findings, fraction of repros achieving ≥80% over 5 attempts | manual QA | ≥ 0.80 |
| Reproduction rate (non-race) | for all other patterns, fraction achieving ≥95% over 5 attempts | manual QA | ≥ 0.95 |
| Network calls per run | sum of outbound calls per run | `run_manifest.network_calls` | == 0 |
| PII redaction coverage | fraction of PII tokens in `eval/pii_corpus/` that are correctly redacted | unit test on `redact_pii.py` | == 1.00 |

## Quarterly publication

A short report is published quarterly in
`docs/quarterly-metrics-YYYY-QN.md` (outside the skill directory, in
the operator's documentation system). The report contains:

- Each metric's value for the last quarter and a sparkline of the
  trailing 4 quarters.
- For metrics below target: a one-paragraph explanation and the
  remediation action triggered per the lifecycle playbook.
- Significant additions to the golden set (new cases, sanitized
  examples).

The skill itself never reads or writes these reports; they are
operator-side artifacts.

## Aggregation across runs

When precision and recall are reported, they are computed across the
**entire golden set as a single corpus** (micro-averaged), NOT
per-fixture (macro-averaged). This makes the metric robust against a
single large fixture dominating the mean.

When the trend on a per-fixture basis is needed for diagnosis, a
per-fixture breakdown is included as a secondary table.

## Versioning of metrics

Metric definitions are themselves versioned. Any change to the
definition (e.g. tightening the line-range overlap criterion in the
golden-set match algorithm) is a **major** skill bump because it
changes the historical comparability of numbers.

## Feedback ingestion (closed loop)

`eval/feedback.jsonl` accumulates one line per triaged finding marked
`false_positive: true`. The line shape is documented in
`lifecycle_playbook.md`. Monthly:

1. Maintainers compute precision against the cumulative feedback.
2. The bug-pattern row with the worst FP rate is reviewed; if a
   tightening of the precondition signals would have prevented the
   FPs, the pattern is updated (minor bump).
3. The change is validated by re-running the golden set and confirming
   recall remains ≥ 0.70.

## Empty-corpus posture

The v1.0.0 release ships with `golden_set/manifest.json.cases == []`
because fixtures are derived from real production bugs. In that state:

- Precision and recall are reported as `N/A — empty corpus`.
- κ measurements require at least 5 findings per axis to be meaningful;
  smaller samples report `insufficient sample`.
- The Quality Bar checks for precision / recall in `SKILL.md` are
  satisfied vacuously while the corpus is empty; they activate
  automatically when `manifest.json.cases.length >= 5`.

This is intentional: the skill is shipped before its corpus is built,
and the operator is expected to grow the corpus over time using real
sanitized triage outcomes.
