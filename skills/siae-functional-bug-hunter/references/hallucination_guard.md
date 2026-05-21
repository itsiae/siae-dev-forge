# Hallucination guard contract

Load-on-demand reference: the machine-enforced check that gates emission
of `qa_report.md` from `qa_report.json` at the end of Phase 8.

## Invocation

After generating `qa_report.json`, run:

    python scripts/hallucination_guard.py qa_report.json

A non-zero exit code MUST block the pipeline. Do not proceed to
`render_qa_report.py` until `hallucination_guard.py` exits 0.

## Deterministic checks (HG-01 .. HG-05)

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

## Grounding policy (operator obligation during Phase 3 / Phase 4)

The machine-enforced HG above sits AFTER finding emission. The earlier
grounding policy still applies during finding *construction*:

- never cite a line that was not seen in a grep/Read output;
- never assume framework from package naming when a manifest is available;
- never promote a hypothesis to a finding without a citable evidence excerpt.

These are operator obligations the LLM must respect when populating the
JSON; `hallucination_guard.py` only catches the structural symptoms.
