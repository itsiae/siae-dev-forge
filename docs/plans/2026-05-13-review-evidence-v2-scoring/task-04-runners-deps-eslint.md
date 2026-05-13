# Task 04 — Runner pip-audit + npm-audit + eslint-security

**SP:** 1.5 · **AC mappati:** AC #11 · **Dipendenze:** Task 03 (registry) · **Wave:** 1b

## Goal

3 runner MVP aggiuntivi che chiudono i 5 totali del MVP scope (post W1 iter1 fix):
- `pip-audit` — Python deps vulnerabilities
- `npm-audit` — TS/JS deps vulnerabilities
- `eslint-security` — TS/JS security (plugin eslint-plugin-security)

Stesso pattern Task 03: subprocess + try/except + register + SecurityFindings normalized output.

## File coinvolti

**Creare:**
- `lib/review_evidence/runners/pip_audit.py`
- `lib/review_evidence/runners/npm_audit.py`
- `lib/review_evidence/runners/eslint_security.py`
- `tests/test_review_evidence_runner_pip_audit.py`
- `tests/test_review_evidence_runner_npm_audit.py`
- `tests/test_review_evidence_runner_eslint_security.py`
- `tests/fixtures/review-evidence/pip_audit_output.json`
- `tests/fixtures/review-evidence/npm_audit_output.json`
- `tests/fixtures/review-evidence/eslint_security_output.json`

## Step TDD

### Step 1 — Fixture

`pip_audit_output.json` (pip-audit `-f json`):

```json
{
  "dependencies": [
    {"name": "django", "version": "3.2.0", "vulns": [
      {"id": "GHSA-xxxx", "severity": "HIGH", "fix_versions": ["3.2.13"]}
    ]},
    {"name": "requests", "version": "2.20.0", "vulns": [
      {"id": "GHSA-yyyy", "severity": "MEDIUM", "fix_versions": ["2.31.0"]}
    ]}
  ]
}
```

`npm_audit_output.json` (npm audit `--json`):

```json
{
  "vulnerabilities": {
    "lodash": {"severity": "critical", "via": ["CVE-2021-23337"], "fixAvailable": true},
    "axios": {"severity": "high", "via": ["CVE-2023-45857"], "fixAvailable": true}
  },
  "metadata": {
    "vulnerabilities": {"critical": 1, "high": 1, "moderate": 0, "low": 0, "info": 0, "total": 2}
  }
}
```

`eslint_security_output.json` (eslint `--format json` con plugin security):

```json
[
  {"filePath": "/repo/src/api.js", "messages": [
    {"ruleId": "security/detect-eval-with-expression", "severity": 2,
     "message": "Found eval()", "line": 15, "column": 5}
  ], "errorCount": 1, "warningCount": 0}
]
```

### Step 2 — Test fallente (3 file test base)

`test_review_evidence_runner_pip_audit.py`:

```python
"""Tests for pip-audit runner."""
import json
from pathlib import Path
from unittest.mock import patch
from lib.review_evidence.runners.pip_audit import PipAuditRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_requirements_txt(tmp_path):
    (tmp_path / "requirements.txt").write_text("django==3.2.0")
    assert PipAuditRunner().is_applicable(tmp_path) is True


def test_is_applicable_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")
    assert PipAuditRunner().is_applicable(tmp_path) is True


def test_not_applicable_non_python(tmp_path):
    assert PipAuditRunner().is_applicable(tmp_path) is False


def test_run_parses_severities(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")
    out = (FIX / "pip_audit_output.json").read_text()
    def fake_run(cmd, **kw):
        from subprocess import CompletedProcess
        return CompletedProcess(cmd, 1, stdout=out, stderr="")  # exit 1 when vulns
    with patch("lib.review_evidence.runners.pip_audit.subprocess.run", side_effect=fake_run):
        result = PipAuditRunner().run(tmp_path)
    assert result.high == 1
    assert result.medium == 1
    assert result.critical == 0


def test_run_missing_tool_returns_none(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")
    with patch("lib.review_evidence.runners.pip_audit.subprocess.run",
                side_effect=FileNotFoundError("pip-audit")):
        assert PipAuditRunner().run(tmp_path) is None
```

`test_review_evidence_runner_npm_audit.py` (analoghi 5 test).
`test_review_evidence_runner_eslint_security.py` (analoghi 5 test).

### Step 3 — Implementa 3 runner

`lib/review_evidence/runners/pip_audit.py`:

