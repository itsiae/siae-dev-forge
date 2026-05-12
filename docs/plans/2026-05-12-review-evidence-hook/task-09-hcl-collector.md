# Task 09 — HCL collector (tflint + terraform validate)

**SP:** 1.0 · **AC mappati:** AC #3 · **Dipendenze:** Task 04 · **Wave:** 3

## Goal

Implementare `lib/review_evidence/collectors/hcl.py`: detection (`*.tf` files), invoca `tflint --format json` e `terraform validate -json`. Coverage non applicabile a HCL (campo `null`).

## File coinvolti

**Creare:**
- `lib/review_evidence/collectors/hcl.py`
- `tests/test_review_evidence_collector_hcl.py`
- `tests/fixtures/review-evidence/tflint_output.json`
- `tests/fixtures/review-evidence/terraform_validate.json`

## Step TDD

### Step 1 — Fixture

`tests/fixtures/review-evidence/tflint_output.json`:

```json
{
  "issues": [
    {"rule": {"name": "terraform_unused_declarations", "severity": "warning"},
     "message": "variable \"unused\" is declared but not used",
     "range": {"filename": "main.tf", "start": {"line": 3, "column": 1}}},
    {"rule": {"name": "terraform_required_version", "severity": "error"},
     "message": "missing required_version",
     "range": {"filename": "main.tf", "start": {"line": 1, "column": 1}}}
  ],
  "errors": []
}
```

`tests/fixtures/review-evidence/terraform_validate.json`:

```json
{
  "valid": false,
  "error_count": 1,
  "warning_count": 0,
  "diagnostics": [
    {"severity": "error", "summary": "Reference to undeclared resource",
     "detail": "A managed resource \"aws_s3_bucket\" \"foo\" has not been declared.",
     "range": {"filename": "main.tf", "start": {"line": 10, "column": 5}}}
  ]
}
```

### Step 2 — Test fallente

```python
"""Tests for HCL collector."""
import json
from pathlib import Path
from unittest.mock import patch

from lib.review_evidence.collectors.hcl import HCLCollector

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_tf_file(tmp_path):
    (tmp_path / "main.tf").write_text("# tf")
    assert HCLCollector().is_applicable(tmp_path) is True


def test_not_applicable_otherwise(tmp_path):
    (tmp_path / "README.md").write_text("md")
    assert HCLCollector().is_applicable(tmp_path) is False


def test_collect_with_tflint_and_validate(tmp_path):
    (tmp_path / "main.tf").write_text("# tf")
    tflint_out = (FIX / "tflint_output.json").read_text()
    tfval_out = (FIX / "terraform_validate.json").read_text()

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if cmd[0] == "tflint":
            return CompletedProcess(cmd, 0, stdout=tflint_out, stderr="")
        if cmd[0] == "terraform" and "validate" in cmd:
            return CompletedProcess(cmd, 0, stdout=tfval_out, stderr="")
        return CompletedProcess(cmd, 1, stdout="", stderr="?")

    with patch("lib.review_evidence.collectors.hcl.subprocess.run", side_effect=fake_run):
        result = HCLCollector().collect(tmp_path, "main", "HEAD")

    assert result["stack"] == "hcl"
    assert result["coverage"] is None  # HCL doesn't have coverage
    # 1 tflint error + 1 terraform validate error = 2 errors
    assert result["lint"]["errors"] == 2
    assert result["lint"]["warnings"] == 1  # 1 tflint warning
    assert "tflint" in result["lint"]["source"]
    assert "terraform" in result["lint"]["source"]


def test_collect_missing_tools_returns_lint_none(tmp_path):
    (tmp_path / "main.tf").write_text("# tf")
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    with patch("lib.review_evidence.collectors.hcl.subprocess.run", side_effect=fake_run):
        result = HCLCollector().collect(tmp_path, "main", "HEAD")
    assert result["lint"] is None
```

### Step 3 — Implementa hcl.py

```python
"""HCL stack collector: tflint + terraform validate."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from lib.review_evidence.registry import register


class HCLCollector:
    name = "hcl"

    def is_applicable(self, repo_root: Path) -> bool:
        return any(repo_root.rglob("*.tf"))

    def collect(self, repo_root: Path, base_ref: str, head_ref: str) -> dict[str, Any]:
        return {
            "stack": "hcl",
            "coverage": None,  # N/A for HCL
            "lint": self._aggregate_lint(repo_root),
            "complexity": None,
        }

    def _aggregate_lint(self, repo_root: Path) -> dict[str, Any] | None:
        tflint = self._tflint(repo_root)
        tfval = self._tf_validate(repo_root)
        if tflint is None and tfval is None:
            return None

        errors = 0
        warnings = 0
        findings = []
        sources = []
        if tflint:
            sources.append("tflint")
            errors += tflint["errors"]
            warnings += tflint["warnings"]
            findings.extend(tflint["findings"])
        if tfval:
            sources.append("terraform-validate")
            errors += tfval["errors"]
            warnings += tfval["warnings"]
            findings.extend(tfval["findings"])

        return {"errors": errors, "warnings": warnings, "findings": findings,
                "source": "local:" + "+".join(sources)}

    def _tflint(self, repo_root: Path) -> dict | None:
        try:
            p = subprocess.run(
                ["tflint", "--format", "json"],
                cwd=repo_root, capture_output=True, text=True, timeout=10, check=False,
            )
            data = json.loads(p.stdout or "{}")
            errors = 0
            warnings = 0
            findings = []
            for issue in data.get("issues", []):
                sev = issue.get("rule", {}).get("severity", "warning")
                if sev == "error":
                    errors += 1
                else:
                    warnings += 1
                findings.append({
                    "file": issue.get("range", {}).get("filename"),
                    "line": issue.get("range", {}).get("start", {}).get("line", 0),
                    "rule": issue.get("rule", {}).get("name", "?"),
                    "severity": sev,
                    "msg": issue.get("message", ""),
                })
            return {"errors": errors, "warnings": warnings, "findings": findings}
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None

    def _tf_validate(self, repo_root: Path) -> dict | None:
        try:
            p = subprocess.run(
                ["terraform", "validate", "-json"],
                cwd=repo_root, capture_output=True, text=True, timeout=10, check=False,
            )
            data = json.loads(p.stdout or "{}")
            errors = data.get("error_count", 0)
            warnings = data.get("warning_count", 0)
            findings = []
            for d in data.get("diagnostics", []):
                sev = d.get("severity", "warning")
                findings.append({
                    "file": d.get("range", {}).get("filename"),
                    "line": d.get("range", {}).get("start", {}).get("line", 0),
                    "rule": d.get("summary", "?"),
                    "severity": sev,
                    "msg": d.get("detail", ""),
                })
            return {"errors": errors, "warnings": warnings, "findings": findings}
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(HCLCollector())
```

### Step 4 — Esegui test e commit

```bash
pytest tests/test_review_evidence_collector_hcl.py -v
# 4 passed

git add lib/review_evidence/collectors/hcl.py \
        tests/test_review_evidence_collector_hcl.py \
        tests/fixtures/review-evidence/tflint_output.json \
        tests/fixtures/review-evidence/terraform_validate.json
git commit -m "feat(review-evidence): add HCL collector (tflint+terraform validate) (#task-09)"
```

## Criteri di accettazione

- [ ] `HCLCollector.is_applicable()` rileva file `.tf`
- [ ] `coverage` sempre `None` per HCL
- [ ] Lint aggregato tflint + terraform validate
- [ ] Missing tools graceful (return `None`)
- [ ] 4 test passano
