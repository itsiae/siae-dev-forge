# QA report — JSON Schema &amp; render contract

This file replaces the former `qa_report_template.md`. The contract is
split in two:

- **`qa_report.json`** — schema-stable, validable, diff-able in CI. Claude
  generates this file directly from Phase 7 synthesis. The structured fields
  (`dedup_key`, `severity`, `category`, `entry_point_id`,
  `reproduction_rate_target`) are deterministic across LLM runs.
- **`qa_report.md`** — deterministic rendering of `qa_report.json` via
  `scripts/render_qa_report.py`. The free-text fields (`title`,
  `preconditions`, `steps`, `suggested_fix_direction`) vary across LLM
  runs and MUST NOT be used for byte-a-byte diff in CI.

## DETERMINISM CONTRACT

- `qa_report.json`: schema-stable. I campi strutturati (`dedup_key`,
  `severity`, `category`, `entry_point_id`, `reproduction_rate_target`)
  sono deterministici e diff-able in CI.
- `qa_report.md`: rendering deterministico via `render_qa_report.py` dal
  JSON. I campi free-text (`title`, `preconditions`, `steps`,
  `suggested_fix_direction`) variano tra run LLM; NON usare `qa_report.md`
  per confronto byte-a-byte in CI.
- Gate CI consigliato: diff su `qa_report.json` campi strutturati, non
  su `.md`.

## QA test case JSON schema

Every finding in `qa_report.json` is one entry in the `findings[]` array.
The schema is the **aggregate** of the per-subagent `SubagentResult.Finding`
schema declared in `references/subagent_contract.md`, extended with the
report-level fields below.

### Report-level shape

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "QAReport",
  "type": "object",
  "required": ["schema_version", "run_id", "generated_at", "skill_semver",
               "model_id", "mode", "lang", "findings"],
  "additionalProperties": false,
  "properties": {
    "schema_version":   { "const": "1.0" },
    "run_id":           { "type": "string" },
    "scope_hash":       { "type": "string" },
    "generated_at":     { "type": "string", "format": "date-time",
                          "description": "ISO 8601 UTC. Used by render_qa_report.py as the markdown header timestamp." },
    "skill_semver":     { "type": "string" },
    "model_id":         { "type": "string" },
    "mode":             { "enum": ["interactive","strict","report-only"] },
    "confidence":       { "enum": ["high","medium","low_partial","low_model_tier","low_pattern_match"] },
    "lang":             { "enum": ["en","it"] },
    "findings":         { "type": "array", "items": { "$ref": "#/definitions/Finding" } },
    "stats":            { "type": "object" }
  },
  "definitions": {
    "Finding": {
      "type": "object",
      "required": ["dedup_key","finding_id","entry_point_id","journey",
                   "title","severity","severity_rubric_row","pattern_id",
                   "category","preconditions","steps","expected","actual",
                   "evidence","suggested_fix_direction","reproduction_rate_target",
                   "confidence"],
      "additionalProperties": false,
      "properties": {
        "dedup_key":               { "type": "string", "pattern": "^[0-9a-f]{16}$" },
        "finding_id":              { "type": "string", "pattern": "^F-[0-9]{4}$" },
        "entry_point_id":          { "type": "string" },
        "journey":                 { "type": "string", "pattern": "^J-[0-9]{3}(-misc)?$" },
        "title":                   { "type": "string", "maxLength": 120 },
        "severity":                { "enum": ["SEV-1","SEV-2","SEV-3","SEV-4"] },
        "severity_rubric_row":     { "type": "string" },
        "pattern_id":              { "type": "string", "pattern": "^BP-[0-9]{3}$" },
        "category":                { "enum": ["auth-bypass","data-race","toctou","webhook-replay",
                                              "cache-staleness","cursor-drift","dst-skip",
                                              "input-validation","business-logic","other"] },
        "preconditions":           { "type": "array", "items": { "type": "string" }, "minItems": 1 },
        "steps":                   { "type": "array", "items": { "type": "string" }, "minItems": 1 },
        "expected":                { "type": "string" },
        "actual":                  { "type": "string" },
        "evidence":                {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["file","line_start","line_end","sha","dirty_flag","excerpt"],
            "additionalProperties": false,
            "properties": {
              "file":       { "type": "string" },
              "line_start": { "type": "integer", "minimum": 1 },
              "line_end":   { "type": "integer", "minimum": 1 },
              "sha":        { "type": "string" },
              "dirty_flag": { "type": "boolean" },
              "excerpt":    { "type": "string", "maxLength": 200 }
            }
          }
        },
        "suggested_fix_direction": { "type": "string" },
        "reproduction_rate_target":{ "enum": ["deterministic","95%","80%","<80%-needs-harness"] },
        "boundary_observations":   { "type": "array", "items": { "type": "string" } },
        "confidence":              { "enum": ["high","medium","low_partial","low_model_tier","low_pattern_match"] },
        "notes":                   { "type": "string", "maxLength": 200 }
      }
    }
  }
}
```

### Field mapping (canonical record → JSON finding)

```
canonical_record.id             → entry_point_id
canonical_record.source_ref     → evidence[0]  (entry-point evidence)
canonical_record.kind           → drives primary actor primitive used in steps
canonical_record.actor          → primary actor primitive
canonical_record.trigger        → step 1 phrasing
canonical_record.inputs         → preconditions + step 1 inputs
canonical_record.downstream_calls → boundary_observations (when crossing units)
canonical_record.side_effects   → observer step (last)