```python
"""pip-audit Python deps vulnerability runner."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.scoring import SecurityFindings
from lib.review_evidence.runners._registry import register


class PipAuditRunner:
    name = "pip-audit"
    category = "deps"

    def is_applicable(self, repo_root: Path) -> bool:
        return any((repo_root / f).exists() for f in
                    ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"])

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        try:
            p = subprocess.run(
                ["pip-audit", "-f", "json", "--quiet"],
                cwd=repo_root, capture_output=True, text=True,
                timeout=60, check=False,
            )
            if not p.stdout.strip():
                return SecurityFindings()
            data = json.loads(p.stdout)
            critical = high = medium = low = 0
            for dep in data.get("dependencies", []):
                for vuln in dep.get("vulns", []):
                    sev = vuln.get("severity", "").upper()
                    if sev == "CRITICAL":
                        critical += 1
                    elif sev == "HIGH":
                        high += 1
                    elif sev == "MEDIUM":
                        medium += 1
                    else:
                        low += 1
            return SecurityFindings(critical=critical, high=high, medium=medium, low=low)
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(PipAuditRunner())
```

`lib/review_evidence/runners/npm_audit.py`:

```python
"""npm audit TS/JS deps vulnerability runner."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.scoring import SecurityFindings
from lib.review_evidence.runners._registry import register


class NpmAuditRunner:
    name = "npm-audit"
    category = "deps"

    def is_applicable(self, repo_root: Path) -> bool:
        return (repo_root / "package.json").exists()

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        try:
            p = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=repo_root, capture_output=True, text=True,
                timeout=60, check=False,
            )
            if not p.stdout.strip():
                return SecurityFindings()
            data = json.loads(p.stdout)
            counts = data.get("metadata", {}).get("vulnerabilities", {})
            # npm audit uses "moderate" instead of "medium"
            return SecurityFindings(
                critical=counts.get("critical", 0),
                high=counts.get("high", 0),
                medium=counts.get("moderate", 0),
                low=counts.get("low", 0),
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(NpmAuditRunner())
```

`lib/review_evidence/runners/eslint_security.py`:

```python
"""ESLint security plugin runner (TS/JS)."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.scoring import SecurityFindings
from lib.review_evidence.runners._registry import register


class EslintSecurityRunner:
    name = "eslint-security"
    category = "security"

    def is_applicable(self, repo_root: Path) -> bool:
        return (repo_root / "package.json").exists() and any(
            repo_root.rglob(p) for p in ["*.ts", "*.tsx", "*.js", "*.jsx"]
        )

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        try:
            p = subprocess.run(
                ["npx", "--no-install", "eslint", ".", "--format", "json",
                 "--no-eslintrc", "--plugin", "security", "--rule",
                 '{"security/detect-eval-with-expression":"error","security/detect-non-literal-fs-filename":"warn"}'],
                cwd=repo_root, capture_output=True, text=True,
                timeout=60, check=False,
            )
            if not p.stdout.strip():
                return SecurityFindings()
            data = json.loads(p.stdout)
            errors = sum(f.get("errorCount", 0) for f in data)
            warnings = sum(f.get("warningCount", 0) for f in data)
            # eslint-security: errors → high, warnings → medium (no critical)
            return SecurityFindings(high=errors, medium=warnings)
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(EslintSecurityRunner())
```

### Step 4 — Run + commit

```bash
python3 -m pytest tests/test_review_evidence_runner_pip_audit.py \
                   tests/test_review_evidence_runner_npm_audit.py \
                   tests/test_review_evidence_runner_eslint_security.py -v
# 15 passed atteso (5 per ognuno)

git add lib/review_evidence/runners/pip_audit.py \
        lib/review_evidence/runners/npm_audit.py \
        lib/review_evidence/runners/eslint_security.py \
        tests/test_review_evidence_runner_pip_audit.py \
        tests/test_review_evidence_runner_npm_audit.py \
        tests/test_review_evidence_runner_eslint_security.py \
        tests/fixtures/review-evidence/pip_audit_output.json \
        tests/fixtures/review-evidence/npm_audit_output.json \
        tests/fixtures/review-evidence/eslint_security_output.json
git commit -m "feat(review-evidence-v2): add 3 MVP runner (pip-audit, npm-audit, eslint-security) (#task-04)"
```

## Criteri di accettazione

- [ ] 3 runner integrati nel registry (Task 03 framework)
- [ ] PipAuditRunner detect via requirements.txt / pyproject / setup.py / Pipfile
- [ ] NpmAuditRunner detect via package.json
- [ ] EslintSecurityRunner detect via package.json + .ts/.tsx/.js/.jsx files
- [ ] Severity mapping coerente (critical/high/medium/low → SecurityFindings)
- [ ] Tool missing → None graceful
- [ ] Timeout 60s per deps runner (network slow)
- [ ] 15 test passano (5 per runner)
- [ ] No regression v1
