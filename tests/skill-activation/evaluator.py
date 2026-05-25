#!/usr/bin/env python3
"""Skill Activation Evaluator.

Parsa log JSONL del runner Bedrock, confronta con cases.yml expected,
calcola KPI (accuracy, chain_completeness, forbidden_rate), scrive report markdown.

Usage:
  python3 evaluator.py <log.jsonl> [--label LABEL]
"""
import sys
import json
import yaml
import re
import argparse
from datetime import date
from pathlib import Path


def parse_response(response_text: str) -> dict:
    """Estrai primary skill + chain dal JSON response Bedrock."""
    try:
        m = re.search(r'\{.*\}', response_text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except json.JSONDecodeError:
        pass
    name_match = re.search(r'siae-[a-z-]+|using-devforge', response_text)
    return {"primary": name_match.group(0) if name_match else "UNKNOWN", "chain": []}


def evaluate(cases: list, log_lines: list) -> dict:
    by_id = {entry["id"]: entry for entry in log_lines if "id" in entry}
    results = []
    for case in cases:
        entry = by_id.get(case["id"])
        if not entry or "error" in entry:
            results.append({"id": case["id"], "status": "ERROR", "expected": case.get("expected_primary"), "got": "ERROR"})
            continue
        parsed = parse_response(entry.get("response", ""))
        expected = case["expected_primary"]
        got = parsed.get("primary", "UNKNOWN")
        status = "PASS" if got == expected else "FAIL"
        forbidden = case.get("forbidden", [])
        forbidden_hit = [f for f in forbidden if f in [got] + parsed.get("chain", [])]
        chain = parsed.get("chain", [])
        chain_expected = case.get("expected_chain", [])
        chain_complete = all(s in chain or s == got for s in chain_expected) if chain_expected else None
        results.append({
            "id": case["id"], "status": status, "expected": expected, "got": got,
            "forbidden_hit": forbidden_hit, "chain_complete": chain_complete,
            "prompt": case["prompt"]
        })
    n = len(results)
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    forbidden_count = sum(1 for r in results if r.get("forbidden_hit"))
    chain_results = [r for r in results if r.get("chain_complete") is not None]
    chain_complete_count = sum(1 for r in chain_results if r["chain_complete"])
    return {
        "results": results,
        "kpi": {
            "activation_accuracy": pass_count / n if n else 0,
            "forbidden_rate": forbidden_count / n if n else 0,
            "chain_completeness": chain_complete_count / len(chain_results) if chain_results else 0,
            "total": n, "pass": pass_count, "fail": n - pass_count,
        }
    }


def write_report(report: dict, label: str, out_path: Path) -> None:
    kpi = report["kpi"]
    lines = [
        f"# Skill Activation Report — {label}",
        f"\nDate: {date.today().isoformat()}",
        "\n## KPI\n",
        f"- **activation_accuracy**: {kpi['activation_accuracy']:.1%} ({kpi['pass']}/{kpi['total']})",
        f"- **forbidden_rate**: {kpi['forbidden_rate']:.1%}",
        f"- **chain_completeness**: {kpi['chain_completeness']:.1%}",
        "\n## Per-case results\n",
        "| ID | Status | Expected | Got | Forbidden | Chain |",
        "|---|---|---|---|---|---|",
    ]
    for r in report["results"]:
        fb = ",".join(r.get("forbidden_hit", [])) or "-"
        ch = "OK" if r.get("chain_complete") else ("N/A" if r.get("chain_complete") is None else "INCOMPLETE")
        lines.append(f"| {r['id']} | {r['status']} | {r['expected']} | {r['got']} | {fb} | {ch} |")
    lines.append("\n## Failures detail\n")
    for r in report["results"]:
        if r["status"] != "PASS":
            lines.append(f"\n### {r['id']}\n- Prompt: `{r['prompt']}`\n- Expected: {r['expected']}\n- Got: {r['got']}")
    out_path.write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("log", help="JSONL log from run.sh")
    parser.add_argument("--label", default="run", help="Label for report filename")
    parser.add_argument("--cases", default="cases.yml")
    args = parser.parse_args()

    cases = yaml.safe_load(Path(args.cases).read_text())
    log_lines = [json.loads(l) for l in Path(args.log).read_text().strip().split("\n") if l]
    report = evaluate(cases, log_lines)

    out = Path(f"report-{date.today().isoformat()}-{args.label}.md")
    write_report(report, args.label, out)
    print(f"Report written: {out}")
    print(json.dumps(report["kpi"], indent=2))
    return 0 if report["kpi"]["activation_accuracy"] >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
