# Golden set

The golden set is a curated corpus of fixtures, each describing a known
functional bug with its expected classification. It is the authoritative
input for measuring inter-rater agreement (Cohen's κ) on the two
classification axes that the skill emits: `severity` (4 classes) and
`category` (10 classes).

The corpus was populated as part of FIX-9 with **5 bootstrap fixtures**
covering the 5 high-frequency patterns added in FIX-8 (BP-019..BP-023).

## Directory layout

```
golden_set/
├── README.md                                           (this file)
└── fixtures/
    ├── fixture_001_toctou_auth_revocation/
    ├── fixture_002_webhook_replay_stripe/
    ├── fixture_003_cursor_pagination_drift/
    ├── fixture_004_dst_cron_skip/
    └── fixture_005_cache_staleness_redis/
        ├── input.json              (entry points + stack_context)
        ├── expected_finding.json   (ground-truth Finding object, schema v1.0)
        ├── rationale.md            (3–5 lines: why this severity, edge cases)
        └── negative_example.json   (typical wrong finding + why it is wrong)
```

Each fixture is self-contained: a single bug, a single expected
classification, a single annotated counterexample.

## Adding a new fixture

1. Create `fixtures/fixture_NNN_<descriptive_name>/`.
2. Author `input.json` with `entry_points` (per the canonical record
   schema in `scripts/list_entry_points.py`) and a `stack_context`
   string describing the relevant framework configuration.
3. Author `expected_finding.json` as a single object matching the
   `SubagentResult.Finding` schema in
   `references/subagent_contract.md`. Compute `dedup_key` as
   `sha256(boundary_id + ':' + category + ':' + entry_point_id)[:16]`.
4. Author `rationale.md`: 3–5 lines explaining the severity choice
   (which row of `severity_rubric.md` and why), plus edge cases that
   would shift the classification.
5. Author `negative_example.json` with a `wrong_finding` object (same
   schema) and a `why_wrong` paragraph explaining the misclassification
   — typically a swap of category or severity that the rubric resolves
   against.
6. Run `python3 eval/run_kappa_eval.py` to confirm the sanity-wiring
   path (expected == reported) still passes.

## Running the κ evaluator

```bash
# Sanity check (expected == reported, κ must be 1.0)
python3 eval/run_kappa_eval.py

# Negative baseline (feeds each fixture's wrong_finding; κ must drop)
python3 eval/run_kappa_eval.py --negative-baseline

# Real scoring against a directory of skill outputs
python3 eval/run_kappa_eval.py --reports-dir /path/to/run-outputs/
```

Thresholds (the script exits 1 below either):

- κ_severity ≥ 0.70
- κ_category ≥ 0.60

## Current results

Measured on the 5 bootstrap fixtures shipped with FIX-9 (2026-05-21):

| Run                          | κ_severity | κ_category | rc |
|------------------------------|-----------:|-----------:|---:|
| sanity wiring (expected==reported) | 1.0000 | 1.0000 | 0 |
| negative baseline (wrong_finding)  | -0.3158 | 0.0000 | 1 |

These two runs are the calibration bookends: the sanity run verifies
the κ machinery is wired up; the negative baseline verifies κ correctly
signals classification drift. **Neither measurement reflects skill
quality** — that requires real skill runs against the fixtures and a
`--reports-dir` argument.

## Important: corpus is below CI-gate size

κ ≥ 0.70 on this 5-fixture corpus is **necessary but not sufficient**.
The corpus must grow to ≥ 30 fixtures with diverse stacks and patterns
before κ is reliable enough to gate CI. Until then, treat
`run_kappa_eval.py` as a sanity tool, not a release-blocking metric.
The growth path is documented in `references/lifecycle_playbook.md`
under "calibration loop".

## What κ measures (and what it does not)

- κ_severity measures whether the skill assigns the same severity tier
  as the human annotator. It does NOT measure whether the finding is
  real, useful, or actionable.
- κ_category measures whether the skill picks the same category. A
  systematic preference for `other` (the lazy-classification anti-pattern
  in `severity_rubric.md`) drives κ_category down quickly — by design.
- Precision and recall are computed separately by future scripts (see
  the precision/recall section in the prior README iteration, archived
  in git history). They require a different fixture format (full repo
  snapshots) and are not part of FIX-9.
