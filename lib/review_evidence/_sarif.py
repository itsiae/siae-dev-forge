"""SARIF 2.1.0 parser — tool-agnostic, multi-file aggregator."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# SARIF level → severity bucket
_LEVEL_TO_BUCKET = {
    "error": "critical",
    "warning": "high",
    "note": "low",
    "none": "low",
}


def parse_sarif(content: str) -> dict[str, Any]:
    data = json.loads(content)
    runs = data.get("runs", [])
    if not runs:
        return {"tool_name": "unknown", "problems_critical": 0, "problems_high": 0, "findings": []}

    tool_name = runs[0].get("tool", {}).get("driver", {}).get("name", "unknown")
    critical = 0
    high = 0
    findings = []
    for run in runs:
        for r in run.get("results", []):
            level = r.get("level", "warning")
            bucket = _LEVEL_TO_BUCKET.get(level, "high")
            if bucket == "critical":
                critical += 1
            elif bucket == "high":
                high += 1
            loc_uri = ""
            line = 0
            for loc in r.get("locations", []):
                phys = loc.get("physicalLocation", {})
                loc_uri = phys.get("artifactLocation", {}).get("uri", "")
                line = phys.get("region", {}).get("startLine", 0)
                break
            findings.append({
                "tool": tool_name,
                "rule": r.get("ruleId", "?"),
                "level": level,
                "file": loc_uri,
                "line": line,
                "msg": r.get("message", {}).get("text", ""),
            })
    return {"tool_name": tool_name, "problems_critical": critical, "problems_high": high, "findings": findings}


def aggregate_sarif_dir(path: Path) -> dict[str, Any]:
    critical = 0
    high = 0
    findings = []
    tools = []
    for sarif_file in path.rglob("*.sarif"):
        try:
            parsed = parse_sarif(sarif_file.read_text())
        except Exception:
            continue
        critical += parsed["problems_critical"]
        high += parsed["problems_high"]
        findings.extend(parsed["findings"])
        if parsed["tool_name"] not in tools:
            tools.append(parsed["tool_name"])
    return {
        "problems_critical": critical,
        "problems_high": high,
        "findings": findings,
        "source": "ci:sarif:" + ",".join(tools) if tools else "ci:sarif:none",
    }
