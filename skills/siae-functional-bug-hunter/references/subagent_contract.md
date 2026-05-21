# Subagent Contract — functional-bug-hunter Phase 3

This file is the **single source of truth** for the contract between the
orchestrator and the per-boundary subagents fanned out in Phase 3 of the
pipeline. The orchestrator MUST inject the prompt template below verbatim,
MUST validate every subagent return payload against the JSON schema, and
MUST merge by `dedup_key` per the strategy below. Schema drift between
subagents is the single largest source of false positives in v1; this file
exists to eliminate it.

## Prompt template (da iniettare per ogni subagent)

```
SYSTEM: You are a functional-bug-hunter subagent. Your scope is EXACTLY ONE boundary:
<boundary_id>{{BOUNDARY_ID}}</boundary_id>
<boundary_type>{{BOUNDARY_TYPE}}</boundary_type>  <!-- api|db|event|cache|auth|scheduler|webhook|ui -->
<stack_context>{{STACK_SNIPPET}}</stack_context>
<schema_version>1.0</schema_version>
Return ONLY valid JSON matching the SubagentResult schema below. No prose, no markdown.
If you find no bugs, return an empty findings array.

USER: Analyse the following entry points and cross-stack payloads for functional bugs.
Entry points: {{ENTRY_POINTS_JSON}}
Payloads dir: {{PAYLOADS_SUMMARY}}
```

Placeholders:

| Placeholder | Source | Notes |
|---|---|---|
| `{{BOUNDARY_ID}}` | `boundary_identifier_registry.json` key | Stable across runs (kind + identifier) |
| `{{BOUNDARY_TYPE}}` | enum: `api`, `db`, `event`, `cache`, `auth`, `scheduler`, `webhook`, `ui` | Drives which bug patterns are in scope |
| `{{STACK_SNIPPET}}` | Excerpt from `references/stacks/<id>.md` for the unit | Limit ~2 KB to keep prompt small |
| `{{ENTRY_POINTS_JSON}}` | Subset of `entry_points.json` for this boundary | Already validated by `list_entry_points.py` |
| `{{PAYLOADS_SUMMARY}}` | Output of `scripts/generate_payloads.py --output-dir` | See "Payloads dir — producer" below |

## SubagentResult schema (JSON Schema Draft-07)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SubagentResult",
  "type": "object",
  "required": ["boundary_id", "schema_version", "findings"],
  "additionalProperties": false,
  "properties": {
    "boundary_id":     { "type": "string" },
    "schema_version":  { "const": "1.0" },
    "findings": {
      "type": "array",
      "items": { "$ref": "#/definitions/Finding" }
    }
  },
  "definitions": {
    "Finding": {
      "type": "object",
      "required": ["dedup_key","title","severity","category",
                   "preconditions","steps","expected","actual",
                   "suggested_fix_direction","reproduction_rate_target"],
      "additionalProperties": false,
      "properties": {
        "dedup_key": {
          "type": "string",
          "description": "SHA-256(boundary_id + ':' + category + ':' + entry_point_id). Hex, lowercase, first 16 chars.",
          "pattern": "^[0-9a-f]{16}$"
        },
        "title":        { "type": "string", "maxLength": 120 },
        "severity":     { "enum": ["SEV-1","SEV-2","SEV-3","SEV-4"] },
        "category":     { "enum": ["auth-bypass","data-race","toctou","webhook-replay",
                                   "cache-staleness","cursor-drift","dst-skip",
                                   "input-validation","business-logic","other"] },
        "entry_point_id": { "type": "string" },
        "preconditions":  { "type": "array", "items": { "type": "string" }, "minItems": 1 },
        "steps":          { "type": "array", "items": { "type": "string" }, "minItems": 1 },
        "expected":       { "type": "string" },
        "actual":         { "type": "string" },
        "suggested_fix_direction": { "type": "string" },
        "reproduction_rate_target": {
          "type": "string",
          "enum": ["deterministic","95%","80%","<80%-needs-harness"],
          "description": "Declared target. Must match observed if harness exists."
        },
        "cross_stack_bridge": { "type": ["string","null"] }
      }
    }
  }
}
```

## Dedup strategy

The merge pipeline uses `dedup_key` as the primary key. The orchestrator
collects all `SubagentResult.findings` arrays returned by the fan-out
(max 8 in parallel) and performs the following deterministic merge:

1. Group findings by `dedup_key`.
2. Collision (same `dedup_key` from ≥2 subagents) → merge:
   - keep the finding with the highest severity (SEV-1 > SEV-2 > SEV-3 > SEV-4);
   - if severities are equal, keep the one with the longer `steps` array;
   - if still tied, keep the one whose `boundary_id` sorts first lexicographically.
3. Log every collision in `.fbh/merge.log` with format:
   `<ISO8601> dedup_key=<key> kept=<boundary_id> dropped=<boundary_id>,...`
4. Validate the merged finding once more against the schema. Drop and log
   any merged finding that fails validation (this should never happen if
   inputs pass validation, but is the safety net).

`dedup_key` is computed as:

```
dedup_key = sha256(boundary_id + ':' + category + ':' + entry_point_id).hexdigest()[:16]
```

Subagents MUST compute this themselves (not the orchestrator) so the
orchestrator can validate the claim before merging. A `dedup_key` that
does not match the recomputed hash is a schema violation.

## Payloads dir — producer

`list_entry_points.py --payloads <DIR>` (alias `--payloads-dir <DIR>`)
expects `<DIR>` to be populated by `scripts/generate_payloads.py`
(see `scripts/generate_payloads.py` for the contract). If the dir is
absent or empty, `list_entry_points.py` MUST print a warning on stderr
and continue with an empty array — it MUST NOT fail silently.

The producer (`generate_payloads.py`) writes one JSON file per entry
point under `<DIR>/<entry_point_id>.json` containing the cross-stack
payload signals discovered for that entry point (request/response
schemas, queue/topic payload samples, env-var-resolved literals, etc.).
The output dir path is printed on stdout so the orchestrator can pipe
it into `list_entry_points.py`.

## Validation pipeline

The orchestrator validates each `SubagentResult` BEFORE merging:

1. JSON parse — failure → log and drop the entire subagent return.
2. Schema validation against `SubagentResult` — any failure → log and
   drop the entire subagent return (do NOT cherry-pick valid findings;
   schema drift in one finding is a signal the subagent is unreliable).
3. `schema_version == "1.0"` — mismatch is a hard error; the orchestrator
   aborts the merge phase and surfaces the version skew in
   `open_questions.md`.
4. Per-finding: recompute `dedup_key` and reject any finding whose
   declared key disagrees with the recomputed one.

## Hard cap and fallback

The hard cap is **8 subagents in parallel**. If the orchestrator runtime
does not support parallel `Task` tool invocations, the fallback is
**sequential dispatch** — same prompt, same schema, same merge — at the
cost of wall-clock time. The cap is hard because each subagent reads
roughly 30–80 KB of source per boundary and the orchestrator must hold
all return payloads in memory before merging.

## Versioning

Any breaking change to the schema (field removal, type change, enum
narrowing) requires a `schema_version` bump and a coordinated update of
this file plus `scripts/render_qa_report.py` plus
`scripts/hallucination_guard.py`. Additive changes (new optional fields,
enum widening) are non-breaking and stay on `1.0`.
