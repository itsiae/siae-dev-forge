# Task 03 — Runner registry framework + bandit + gitleaks

**SP:** 2.0 · **AC mappati:** AC #11 · **Dipendenze:** Task 01 (schema) · **Wave:** 1b

## Goal

Creare framework `lib/review_evidence/runners/__init__.py` (registry) + 2 runner reference (bandit Python security, gitleaks secret scan cross-stack). Pattern identico a `lib/review_evidence/collectors/` esistente: registry singleton + auto-register a module load. Output normalizzato `SecurityFindings` (Task 02 dataclass).

## File coinvolti

**Creare:**
- `lib/review_evidence/runners/__init__.py` (registry esposto)
- `lib/review_evidence/runners/_registry.py` (registry impl)
- `lib/review_evidence/runners/bandit.py`
- `lib/review_evidence/runners/gitleaks.py`
- `tests/test_review_evidence_runners_registry.py`
- `tests/test_review_evidence_runner_bandit.py`
- `tests/test_review_evidence_runner_gitleaks.py`
- `tests/fixtures/review-evidence/bandit_output.json`
- `tests/fixtures/review-evidence/gitleaks_output.json`

## Step TDD

### Step 1 — Fixture

`tests/fixtures/review-evidence/bandit_output.json` (formato bandit `-f json`):

```json
{
  "errors": [],
  "metrics": {"_totals": {"SEVERITY.HIGH": 1, "SEVERITY.MEDIUM": 2, "SEVERITY.LOW": 0}},
  "results": [
    {"filename": "src/auth.py", "line_number": 12, "issue_severity": "HIGH",
     "issue_text": "hardcoded password", "test_id": "B105"},
    {"filename": "src/db.py", "line_number": 45, "issue_severity": "MEDIUM",
     "issue_text": "sql injection", "test_id": "B608"},
    {"filename": "src/db.py", "line_number": 78, "issue_severity": "MEDIUM",
     "issue_text": "exec", "test_id": "B102"}
  ]
}
```

`tests/fixtures/review-evidence/gitleaks_output.json`:

```json
[
  {"Description": "AWS Access Key", "File": "config.py", "StartLine": 5, "RuleID": "aws-access-key-id"},
  {"Description": "Generic API key", "File": ".env", "StartLine": 1, "RuleID": "generic-api-key"}
]
```

### Step 2 — Test registry

```python
"""Tests for runners registry framework."""
import pytest
from pathlib import Path
from unittest.mock import patch

from lib.review_evidence.runners import _registry as R


def test_register_and_list():
    R.registry.clear()

    class FakeRunner:
        name = "fake"
        category = "security"
        def is_applicable(self, repo_root: Path) -> bool:
            return True
        def run(self, repo_root: Path):
            return {"critical": 0, "high": 0, "medium": 0, "low": 0}

    R.register(FakeRunner())
    assert len(R.registry) == 1
    assert R.registry[0].name == "fake"


def test_applicable_filters_inapplicable():
    R.registry.clear()

    class AlwaysFalse:
        name = "no-op"
        category = "security"
        def is_applicable(self, repo_root):
            return False
        def run(self, repo_root):
            return None

    class AlwaysTrue:
        name = "yes-op"
        category = "security"
        def is_applicable(self, repo_root):
            return True
        def run(self, repo_root):
            return {}

    R.register(AlwaysFalse())
    R.register(AlwaysTrue())
    applicable = R.applicable(Path("/tmp"))
    assert len(applicable) == 1
    assert applicable[0].name == "yes-op"
```

### Step 3 — Test bandit runner

```python
"""Tests for bandit runner."""
import json
from pathlib import Path
from unittest.mock import patch

from lib.review_evidence.runners.bandit import BanditRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_python_repo(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")
    assert BanditRunner().is_applicable(tmp_path) is True


def test_not_applicable_non_python(tmp_path):
    assert BanditRunner().is_applicable(tmp_path) is False


def test_run_parses_severities(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")
    bandit_out = (FIX / "bandit_output.json").read_text()

    def fake_run(cmd, **kw):
        from subprocess import CompletedProcess
        return CompletedProcess(cmd, 0, stdout=bandit_out, stderr="")

    with patch("lib.review_evidence.runners.bandit.subprocess.run", side_effect=fake_run):
        result = BanditRunner().run(tmp_path)
    assert result.high == 1
    assert result.medium == 2
    assert result.low == 0
    assert result.critical == 0


def test_run_missing_bandit_returns_none(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")
    def fake_run(cmd, **kw):
        raise FileNotFoundError("bandit")
    with patch("lib.review_evidence.runners.bandit.subprocess.run", side_effect=fake_run):
        assert BanditRunner().run(tmp_path) is None
```

### Step 4 — Test gitleaks runner

