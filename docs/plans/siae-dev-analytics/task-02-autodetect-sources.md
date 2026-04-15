# Task 02 — autodetect_sources.py + test

**Goal:** Implementare rilevamento automatico delle fonti dati disponibili con matrice gracefulness (FULL/HYBRID/GITHUB-ONLY/ABORT).

**AC coperti:** AC03

**Dipendenze:** Task 1

**Tempo stimato:** 20 min

---

## File coinvolti

- `skills/siae-dev-analytics/scripts/autodetect_sources.py` (nuovo)
- `skills/siae-dev-analytics/tests/test_autodetect.py` (nuovo)

## Step 1 — TDD: Scrivi test PRIMA

Crea `skills/siae-dev-analytics/tests/test_autodetect.py`:

```python
"""Test per autodetect_sources.py — TDD first."""
from unittest.mock import patch, MagicMock
import pytest

# L'import si risolve via sys.path in conftest.py (vedi Step 4).
# Fallisce con ModuleNotFoundError finché Step 3 non è completato — atteso in TDD RED.
import autodetect_sources as ad


def test_github_authenticated_returns_true():
    """gh auth status OK → github=True."""
    with patch("subprocess.run") as mock:
        mock.return_value = MagicMock(returncode=0, stdout="Logged in to github.com")
        result = ad.check_gh_auth()
    assert result is True


def test_github_not_authenticated_returns_false():
    """gh auth status KO → github=False."""
    with patch("subprocess.run") as mock:
        mock.return_value = MagicMock(returncode=1, stdout="")
        result = ad.check_gh_auth()
    assert result is False


def test_s3_bucket_accessible_returns_true():
    """boto3 head_bucket OK → s3=True."""
    with patch("boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.head_bucket.return_value = {}
        mock_client.return_value = mock_s3
        result = ad.check_s3_prefix("siae-devforge-telemetry", "devforge-logs/")
    assert result is True


def test_s3_bucket_no_creds_returns_false():
    """boto3 NoCredentials → s3=False."""
    with patch("boto3.client") as mock_client:
        mock_client.side_effect = Exception("NoCredentialsError")
        result = ad.check_s3_prefix("siae-devforge-telemetry", "devforge-logs/")
    assert result is False


def test_mode_full_all_sources_available():
    """github + s3_devforge + s3_blend → FULL."""
    report = ad.SourceReport(github=True, s3_devforge=True, s3_blend=True)
    assert report.mode() == "FULL"


def test_mode_hybrid_s3_partial():
    """github + s3_devforge senza s3_blend → HYBRID."""
    report = ad.SourceReport(github=True, s3_devforge=True, s3_blend=False)
    assert report.mode() == "HYBRID"


def test_mode_github_only_no_s3():
    """github ok, nessun s3 → GITHUB-ONLY."""
    report = ad.SourceReport(github=True, s3_devforge=False, s3_blend=False)
    assert report.mode() == "GITHUB-ONLY"


def test_mode_abort_no_github():
    """github mancante → ABORT."""
    report = ad.SourceReport(github=False, s3_devforge=False, s3_blend=False)
    assert report.mode() == "ABORT"


def test_autodetect_aborts_without_github():
    """autodetect() solleva RuntimeError se github mancante."""
    with patch.object(ad, "check_gh_auth", return_value=False):
        with pytest.raises(RuntimeError, match="GitHub CLI not authenticated"):
            ad.autodetect(abort_on_no_github=True)


def test_autodetect_returns_report_full_mode():
    """autodetect() con tutti disponibili → report FULL."""
    with patch.object(ad, "check_gh_auth", return_value=True), \
         patch.object(ad, "check_s3_prefix", return_value=True):
        report = ad.autodetect()
    assert report.mode() == "FULL"
    assert report.github is True
    assert report.s3_devforge is True
    assert report.s3_blend is True
```

