#!/usr/bin/env python3
"""parse_coverage.py — parser deterministico di coverage report.

Sostituisce il pattern fragile `tail -n 100 + grep` con parsing JSON tipato
da reporter standardizzati: --coverage.reporter=json-summary (Vitest/Jest),
--cov-report=json (pytest), JaCoCo XML, etc.

Usage:
    python3 parse_coverage.py <framework> <input-file>

Frameworks supportati:
    vitest, jest, pytest, jacoco, kover, go-test, cargo, dotnet

Output (stdout): JSON con schema:
    {
        "global_pct": float,
        "global_branch_pct": float,
        "modules": [
            {"path": str, "lines_pct": float, "branch_pct": float,
             "priority": "P1"|"P2"|"P3"|null, "threshold": float, "status": "PASS"|"FAIL"}
        ],
        "failing": [str],
        "framework": str,
        "error": str | null
    }

Exit code: 0 in tutti i casi (parse error veicolato in JSON `error` field).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEFAULT_THRESHOLDS = {"P1": 80.0, "P2": 70.0, "P3": 60.0, "default": 70.0}


def parse_vitest_or_jest(data: dict) -> tuple[float, float, list[dict]]:
    total = data.get("total", {})
    global_pct = float(total.get("lines", {}).get("pct", 0))
    global_branch_pct = float(total.get("branches", {}).get("pct", 0))
    modules = []
    for path, metrics in data.items():
        if path == "total":
            continue
        if not isinstance(metrics, dict):
            continue
        lines_pct = float(metrics.get("lines", {}).get("pct", 0))
        branch_pct = float(metrics.get("branches", {}).get("pct", 0))
        modules.append({
            "path": path,
            "lines_pct": lines_pct,
            "branch_pct": branch_pct,
        })
    return global_pct, global_branch_pct, modules


def parse_pytest_cov(data: dict) -> tuple[float, float, list[dict]]:
    totals = data.get("totals", {})
    global_pct = float(totals.get("percent_covered", 0))
    num_branches = totals.get("num_branches", 0)
    covered_branches = totals.get("covered_branches", 0)
    global_branch_pct = (covered_branches / num_branches * 100) if num_branches else 0.0
    modules = []
    for path, info in data.get("files", {}).items():
        summary = info.get("summary", {})
        nb = summary.get("num_branches", 0)
        cb = summary.get("covered_branches", 0)
        modules.append({
            "path": path,
            "lines_pct": float(summary.get("percent_covered", 0)),
            "branch_pct": (cb / nb * 100) if nb else 0.0,
        })
    return global_pct, global_branch_pct, modules


def parse_jacoco_xml(content: str) -> tuple[float, float, list[dict]]:
    line_match = re.search(r'<counter type="LINE" missed="(\d+)" covered="(\d+)"', content)
    branch_match = re.search(r'<counter type="BRANCH" missed="(\d+)" covered="(\d+)"', content)
    if not line_match:
        return 0.0, 0.0, []
    line_missed, line_covered = int(line_match.group(1)), int(line_match.group(2))
    line_total = line_missed + line_covered
    global_pct = (line_covered / line_total * 100) if line_total else 0.0
    if branch_match:
        b_missed, b_covered = int(branch_match.group(1)), int(branch_match.group(2))
        b_total = b_missed + b_covered
        global_branch_pct = (b_covered / b_total * 100) if b_total else 0.0
    else:
        global_branch_pct = 0.0
    modules = []
    for pkg in re.finditer(r'<package name="([^"]+)">(.*?)</package>', content, re.DOTALL):
        pkg_name = pkg.group(1)
        pkg_body = pkg.group(2)
        pkg_line = re.search(r'<counter type="LINE" missed="(\d+)" covered="(\d+)"', pkg_body)
        if pkg_line:
            pm, pc = int(pkg_line.group(1)), int(pkg_line.group(2))
            pt = pm + pc
            modules.append({
                "path": pkg_name.replace("/", "."),
                "lines_pct": (pc / pt * 100) if pt else 0.0,
                "branch_pct": 0.0,
            })
    return global_pct, global_branch_pct, modules


def parse_go_cover(content: str) -> tuple[float, float, list[dict]]:
    modules: dict[str, list[float]] = {}
    global_pct = 0.0
    for line in content.splitlines():
        m = re.match(r'^([^:]+\.go):\d+:\s+\S+\s+(\d+\.?\d*)%', line)
        if m:
            path = m.group(1)
            pct = float(m.group(2))
            modules.setdefault(path, []).append(pct)
            continue
        total_m = re.search(r'^total:\s+\(statements\)\s+(\d+\.?\d*)%', line)
        if total_m:
            global_pct = float(total_m.group(1))
    module_list = [
        {"path": p, "lines_pct": sum(pcts) / len(pcts), "branch_pct": 0.0}
        for p, pcts in modules.items()
    ]
    return global_pct, 0.0, module_list


def parse_cargo_tarpaulin(data: dict) -> tuple[float, float, list[dict]]:
    files_data = data.get("files", [])
    total_covered = sum(f.get("covered", 0) for f in files_data)
    total_coverable = sum(f.get("coverable", 0) for f in files_data)
    global_pct = (total_covered / total_coverable * 100) if total_coverable else 0.0
    modules = []
    for f in files_data:
        cov = f.get("covered", 0)
        coverable = f.get("coverable", 0)
        modules.append({
            "path": f.get("path", "unknown"),
            "lines_pct": (cov / coverable * 100) if coverable else 0.0,
            "branch_pct": 0.0,
        })
    return global_pct, 0.0, modules


def assign_priority_and_threshold(
    path: str, priority_rules: dict | None
) -> tuple[str | None, float]:
    if not priority_rules:
        return None, DEFAULT_THRESHOLDS["default"]
    levels = priority_rules.get("priority_levels", {})
    for level_name in ("P1", "P2", "P3"):
        level = levels.get(level_name, {})
        patterns = level.get("path_patterns", [])
        for pattern in patterns:
            regex = pattern.replace("**/", ".*/").replace("**", ".*").replace("*", "[^/]*")
            if re.search(regex, path):
                return level_name, float(level.get("min_coverage_pct", DEFAULT_THRESHOLDS["default"]))
    return None, DEFAULT_THRESHOLDS["default"]


def load_priority_rules(skill_root: Path) -> dict | None:
    rules_path = skill_root / "assets" / "priority-rules.json"
    if rules_path.exists():
        with open(rules_path) as f:
            return json.load(f)
    return None


def parse(framework: str, input_path: Path, priority_rules: dict | None) -> dict:
    if not input_path.exists():
        return {
            "global_pct": 0.0,
            "global_branch_pct": 0.0,
            "modules": [],
            "failing": [],
            "framework": framework,
            "error": f"Input file does not exist: {input_path}",
        }
    try:
        if framework in ("jacoco", "kover"):
            content = input_path.read_text()
            global_pct, branch_pct, modules = parse_jacoco_xml(content)
        elif framework == "go-test":
            content = input_path.read_text()
            global_pct, branch_pct, modules = parse_go_cover(content)
        else:
            with open(input_path) as f:
                data = json.load(f)
            if framework in ("vitest", "jest"):
                global_pct, branch_pct, modules = parse_vitest_or_jest(data)
            elif framework == "pytest":
                global_pct, branch_pct, modules = parse_pytest_cov(data)
            elif framework == "cargo":
                global_pct, branch_pct, modules = parse_cargo_tarpaulin(data)
            elif framework == "dotnet":
                content = input_path.read_text()
                global_pct, branch_pct, modules = parse_jacoco_xml(content)
            else:
                return {
                    "global_pct": 0.0,
                    "global_branch_pct": 0.0,
                    "modules": [],
                    "failing": [],
                    "framework": framework,
                    "error": f"Framework non supportato: {framework}",
                }
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "global_pct": 0.0,
            "global_branch_pct": 0.0,
            "modules": [],
            "failing": [],
            "framework": framework,
            "error": f"Parse error: {e}",
        }

    enriched = []
    failing = []
    for m in modules:
        pri, threshold = assign_priority_and_threshold(m["path"], priority_rules)
        status = "PASS" if m["lines_pct"] >= threshold else "FAIL"
        enriched.append({**m, "priority": pri, "threshold": threshold, "status": status})
        if status == "FAIL":
            failing.append(m["path"])

    return {
        "global_pct": round(global_pct, 2),
        "global_branch_pct": round(branch_pct, 2),
        "modules": enriched,
        "failing": failing,
        "framework": framework,
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "framework",
        choices=["vitest", "jest", "pytest", "jacoco", "kover", "go-test", "cargo", "dotnet"],
    )
    parser.add_argument("input", type=Path, help="Input file (json-summary, lcov, xml, etc.)")
    parser.add_argument(
        "--skill-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Path skill root (per priority-rules.json)",
    )
    args = parser.parse_args()

    priority_rules = load_priority_rules(args.skill_root)
    result = parse(args.framework, args.input, priority_rules)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