```python
"""Tests for gitleaks runner."""
import json
from pathlib import Path
from unittest.mock import patch

from lib.review_evidence.runners.gitleaks import GitleaksRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_any_repo(tmp_path):
    (tmp_path / ".git").mkdir()
    assert GitleaksRunner().is_applicable(tmp_path) is True


def test_run_parses_findings_as_critical(tmp_path):
    (tmp_path / ".git").mkdir()
    gl_out = (FIX / "gitleaks_output.json").read_text()
    def fake_run(cmd, **kw):
        from subprocess import CompletedProcess
        # gitleaks exits 1 when leaks found, but stdout has JSON
        return CompletedProcess(cmd, 1, stdout=gl_out, stderr="")
    with patch("lib.review_evidence.runners.gitleaks.subprocess.run", side_effect=fake_run):
        result = GitleaksRunner().run(tmp_path)
    # Both findings = critical (secrets = critical severity)
    assert result.critical == 2
    assert result.high == 0
```

### Step 5 — Implementa registry, bandit, gitleaks

`lib/review_evidence/runners/_registry.py`:

```python
"""Plug-in registry for OSS runners (security, quality, deps, etc)."""
from __future__ import annotations
from pathlib import Path
from typing import Protocol, Any


class Runner(Protocol):
    name: str
    category: str  # "security" | "quality" | "deps" | "secret"

    def is_applicable(self, repo_root: Path) -> bool: ...
    def run(self, repo_root: Path) -> Any: ...


registry: list[Runner] = []


def register(runner: Runner) -> None:
    registry.append(runner)


def applicable(repo_root: Path) -> list[Runner]:
    return [r for r in registry if r.is_applicable(repo_root)]
```

`lib/review_evidence/runners/__init__.py`:

```python
"""Runner framework + auto-load OSS adapters."""
from lib.review_evidence.runners._registry import register, registry, applicable, Runner  # noqa: F401
```

`lib/review_evidence/runners/bandit.py`:

```python
"""Bandit Python security runner."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.scoring import SecurityFindings
from lib.review_evidence.runners._registry import register


class BanditRunner:
    name = "bandit"
    category = "security"

    def is_applicable(self, repo_root: Path) -> bool:
        return (
            (repo_root / "pyproject.toml").exists()
            or (repo_root / "setup.py").exists()
            or any(repo_root.rglob("*.py"))
        )

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        try:
            p = subprocess.run(
                ["bandit", "-r", ".", "-f", "json", "-q"],
                cwd=repo_root, capture_output=True, text=True,
                timeout=30, check=False,
            )
            if not p.stdout.strip():
                return None
            data = json.loads(p.stdout)
            totals = data.get("metrics", {}).get("_totals", {})
            return SecurityFindings(
                critical=0,
                high=totals.get("SEVERITY.HIGH", 0),
                medium=totals.get("SEVERITY.MEDIUM", 0),
                low=totals.get("SEVERITY.LOW", 0),
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(BanditRunner())
```

`lib/review_evidence/runners/gitleaks.py`:

```python
"""Gitleaks secret scanner (cross-stack)."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.scoring import SecurityFindings
from lib.review_evidence.runners._registry import register


class GitleaksRunner:
    name = "gitleaks"
    category = "secret"

    def is_applicable(self, repo_root: Path) -> bool:
        return (repo_root / ".git").exists()

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        try:
            p = subprocess.run(
                ["gitleaks", "detect", "--no-banner", "--report-format=json",
                 "--report-path=/dev/stdout", "--source", "."],
                cwd=repo_root, capture_output=True, text=True,
                timeout=30, check=False,
            )
            # gitleaks exit 1 when leaks present, stdout has JSON
            if not p.stdout.strip():
                return SecurityFindings()  # 0 leaks
            findings = json.loads(p.stdout)
            # Every secret = CRITICAL (zero tolerance)
            return SecurityFindings(critical=len(findings))
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(GitleaksRunner())
```

### Step 6 — Run + commit

```bash
python3 -m pytest tests/test_review_evidence_runners_registry.py \
                   tests/test_review_evidence_runner_bandit.py \
                   tests/test_review_evidence_runner_gitleaks.py -v
# 2 + 4 + 2 = 8 passed atteso

git add lib/review_evidence/runners/_registry.py \
        lib/review_evidence/runners/__init__.py \
        lib/review_evidence/runners/bandit.py \
        lib/review_evidence/runners/gitleaks.py \
        tests/test_review_evidence_runners_registry.py \
        tests/test_review_evidence_runner_bandit.py \
        tests/test_review_evidence_runner_gitleaks.py \
        tests/fixtures/review-evidence/bandit_output.json \
        tests/fixtures/review-evidence/gitleaks_output.json
git commit -m "feat(review-evidence-v2): runner registry + bandit + gitleaks (#task-03)"
```

## Criteri di accettazione

- [ ] Runner registry pattern coerente con collectors v1 (auto-register a import)
- [ ] BanditRunner: applicable su Python repo, parsing severity HIGH/MEDIUM/LOW → SecurityFindings
- [ ] GitleaksRunner: applicable su qualsiasi git repo, ogni leak = critical
- [ ] Tool missing → run() returns None graceful
- [ ] Timeout 30s per runner (memory `feedback_macos_timeout_portability`)
- [ ] 8 test passano (2 registry + 4 bandit + 2 gitleaks)
- [ ] No regression v1