## Step 2 — Run test, verifica che falliscono

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge/skills/siae-dev-analytics"
pytest tests/test_autodetect.py -v 2>&1 | tail -20
```

Output atteso: `ModuleNotFoundError: No module named 'autodetect_sources'` (il modulo non esiste finché Step 3 non viene completato — atteso in TDD RED).

## Step 3 — Implementa `autodetect_sources.py`

Crea `skills/siae-dev-analytics/scripts/autodetect_sources.py`:

```python
"""Auto-detect data sources for dev analytics.

Matrice mode:
    github | s3_devforge | s3_blend | mode
    ✅     | ✅          | ✅       | FULL
    ✅     | ✅          | ❌       | HYBRID
    ✅     | ❌          | *        | GITHUB-ONLY
    ❌     | *           | *        | ABORT
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Literal

Mode = Literal["FULL", "HYBRID", "GITHUB-ONLY", "ABORT"]

S3_BUCKET = "siae-devforge-telemetry"
S3_DEVFORGE_PREFIX = "devforge-logs/"
S3_BLEND_PREFIX = "blend-usage/"


@dataclass
class SourceReport:
    """Stato delle fonti rilevate."""
    github: bool
    s3_devforge: bool
    s3_blend: bool

    def mode(self) -> Mode:
        if not self.github:
            return "ABORT"
        if self.s3_devforge and self.s3_blend:
            return "FULL"
        if self.s3_devforge or self.s3_blend:
            return "HYBRID"
        return "GITHUB-ONLY"

    def as_dict(self) -> dict:
        return {
            "github": self.github,
            "s3_devforge": self.s3_devforge,
            "s3_blend": self.s3_blend,
            "mode": self.mode(),
        }


def check_gh_auth() -> bool:
    """True se `gh auth status` indica sessione attiva."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0 and "Logged in" in (result.stdout + result.stderr)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_s3_prefix(bucket: str, prefix: str) -> bool:
    """True se bucket/prefix è accessibile e contiene almeno 1 oggetto."""
    try:
        import boto3  # lazy import, boto3 è opzionale
        s3 = boto3.client("s3")
        s3.head_bucket(Bucket=bucket)
        resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1)
        return resp.get("KeyCount", 0) > 0
    except Exception:
        return False


def autodetect(abort_on_no_github: bool = True) -> SourceReport:
    """Rileva le fonti disponibili."""
    github = check_gh_auth()
    if not github and abort_on_no_github:
        raise RuntimeError(
            "GitHub CLI not authenticated. Run `gh auth login` and retry."
        )

    s3_devforge = check_s3_prefix(S3_BUCKET, S3_DEVFORGE_PREFIX) if github else False
    s3_blend = check_s3_prefix(S3_BUCKET, S3_BLEND_PREFIX) if github else False

    return SourceReport(
        github=github,
        s3_devforge=s3_devforge,
        s3_blend=s3_blend,
    )


if __name__ == "__main__":
    import json
    report = autodetect(abort_on_no_github=False)
    print(json.dumps(report.as_dict(), indent=2))
```

## Step 4 — Setup import path nei test

In `tests/conftest.py` (appendi alla fine):

```python
import sys
from pathlib import Path

# Rendi importabili gli script direttamente (pattern siae-dev-analytics)
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
```

Dopo questo, l'import `import autodetect_sources as ad` nei test si risolve correttamente.

## Step 5 — Run test, verifica che passano

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge/skills/siae-dev-analytics"
pip install pytest boto3 2>&1 | tail -2
pytest tests/test_autodetect.py -v 2>&1 | tail -20
```

Output atteso: `10 passed in X.XXs`.

## Step 6 — Smoke test CLI

Run:
```bash
python3 skills/siae-dev-analytics/scripts/autodetect_sources.py
```

Output atteso (in ambiente con gh auth ok, senza AWS creds):
```json
{
  "github": true,
  "s3_devforge": false,
  "s3_blend": false,
  "mode": "GITHUB-ONLY"
}
```

## Step 7 — Commit

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge"
git add skills/siae-dev-analytics/scripts/autodetect_sources.py \
        skills/siae-dev-analytics/tests/test_autodetect.py \
        skills/siae-dev-analytics/tests/conftest.py
git commit -m "feat(skill): add autodetect_sources for siae-dev-analytics [Task 2/7]

- SourceReport dataclass con mode() FULL/HYBRID/GITHUB-ONLY/ABORT
- check_gh_auth via subprocess gh
- check_s3_prefix via boto3 head_bucket + list_objects_v2
- Graceful degrade: no creds AWS → s3=False, continua in GITHUB-ONLY
- 10 test pytest pass, mock subprocess + boto3

AC03"
```

## Criteri di accettazione Task 2

- [ ] `autodetect_sources.py` implementa `check_gh_auth`, `check_s3_prefix`, `autodetect`, `SourceReport`
- [ ] `SourceReport.mode()` restituisce FULL/HYBRID/GITHUB-ONLY/ABORT secondo matrice
- [ ] `autodetect(abort_on_no_github=True)` solleva RuntimeError se gh non autenticato
- [ ] CLI diretto stampa JSON con i 4 campi
- [ ] 10 test pytest pass
- [ ] Commit conventional

## Verifica

Run:
```bash
pytest skills/siae-dev-analytics/tests/test_autodetect.py -v --tb=short
```

Output atteso: `10 passed`.