hypothesis.pattern_id           → pattern_id
hypothesis.category             → category
hypothesis.precondition_signals → preconditions (augmented)
hypothesis.functional_manifestation → actual
hypothesis.severity_hint        → severity (then refined by rubric)
hypothesis.related_actors       → constrains step primitives
```

## Markdown render contract

`scripts/render_qa_report.py` reads `qa_report.json` and emits
`qa_report.md` using the skeleton below. The rendering is deterministic
given the same JSON: same sort order, same header timestamp (taken from
`generated_at`, never from `datetime.now()`), same separator characters.

```markdown
# Functional bug report

- **Run id**: <run_id>
- **Scope hash**: <scope_hash>
- **Skill semver**: <skill_semver>
- **Model id**: <model_id>
- **Mode**: <mode>
- **Generated at**: <generated_at>  (from qa_report.json, NOT datetime.now())
- **Confidence (global)**: <confidence>
- **Findings**: <n_sev1> SEV-1 · <n_sev2> SEV-2 · <n_sev3> SEV-3 · <n_sev4> SEV-4
- **Lang**: <lang>

## Index

| Finding | Journey | Severity | Title | Entry point |
|---|---|---|---|---|
| F-0001 | J-001 | SEV-2 | <title> | <entry_point_id> |
| …      | …     | …      | …       | …                |

## Journey J-001 — <derived journey title>

### F-0001 — <title>

- **Severity**: <SEV-N> (rubric row <severity_rubric_row>)
- **Pattern**: <pattern_id>
- **Category**: <category>
- **Entry point**: <entry_point_id>
- **Confidence**: <confidence>

**Preconditions**

- <bullet>
- <bullet>

**Steps**

1. <step>
2. <step>

**Expected result**

<text>

**Actual result**

<text>

**Evidence**

- `<file>:<line_start>-<line_end>` @ `<sha>`[`+dirty`]
  > <one-line redacted excerpt>

**Suggested fix direction**

<text>

**Reproduction rate target**

`<deterministic | 95% | 80% | <80%-needs-harness>`

---
```

## Render sort order

`render_qa_report.py` sorts findings before emission:

1. Severity descending: SEV-1 > SEV-2 > SEV-3 > SEV-4.
2. Within same severity: `dedup_key` ascending (alphabetical, since hex).

Journey ordinals (`J-NNN`) are assigned in the order journeys first
appear under that sort. Findings without enough signal land in
`J-000-misc`.

## CI usage

- **Schema diff**: `jq` or any JSON-aware differ on `qa_report.json`.
  The structured fields produce stable diffs across LLM runs.
- **Severity gate**: shell snippet
  ```bash
  jq '[.findings[] | select(.severity == "SEV-1")] | length' qa_report.json
  ```
- **Markdown rendering**: invoke `python scripts/render_qa_report.py
  qa_report.json > qa_report.md`. The output is byte-stable for the same
  JSON input but NOT byte-stable across LLM runs that produce different
  free-text. Treat `.md` as a presentation artifact.

## Localization

When `lang = "it"`:

- All free-text fields (`title`, `preconditions`, `steps`, `expected`,
  `actual`, `suggested_fix_direction`, derived journey title) are
  emitted in Italian.
- Schema field names (those in the JSON schema above) remain English.
- Severity tier names remain English (`SEV-1`…`SEV-4`) so they are
  interoperable with Jira / Xray automation.

When `lang = "en"` (default), everything stays English.
