"""CI-fetch — orchestrate gh run download + SARIF aggregation."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from lib.review_evidence._sarif import aggregate_sarif_dir

GH_TIMEOUT_SEC = 30


def _empty(reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "ci_run_id": None,
        "problems_critical": 0,
        "problems_high": 0,
        "findings": [],
        "source": None,
        "reason": reason,
    }


def fetch_ci_sarif(sha: str, repo_root: Path) -> dict[str, Any]:
    """Discover completed CI runs for sha, download artifacts, parse SARIF, aggregate."""
    try:
        p = subprocess.run(
            ["gh", "run", "list", "--commit", sha, "--limit", "10",
             "--json", "databaseId,workflowName,conclusion"],
            cwd=repo_root, capture_output=True, text=True, timeout=GH_TIMEOUT_SEC, check=False,
        )
    except FileNotFoundError:
        return _empty("gh CLI not installed")
    except subprocess.TimeoutExpired:
        return _empty("gh run list timeout")

    try:
        runs = json.loads(p.stdout or "[]")
    except json.JSONDecodeError:
        return _empty("gh run list returned invalid JSON")

    completed = [r for r in runs if r.get("conclusion") in ("success", "failure", "neutral")]
    if not completed:
        return _empty("no completed CI runs for this sha")

    aggregated_critical = 0
    aggregated_high = 0
    findings: list[Any] = []
    tool_names: list[str] = []
    last_run_id: Any = None

    with tempfile.TemporaryDirectory(prefix="review-evidence-ci-") as tmp:
        tmp_path = Path(tmp)
        for run in completed:
            run_id = run["databaseId"]
            last_run_id = run_id
            run_dir = tmp_path / str(run_id)
            try:
                subprocess.run(
                    ["gh", "run", "download", str(run_id), "--dir", str(run_dir)],
                    cwd=repo_root, capture_output=True, text=True,
                    timeout=GH_TIMEOUT_SEC, check=False,
                )
            except subprocess.TimeoutExpired:
                continue
            except FileNotFoundError:
                return _empty("gh disappeared mid-run")

            if not run_dir.exists():
                continue
            agg = aggregate_sarif_dir(run_dir)
            aggregated_critical += agg["problems_critical"]
            aggregated_high += agg["problems_high"]
            findings.extend(agg["findings"])
            if agg["source"] and agg["source"] != "ci:sarif:none":
                for t in agg["source"].replace("ci:sarif:", "").split(","):
                    if t and t not in tool_names:
                        tool_names.append(t)

    if not tool_names:
        return _empty("no SARIF artefacts in completed runs")

    return {
        "available": True,
        "ci_run_id": str(last_run_id),
        "problems_critical": aggregated_critical,
        "problems_high": aggregated_high,
        "findings": findings,
        "source": "ci:sarif:" + ",".join(tool_names),
    }
