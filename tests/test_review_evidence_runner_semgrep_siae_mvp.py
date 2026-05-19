"""MVP test for Semgrep runner SIAE registry inclusion (Wave 1 task-09 minimal).

Verifica che il runner Semgrep di default includa SIA il community ruleset (`auto`)
SIA la SIAE custom rules registry, in modo che le regole SIAE Wave 1 siano
attive immediatamente senza override env var.

Wave 1 design ref: docs/plans/2026-05-18-security-hook-vulnerability-prevention-design.md
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lib.review_evidence.runners.semgrep import _DEFAULT_CONFIG


REPO_ROOT = Path(__file__).parents[1]
RULE_F1 = REPO_ROOT / "rules" / "semgrep" / "siae" / "formula-injection" / "ts-csv-concat.yaml"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "semgrep_siae" / "synthetic"


def test_default_config_includes_siae_rules_path():
    """AC6 MVP: default config Semgrep include il path SIAE rules (dir auto-discovery)."""
    assert "rules/semgrep/siae" in _DEFAULT_CONFIG, (
        f"_DEFAULT_CONFIG must include SIAE rules path, got: {_DEFAULT_CONFIG!r}"
    )


def test_default_config_preserves_community_auto():
    """AC6 MVP: backward-compat — community 'auto' ruleset resta nel default."""
    assert "auto" in _DEFAULT_CONFIG, (
        f"_DEFAULT_CONFIG must preserve community 'auto', got: {_DEFAULT_CONFIG!r}"
    )


def test_default_config_uses_siae_rules_dir():
    """AC6 v2: default config Semgrep punta alla SIAE rules DIR (auto-discovery)
    invece del registry.yaml manifest che NON è un Semgrep ruleset schema."""
    siae_dir = REPO_ROOT / "rules" / "semgrep" / "siae"
    assert str(siae_dir) in _DEFAULT_CONFIG, (
        f"_DEFAULT_CONFIG must reference SIAE rules DIR for Semgrep auto-discovery, "
        f"got: {_DEFAULT_CONFIG!r}"
    )


def test_default_config_does_not_use_registry_yaml_as_semgrep_config():
    """AC6 v2 regression: registry.yaml è un manifest documentale, NON un Semgrep
    ruleset (Semgrep --config su quel path crasha con JSON empty stdout)."""
    assert "registry.yaml" not in _DEFAULT_CONFIG, (
        f"_DEFAULT_CONFIG must NOT pass registry.yaml as Semgrep config "
        f"(it has no `rules: [{{id, pattern, ...}}]` schema), "
        f"got: {_DEFAULT_CONFIG!r}"
    )


def test_siae_rules_dir_exists_with_at_least_one_rule_yaml():
    """Sanity check: la dir referenziata da _DEFAULT_CONFIG esiste e contiene
    almeno un rule yaml (non manifest)."""
    siae_dir = REPO_ROOT / "rules" / "semgrep" / "siae"
    assert siae_dir.is_dir(), f"SIAE rules dir must exist at: {siae_dir}"
    rule_yamls = [
        p for p in siae_dir.rglob("*.yaml")
        if p.name not in {"registry.yaml", "suppressions.yaml"}
    ]
    assert rule_yamls, f"SIAE rules dir must contain at least one rule yaml: {siae_dir}"


# ---------------------------------------------------------------------------
# AC1 Wave 1 — Semgrep --test integration for rule F1 Formula Injection.
# Skipped if `semgrep` binary not on PATH (CI runner setup).
# ---------------------------------------------------------------------------

def _run_semgrep_on(target: Path, tmp_path: Path) -> list[dict]:
    """Copy target outside the repo (paths.exclude bypass) and run Semgrep rule F1."""
    dest = tmp_path / target.name
    dest.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
    p = subprocess.run(
        ["semgrep", "--config", str(RULE_F1), "--json", "--quiet", str(dest)],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if not p.stdout.strip():
        return []
    return json.loads(p.stdout).get("results", [])


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_rule_f1_matches_vulnerable_csv_concat(tmp_path):
    """AC1 must-catch: vulnerable fixture must produce >=2 findings."""
    findings = _run_semgrep_on(FIXTURES / "vulnerable" / "f1-csv-concat.ts", tmp_path)
    assert len(findings) >= 2, (
        f"Rule F1 must catch vulnerable CSV concat; got {len(findings)} findings"
    )
    rule_ids = {f["check_id"].split(".")[-1] for f in findings}
    assert "csv-row-join-naive" in rule_ids, (
        f"Expected csv-row-join-naive in findings; got {rule_ids}"
    )


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_rule_f1_matches_hyperlink_poc(tmp_path):
    """AC1 PoC: =HYPERLINK pentest payload must be caught."""
    findings = _run_semgrep_on(FIXTURES / "vulnerable" / "f1-csv-poc-hyperlink.ts", tmp_path)
    assert len(findings) >= 2, (
        f"Rule F1 must catch HYPERLINK PoC; got {len(findings)} findings"
    )


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_rule_f1_does_not_match_safe_stringify(tmp_path):
    """AC1 must-skip: safe csv-stringify fixture must produce 0 findings."""
    findings = _run_semgrep_on(FIXTURES / "safe" / "f1-csv-stringify.ts", tmp_path)
    assert findings == [], (
        f"Rule F1 must NOT match safe csv-stringify; got {len(findings)} findings"
    )


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_rule_f1_does_not_match_numeric_pre_filter(tmp_path):
    """EC-03: numeric values mapped via String(i) must NOT trigger rule F1."""
    findings = _run_semgrep_on(FIXTURES / "safe" / "f1-csv-concat-numeric.ts", tmp_path)
    assert findings == [], (
        f"Rule F1 must NOT match numeric-mapped CSV (EC-03 pre-filter); "
        f"got {len(findings)} findings"
    )


# ---------------------------------------------------------------------------
# Additional Wave 1 rules — F2 (DAO tenant), F4 (soft-delete), F6 (query-param), F26 (JWT)
# ---------------------------------------------------------------------------

RULE_F2 = REPO_ROOT / "rules" / "semgrep" / "siae" / "authz-tenant" / "ts-dao-missing-tenant.yaml"
RULE_F4 = REPO_ROOT / "rules" / "semgrep" / "siae" / "soft-delete" / "sql-view-only-filter.yaml"
RULE_F6 = REPO_ROOT / "rules" / "semgrep" / "siae" / "authz-tenant" / "ts-query-param-tenant-override.yaml"
RULE_F26 = REPO_ROOT / "rules" / "semgrep" / "siae" / "jwt" / "ts-jwt-localstorage.yaml"


def _run_semgrep_with_rule(rule: Path, target: Path, tmp_path: Path) -> list[dict]:
    dest = tmp_path / target.name
    dest.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
    p = subprocess.run(
        ["semgrep", "--config", str(rule), "--json", "--quiet", str(dest)],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if not p.stdout.strip():
        return []
    return json.loads(p.stdout).get("results", [])


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_rule_f2_matches_dao_without_tenant(tmp_path):
    """F2 must-catch: 3 vulnerable patterns (id_file/id_report/idFile)."""
    findings = _run_semgrep_with_rule(
        RULE_F2, FIXTURES / "vulnerable" / "f2-dao-missing-tenant.ts", tmp_path
    )
    assert len(findings) == 3, f"F2 expected 3, got {len(findings)}"


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_rule_f2_skips_safe_dao_with_tenant(tmp_path):
    findings = _run_semgrep_with_rule(
        RULE_F2, FIXTURES / "safe" / "f2-dao-with-tenant.ts", tmp_path
    )
    assert findings == []


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_rule_f4_matches_view_only_filter(tmp_path):
    """F4 must-catch: vulnerable SQL views (including whitespace variant)."""
    findings = _run_semgrep_with_rule(
        RULE_F4, FIXTURES / "vulnerable" / "f4-view-only-filter.sql", tmp_path
    )
    assert len(findings) >= 2, f"F4 expected >=2, got {len(findings)}"


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_rule_f4_skips_rls_protected(tmp_path):
    findings = _run_semgrep_with_rule(
        RULE_F4, FIXTURES / "safe" / "f4-rls-protected.sql", tmp_path
    )
    assert findings == []


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_rule_f6_matches_query_param_tenant(tmp_path):
    findings = _run_semgrep_with_rule(
        RULE_F6, FIXTURES / "vulnerable" / "f6-query-param-tenant.ts", tmp_path
    )
    assert len(findings) >= 1, f"F6 expected >=1, got {len(findings)}"


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_rule_f6_skips_token_derived(tmp_path):
    findings = _run_semgrep_with_rule(
        RULE_F6, FIXTURES / "safe" / "f6-token-derived.ts", tmp_path
    )
    assert findings == []


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_rule_f26_matches_localstorage_jwt(tmp_path):
    """F26 must-catch: 3 variants (token/jwt/accessToken)."""
    findings = _run_semgrep_with_rule(
        RULE_F26, FIXTURES / "vulnerable" / "f26-jwt-localstorage.ts", tmp_path
    )
    assert len(findings) == 3, f"F26 expected 3, got {len(findings)}"


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_rule_f26_skips_httponly_cookie(tmp_path):
    findings = _run_semgrep_with_rule(
        RULE_F26, FIXTURES / "safe" / "f26-httponly-cookie.ts", tmp_path
    )
    assert findings == []
