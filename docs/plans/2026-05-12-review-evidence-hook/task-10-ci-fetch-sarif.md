# Task 10 — CI-fetch SARIF parser multi-tool (Qodana/Sonar/CodeQL)

**SP:** 3.5 · **AC mappati:** AC #4, AC #15 · **Dipendenze:** Task 04 · **Wave:** 3

## Goal

Implementare `lib/review_evidence/ci_fetch.py`: pipeline `gh run list` → filter completed → `gh run download` → scan `*.sarif` → parse SARIF 2.1.0 → emit `ci_quality` schema block. Tool-agnostic (Qodana, Sonar, CodeQL — riconosciuti via `runs[].tool.driver.name`).

## File coinvolti

**Creare:**
- `lib/review_evidence/ci_fetch.py`
- `lib/review_evidence/_sarif.py` (parser SARIF 2.1.0)
- `tests/test_review_evidence_ci_fetch.py`
- `tests/fixtures/review-evidence/qodana_sample.sarif`
- `tests/fixtures/review-evidence/sonar_sample.sarif`
- `tests/fixtures/review-evidence/codeql_sample.sarif`

## Step TDD

### Step 1 — Fixture

`tests/fixtures/review-evidence/qodana_sample.sarif`:

```json
{
  "version": "2.1.0",
  "$schema": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/cos02/schemas/sarif-schema-2.1.0.json",
  "runs": [{
    "tool": {"driver": {"name": "Qodana", "version": "2024.3"}},
    "results": [
      {"ruleId": "JavaNullPointerException", "level": "error",
       "message": {"text": "Possible NPE"},
       "locations": [{"physicalLocation": {"artifactLocation": {"uri": "src/main/java/Foo.java"}, "region": {"startLine": 42}}}]},
      {"ruleId": "JavaUnusedImport", "level": "warning",
       "message": {"text": "Unused import"},
       "locations": [{"physicalLocation": {"artifactLocation": {"uri": "src/main/java/Bar.java"}, "region": {"startLine": 5}}}]}
    ]
  }]
}
```

`tests/fixtures/review-evidence/sonar_sample.sarif`:

```json
{
  "version": "2.1.0",
  "runs": [{
    "tool": {"driver": {"name": "SonarQube"}},
    "results": [
      {"ruleId": "java:S1234", "level": "error",
       "message": {"text": "Critical bug"},
       "locations": [{"physicalLocation": {"artifactLocation": {"uri": "src/X.java"}, "region": {"startLine": 10}}}]}
    ]
  }]
}
```

`tests/fixtures/review-evidence/codeql_sample.sarif`:

```json
{
  "version": "2.1.0",
  "runs": [{
    "tool": {"driver": {"name": "CodeQL"}},
    "results": [
      {"ruleId": "py/sql-injection", "level": "error",
       "message": {"text": "SQL injection"},
       "locations": [{"physicalLocation": {"artifactLocation": {"uri": "src/db.py"}, "region": {"startLine": 100}}}]},
      {"ruleId": "py/unused", "level": "note",
       "message": {"text": "Unused"},
       "locations": [{"physicalLocation": {"artifactLocation": {"uri": "src/db.py"}, "region": {"startLine": 5}}}]}
    ]
  }]
}
```

### Step 2 — Test fallente

