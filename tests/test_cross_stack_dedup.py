"""Wave 2/3 cross-stack porting tests + AC19 cross-layer dedup.

Tests:
- Java JPA rule (CWE-89 + CWE-639)
- Python boto3 presigned URL TTL (CWE-200)
- Angular bypassSecurityTrust (CWE-79)
- Cross-layer dedup (community + SIAE on same line)
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lib.review_evidence.dedup import dedup_findings


REPO = Path(__file__).parents[1]
FIXTURES = REPO / "tests" / "fixtures" / "semgrep_siae" / "synthetic"

RULE_JPA = REPO / "rules" / "semgrep" / "siae" / "authz-tenant" / "java-jpa-tenant.yaml"
RULE_PY_BOTO3 = REPO / "rules" / "semgrep" / "siae" / "presigned-url" / "py-boto3-presigned-ttl.yaml"
RULE_NG_BYPASS = REPO / "rules" / "semgrep" / "siae" / "xss-supplement" / "angular-bypass-security-trust.yaml"


def _run_semgrep(rule: Path, target: Path, tmp_path: Path) -> list[dict]:
    dest = tmp_path / target.name
    dest.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
    p = subprocess.run(
        ["semgrep", "--config", str(rule), "--json", "--quiet", str(dest)],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if not p.stdout.strip():
        return []
    return json.loads(p.stdout).get("results", [])


# ---------------------------------------------------------------------------
# Cross-stack rule tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_java_jpa_rule_catches_native_query_sqli_and_no_tenant(tmp_path):
    """Java JPA: @Query nativeQuery con concat O senza id_emittente."""
    findings = _run_semgrep(RULE_JPA, FIXTURES / "vulnerable" / "java-jpa-tenant.java", tmp_path)
    assert len(findings) >= 1, f"Expected >=1 finding on Java JPA vuln; got {len(findings)}"


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_java_jpa_rule_skips_safe_parameterized(tmp_path):
    findings = _run_semgrep(RULE_JPA, FIXTURES / "safe" / "java-jpa-tenant-safe.java", tmp_path)
    assert findings == []


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_py_boto3_catches_ttl_too_long(tmp_path):
    """Python boto3 generate_presigned_url(ExpiresIn>60)."""
    findings = _run_semgrep(RULE_PY_BOTO3, FIXTURES / "vulnerable" / "py-boto3-presigned-ttl.py", tmp_path)
    assert len(findings) == 2, f"Expected 2 (86400 + 3600); got {len(findings)}"


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_py_boto3_skips_ttl_60s(tmp_path):
    findings = _run_semgrep(RULE_PY_BOTO3, FIXTURES / "safe" / "py-boto3-presigned-safe.py", tmp_path)
    assert findings == []


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_angular_bypass_catches_all_variants(tmp_path):
    """Angular DomSanitizer 5 bypass variants."""
    findings = _run_semgrep(RULE_NG_BYPASS, FIXTURES / "vulnerable" / "angular-bypass-security-trust.ts", tmp_path)
    assert len(findings) == 3, f"Expected 3 bypass (Html+Url+ResourceUrl); got {len(findings)}"


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_angular_safe_template_interpolation_skipped(tmp_path):
    findings = _run_semgrep(RULE_NG_BYPASS, FIXTURES / "safe" / "angular-safe-template.ts", tmp_path)
    assert findings == []


# ---------------------------------------------------------------------------
# AC19 cross-layer dedup tests
# ---------------------------------------------------------------------------

def test_dedup_severity_max_wins_community_plus_siae():
    """ADR §3.3.0: community WARNING + SIAE ERROR su stessa riga → ERROR vince."""
    findings = [
        {"path": "src/a.ts", "start": {"line": 10},
         "check_id": "javascript.express.security.audit.xss",
         "extra": {"severity": "WARNING"}},
        {"path": "src/a.ts", "start": {"line": 10},
         "check_id": "siae.formula-injection.ts.csv-row-join-naive",
         "extra": {"severity": "ERROR"}},
    ]
    deduped = dedup_findings(findings)
    assert len(deduped) == 1
    primary = deduped[0]
    assert primary["check_id"].startswith("siae.")
    assert "dedup_secondary" in primary
    assert len(primary["dedup_secondary"]) == 1
    assert primary["dedup_secondary"][0].startswith("javascript.")


def test_dedup_no_overlap_keeps_both():
    """Finding su righe diverse → entrambi mantenuti."""
    findings = [
        {"path": "src/a.ts", "start": {"line": 10},
         "check_id": "x", "extra": {"severity": "ERROR"}},
        {"path": "src/a.ts", "start": {"line": 20},
         "check_id": "y", "extra": {"severity": "ERROR"}},
    ]
    deduped = dedup_findings(findings)
    assert len(deduped) == 2


def test_dedup_different_files_keeps_both():
    findings = [
        {"path": "src/a.ts", "start": {"line": 10},
         "check_id": "x", "extra": {"severity": "ERROR"}},
        {"path": "src/b.ts", "start": {"line": 10},
         "check_id": "y", "extra": {"severity": "ERROR"}},
    ]
    deduped = dedup_findings(findings)
    assert len(deduped) == 2


def test_dedup_three_overlapping_keeps_max_severity():
    findings = [
        {"path": "src/a.ts", "start": {"line": 10},
         "check_id": "info-rule", "extra": {"severity": "INFO"}},
        {"path": "src/a.ts", "start": {"line": 10},
         "check_id": "warning-rule", "extra": {"severity": "WARNING"}},
        {"path": "src/a.ts", "start": {"line": 10},
         "check_id": "error-rule", "extra": {"severity": "ERROR"}},
    ]
    deduped = dedup_findings(findings)
    assert len(deduped) == 1
    assert deduped[0]["check_id"] == "error-rule"
    assert set(deduped[0]["dedup_secondary"]) == {"info-rule", "warning-rule"}
