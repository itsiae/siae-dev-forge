#!/usr/bin/env python3
"""hallucination_guard.py — machine-enforced post-emit gate for qa_report.json.

Replaces the prose 5-checkbox Hallucination Guard with a deterministic
verifier. Runs between `qa_report.json` emission (Phase 8a) and
`qa_report.md` rendering via `scripts/render_qa_report.py` (Phase 8b).

Checks
------
- HG-01: every finding has a non-empty preconditions array (≥1 item).
- HG-02: every finding has a steps array with ≥2 items.
- HG-03: dedup_key is unique in the report (no duplicates).
- HG-04: reproduction_rate_target is one of the enum values.
- HG-05: no two findings share an identical title (case-insensitive).

Output
------
On stdout / stderr: one violation per line, format
    FINDING:<dedup_key>:HG-0N:<description>

Exit codes
----------
0  pass.
1  one or more violations found.
2  JSON parse error / IO error.

Usage
-----
    python3 hallucination_guard.py qa_report.json

The orchestrator MUST treat a non-zero exit code as a hard block — it
must NOT proceed to render_qa_report.py until this script exits 0.

Python 3.9+ standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


VALID_REPRO = {"deterministic", "95%", "80%", "<80%-needs-harness"}


def check_finding(idx: int, f: dict[str, Any]) -> list[str]:
    """Return violation strings (empty if all checks pass) for one finding."""
    violations: list[str] = []
    dk = f.get("dedup_key") or f"<no-dedup-key:idx={idx}>"

    # HG-01: preconditions ≥ 1
    preconds = f.get("preconditions") or []
    if not isinstance(preconds, list) or len(preconds) < 1:
        violations.append(
            f"FINDING:{dk}:HG-01:preconditions must be a non-empty array "
            f"(got {type(preconds).__name__} len={len(preconds) if isinstance(preconds, list) else 'N/A'})"
        )

    # HG-02: steps ≥ 2
    steps = f.get("steps") or []
    if not isinstance(steps, list) or len(steps) < 2:
        violations.append(
            f"FINDING:{dk}:HG-02:steps must have at least 2 items "
            f"(got len={len(steps) if isinstance(steps, list) else 'N/A'})"
        )

    # HG-04: reproduction_rate_target enum
    rrt = f.get("reproduction_rate_target")
    if rrt not in VALID_REPRO:
        violations.append(
            f"FINDING:{dk}:HG-04:reproduction_rate_target {rrt!r} "
            f"not in {sorted(VALID_REPRO)}"
        )

    return violations


def check_report(report: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    findings = report.get("findings")
    if not isinstance(findings, list):
        violations.append("FINDING:<report>:HG-00:findings is not an array")
        return violations

    # Per-finding checks (HG-01, HG-02, HG-04)
    for idx, f in enumerate(findings):
        if not isinstance(f, dict):
            violations.append(
                f"FINDING:<idx={idx}>:HG-00:finding is not an object "
                f"({type(f).__name__})"
            )
            continue
        violations.extend(check_finding(idx, f))

    # HG-03: dedup_key uniqueness across the report
    seen_keys: dict[str, int] = {}
    for idx, f in enumerate(findings):
        if not isinstance(f, dict):
            continue
        dk = f.get("dedup_key")
        if not isinstance(dk, str):
            # Already flagged by HG-00 path or schema validation; skip.
            continue
        if dk in seen_keys:
            violations.append(
                f"FINDING:{dk}:HG-03:duplicate dedup_key "
                f"(also seen at findings[{seen_keys[dk]}], now at findings[{idx}])"
            )
        else:
            seen_keys[dk] = idx

    # HG-05: title uniqueness case-insensitive across the report
    seen_titles: dict[str, str] = {}  # normalized title -> first dedup_key
    for f in findings:
        if not isinstance(f, dict):
            continue
        title = f.get("title")
        dk = f.get("dedup_key", "<no-dedup-key>")
        if not isinstance(title, str):
            continue
        norm = title.strip().lower()
        if not norm:
            continue
        if norm in seen_titles:
            violations.append(
                f"FINDING:{dk}:HG-05:title duplicates an earlier finding "
                f"(case-insensitive match with {seen_titles[norm]!r})"
            )
        else:
            seen_titles[norm] = dk

    return violations


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("input_json", help="Path to qa_report.json")
    args = p.parse_args(argv)

    try:
        report = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    except OSError as e:
        sys.stderr.write(f"[hallucination_guard] cannot read {args.input_json}: {e}\n")
        return 2
    except json.JSONDecodeError as e:
        sys.stderr.write(f"[hallucination_guard] invalid JSON in {args.input_json}: {e}\n")
        return 2

    violations = check_report(report)
    if not violations:
        sys.stdout.write(
            f"[hallucination_guard] PASS: {len(report.get('findings', []))} "
            f"findings, 0 violations\n"
        )
        return 0

    for v in violations:
        sys.stderr.write(v + "\n")
    sys.stderr.write(
        f"[hallucination_guard] FAIL: {len(violations)} violations\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
