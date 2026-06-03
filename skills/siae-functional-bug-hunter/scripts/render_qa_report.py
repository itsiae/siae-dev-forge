#!/usr/bin/env python3
"""render_qa_report.py — deterministic JSON → Markdown renderer for QA reports.

Contract
--------
Input: a `qa_report.json` file matching the QAReport schema declared in
       `references/qa_report_json_schema.md`.
Output: a `qa_report.md` file rendered from the JSON.

Determinism
-----------
- Header timestamp comes from `qa_report.json:generated_at`, NEVER from
  `datetime.now()`. Given the same JSON, the output is byte-stable.
- Findings are sorted SEV-1 → SEV-2 → SEV-3 → SEV-4, then by `dedup_key`
  ascending alphabetically.
- Journey ordinals are reassigned during rendering in the order journeys
  first appear under the sort above.

Exit codes
----------
0  success.
1  validation failure against the aggregate SubagentResult / QAReport
   schema (missing required field, wrong enum value, etc.).
2  argv / IO error.

Usage
-----
    python3 render_qa_report.py qa_report.json [qa_report.md]

If the output path is omitted, the markdown is written to stdout.

Python 3.9+ standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"

VALID_SEVERITIES = ("SEV-1", "SEV-2", "SEV-3", "SEV-4")
VALID_CATEGORIES = {
    "auth-bypass", "data-race", "toctou", "webhook-replay",
    "cache-staleness", "cursor-drift", "dst-skip",
    "input-validation", "business-logic", "other",
}
VALID_REPRO = {"deterministic", "95%", "80%", "<80%-needs-harness"}
VALID_MODES = {"interactive", "strict", "report-only"}
VALID_CONFIDENCE = {"high", "medium", "low_partial",
                    "low_model_tier", "low_pattern_match"}
VALID_LANGS = {"en", "it"}

REPORT_REQUIRED = {
    "schema_version", "run_id", "generated_at", "skill_semver",
    "model_id", "mode", "lang", "findings",
}
FINDING_REQUIRED = {
    "dedup_key", "finding_id", "entry_point_id", "journey",
    "title", "severity", "severity_rubric_row", "pattern_id",
    "category", "preconditions", "steps", "expected", "actual",
    "evidence", "suggested_fix_direction", "reproduction_rate_target",
    "confidence",
}


def validate(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["report must be a JSON object"]

    missing = REPORT_REQUIRED - report.keys()
    if missing:
        errors.append(f"report missing fields: {sorted(missing)}")

    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"schema_version: expected {SCHEMA_VERSION!r}, "
            f"got {report.get('schema_version')!r}"
        )
    if report.get("mode") not in VALID_MODES:
        errors.append(f"mode invalid: {report.get('mode')!r}")
    if report.get("lang") not in VALID_LANGS:
        errors.append(f"lang invalid: {report.get('lang')!r}")
    if report.get("confidence") is not None and report["confidence"] not in VALID_CONFIDENCE:
        errors.append(f"confidence invalid: {report['confidence']!r}")

    findings = report.get("findings")
    if not isinstance(findings, list):
        errors.append("findings must be an array")
        return errors

    for idx, f in enumerate(findings):
        prefix = f"findings[{idx}]"
        if not isinstance(f, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        miss = FINDING_REQUIRED - f.keys()
        if miss:
            errors.append(f"{prefix}: missing fields {sorted(miss)}")
        if f.get("severity") not in VALID_SEVERITIES:
            errors.append(f"{prefix}.severity invalid: {f.get('severity')!r}")
        if f.get("category") not in VALID_CATEGORIES:
            errors.append(f"{prefix}.category invalid: {f.get('category')!r}")
        if f.get("reproduction_rate_target") not in VALID_REPRO:
            errors.append(
                f"{prefix}.reproduction_rate_target invalid: "
                f"{f.get('reproduction_rate_target')!r}"
            )
        if f.get("confidence") not in VALID_CONFIDENCE:
            errors.append(f"{prefix}.confidence invalid: {f.get('confidence')!r}")
        dk = f.get("dedup_key")
        if not isinstance(dk, str) or len(dk) != 16 or any(c not in "0123456789abcdef" for c in dk):
            errors.append(f"{prefix}.dedup_key invalid: {dk!r}")
        preconds = f.get("preconditions") or []
        if not isinstance(preconds, list) or not preconds:
            errors.append(f"{prefix}.preconditions must be a non-empty array")
        steps = f.get("steps") or []
        if not isinstance(steps, list) or not steps:
            errors.append(f"{prefix}.steps must be a non-empty array")

    return errors


def severity_rank(sev: str) -> int:
    # Lower rank value = higher severity = appears first
    return VALID_SEVERITIES.index(sev)


def sorted_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        findings,
        key=lambda f: (severity_rank(f["severity"]), f["dedup_key"]),
    )


def assign_journey_ordinals(findings: list[dict[str, Any]]) -> dict[str, str]:
    """Reassign J-NNN ordinals in the order they first appear under sort."""
    mapping: dict[str, str] = {}
    counter = 1
    for f in findings:
        original = f["journey"]
        if original.endswith("-misc"):
            mapping[original] = "J-000-misc"
            continue
        if original not in mapping:
            mapping[original] = f"J-{counter:03d}"
            counter += 1
    return mapping


def count_by_sev(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {s: 0 for s in VALID_SEVERITIES}
    for f in findings:
        counts[f["severity"]] += 1
    return counts


def render(report: dict[str, Any]) -> str:
    findings = sorted_findings(report["findings"])
    journey_map = assign_journey_ordinals(findings)
    counts = count_by_sev(findings)

    out: list[str] = []
    out.append("# Functional bug report")
    out.append("")
    out.append(f"- **Run id**: {report['run_id']}")
    if report.get("scope_hash"):
        out.append(f"- **Scope hash**: {report['scope_hash']}")
    out.append(f"- **Skill semver**: {report['skill_semver']}")
    out.append(f"- **Model id**: {report['model_id']}")
    out.append(f"- **Mode**: {report['mode']}")
    out.append(f"- **Generated at**: {report['generated_at']}")
    if report.get("confidence"):
        out.append(f"- **Confidence (global)**: {report['confidence']}")
    out.append(
        f"- **Findings**: {counts['SEV-1']} SEV-1 · {counts['SEV-2']} SEV-2 · "
        f"{counts['SEV-3']} SEV-3 · {counts['SEV-4']} SEV-4"
    )
    out.append(f"- **Lang**: {report['lang']}")
    out.append("")

    # Index table
    out.append("## Index")
    out.append("")
    out.append("| Finding | Journey | Severity | Title | Entry point |")
    out.append("|---|---|---|---|---|")
    for f in findings:
        j = journey_map[f["journey"]]
        out.append(
            f"| {f['finding_id']} | {j} | {f['severity']} | "
            f"{f['title']} | {f['entry_point_id']} |"
        )
    out.append("")

    # Group by journey in sort order
    by_journey: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for f in findings:
        j = journey_map[f["journey"]]
        if j not in by_journey:
            by_journey[j] = []
            order.append(j)
        by_journey[j].append(f)

    for j in order:
        out.append(f"## Journey {j}")
        out.append("")
        for f in by_journey[j]:
            out.append(f"### {f['finding_id']} — {f['title']}")
            out.append("")
            out.append(f"- **Severity**: {f['severity']} (rubric row {f['severity_rubric_row']})")
            out.append(f"- **Pattern**: {f['pattern_id']}")
            out.append(f"- **Category**: {f['category']}")
            out.append(f"- **Entry point**: {f['entry_point_id']}")
            out.append(f"- **Confidence**: {f['confidence']}")
            out.append("")
            out.append("**Preconditions**")
            out.append("")
            for p in f["preconditions"]:
                out.append(f"- {p}")
            out.append("")
            out.append("**Steps**")
            out.append("")
            for i, s in enumerate(f["steps"], 1):
                out.append(f"{i}. {s}")
            out.append("")
            out.append("**Expected result**")
            out.append("")
            out.append(f["expected"])
            out.append("")
            out.append("**Actual result**")
            out.append("")
            out.append(f["actual"])
            out.append("")
            if f.get("evidence"):
                out.append("**Evidence**")
                out.append("")
                for ev in f["evidence"]:
                    dirty = "+dirty" if ev.get("dirty_flag") else ""
                    out.append(
                        f"- `{ev['file']}:{ev['line_start']}-{ev['line_end']}` "
                        f"@ `{ev['sha']}`{dirty}"
                    )
                    out.append(f"  > {ev['excerpt']}")
                out.append("")
            out.append("**Suggested fix direction**")
            out.append("")
            out.append(f["suggested_fix_direction"])
            out.append("")
            out.append("**Reproduction rate target**")
            out.append("")
            out.append(f"`{f['reproduction_rate_target']}`")
            out.append("")
            if f.get("boundary_observations"):
                out.append("**Boundary observations**")
                out.append("")
                for b in f["boundary_observations"]:
                    out.append(f"- {b}")
                out.append("")
            out.append("---")
            out.append("")

    return "\n".join(out).rstrip() + "\n"


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("input_json", help="Path to qa_report.json")
    p.add_argument("output_md", nargs="?", default="-",
                   help="Path to qa_report.md (default: stdout)")
    args = p.parse_args(argv)

    try:
        report = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        sys.stderr.write(f"[render_qa_report] cannot read {args.input_json}: {e}\n")
        return 2

    errs = validate(report)
    if errs:
        sys.stderr.write("[render_qa_report] schema validation failed:\n")
        for e in errs:
            sys.stderr.write(f"  - {e}\n")
        return 1

    md = render(report)
    if args.output_md == "-":
        sys.stdout.write(md)
    else:
        Path(args.output_md).write_text(md, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