```python
"""Tests for CI-fetch SARIF parser + gh run download orchestration."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from lib.review_evidence._sarif import parse_sarif, aggregate_sarif_dir
from lib.review_evidence.ci_fetch import fetch_ci_sarif

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_parse_qodana_sarif():
    parsed = parse_sarif((FIX / "qodana_sample.sarif").read_text())
    assert parsed["tool_name"] == "Qodana"
    assert parsed["problems_critical"] == 1
    assert parsed["problems_high"] == 1
    assert len(parsed["findings"]) == 2


def test_parse_sonar_sarif():
    parsed = parse_sarif((FIX / "sonar_sample.sarif").read_text())
    assert parsed["tool_name"] == "SonarQube"
    assert parsed["problems_critical"] == 1
    assert parsed["problems_high"] == 0


def test_parse_codeql_sarif():
    parsed = parse_sarif((FIX / "codeql_sample.sarif").read_text())
    assert parsed["tool_name"] == "CodeQL"
    assert parsed["problems_critical"] == 1
    # level=note → not counted as critical/high (informational)
    assert parsed["problems_high"] == 0


def test_aggregate_sarif_dir(tmp_path):
    (tmp_path / "qodana.sarif").write_text((FIX / "qodana_sample.sarif").read_text())
    (tmp_path / "sonar.sarif").write_text((FIX / "sonar_sample.sarif").read_text())

    agg = aggregate_sarif_dir(tmp_path)
    assert agg["problems_critical"] == 2  # 1 qodana + 1 sonar
    assert agg["problems_high"] == 1      # 1 qodana
    assert "Qodana" in agg["source"]
    assert "SonarQube" in agg["source"]


def test_fetch_ci_sarif_no_runs(tmp_path):
    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if cmd[0] == "gh" and "list" in cmd:
            return CompletedProcess(cmd, 0, stdout="[]", stderr="")
        return CompletedProcess(cmd, 1, stdout="", stderr="?")

    with patch("lib.review_evidence.ci_fetch.subprocess.run", side_effect=fake_run):
        result = fetch_ci_sarif(sha="abc123", repo_root=tmp_path)
    assert result["available"] is False
    assert "no completed" in result["reason"].lower() or "no runs" in result["reason"].lower()


def test_fetch_ci_sarif_with_download(tmp_path, monkeypatch):
    runs_listing = json.dumps([
        {"databaseId": 9876, "workflowName": "Qodana", "conclusion": "success"}
    ])

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if cmd[0] == "gh" and "list" in cmd:
            return CompletedProcess(cmd, 0, stdout=runs_listing, stderr="")
        if cmd[0] == "gh" and "download" in cmd:
            # Simulate gh run download placing a sarif file in --dir
            dl_dir = Path(cmd[cmd.index("--dir") + 1])
            dl_dir.mkdir(parents=True, exist_ok=True)
            (dl_dir / "qodana.sarif").write_text((FIX / "qodana_sample.sarif").read_text())
            return CompletedProcess(cmd, 0, stdout="", stderr="")
        return CompletedProcess(cmd, 1, stdout="", stderr="?")

    with patch("lib.review_evidence.ci_fetch.subprocess.run", side_effect=fake_run):
        result = fetch_ci_sarif(sha="abc123", repo_root=tmp_path)

    assert result["available"] is True
    assert result["problems_critical"] == 1
    assert result["problems_high"] == 1
    assert "qodana" in result["source"].lower()


def test_fetch_ci_sarif_gh_missing(tmp_path):
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("gh")

    with patch("lib.review_evidence.ci_fetch.subprocess.run", side_effect=fake_run):
        result = fetch_ci_sarif(sha="abc", repo_root=tmp_path)
    assert result["available"] is False
    assert "gh" in result["reason"].lower()
```

### Step 3 — Implementa _sarif.py

```python
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
```

### Step 4 — Implementa ci_fetch.py

```python
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
```

### Step 5 — Esegui test e commit

```bash
pytest tests/test_review_evidence_ci_fetch.py -v
# 7 passed atteso

git add lib/review_evidence/_sarif.py lib/review_evidence/ci_fetch.py \
        tests/test_review_evidence_ci_fetch.py \
        tests/fixtures/review-evidence/qodana_sample.sarif \
        tests/fixtures/review-evidence/sonar_sample.sarif \
        tests/fixtures/review-evidence/codeql_sample.sarif
git commit -m "feat(review-evidence): add CI-fetch SARIF parser multi-tool (#task-10)"
```

## Criteri di accettazione

- [ ] SARIF 2.1.0 parser estrae tool_name, level, ruleId, location
- [ ] Multi-tool: Qodana + Sonar + CodeQL fixture parsate correttamente
- [ ] `level=error` → critical; `level=warning` → high; `level=note` → escluso
- [ ] `aggregate_sarif_dir()` somma findings da multipli `*.sarif`
- [ ] `fetch_ci_sarif()` integra `gh run list` + `gh run download`
- [ ] Graceful: `gh` missing / no runs / timeout → `available=false` con reason
- [ ] 7 test passano
